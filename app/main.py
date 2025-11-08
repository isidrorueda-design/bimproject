# app/main.py
import os
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from starlette.concurrency import run_in_threadpool
from datetime import timedelta
from typing import List
from . import crud, models, schemas, security, dependencies
from .database import SessionLocal, engine, get_db

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="ConTech PM API")

@app.on_event("startup")
def create_super_admin_on_startup():

    db = SessionLocal()
    try:
        super_admin = crud.get_user_by_email(db, email="admin@admin.com")
        
        if not super_admin:
            print("Creando usuario Super Admin por defecto (admin@admin.com)...")
            admin_user_schema = schemas.UserCreate(
                email="admin@admin.com",
                password="admin",
                company_id=None,
                role="super_admin"
            )
            crud.create_user(db=db, user=admin_user_schema)
            print("Usuario Super Admin creado. Contraseña: admin")
        else:
            print("Usuario Super Admin ya existe.")
            
    finally:
        db.close()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(
        data={"sub": user.email, "cid": user.company_id, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/companies/", response_model=schemas.Company, status_code=201)
def create_company_endpoint(
    company: schemas.CompanyCreate, 
    db: Session = Depends(get_db),
    current_super_admin: models.User = Depends(dependencies.get_current_super_admin)
):

    db_company = crud.get_company_by_name(db, name=company.name)
    if db_company:
        raise HTTPException(status_code=400, detail="Una compañía con este nombre ya existe")
    return crud.create_company(db=db, company=company)

@app.get("/companies/", response_model=List[schemas.Company])
def read_companies_endpoint(
    db: Session = Depends(get_db),
    current_super_admin: models.User = Depends(dependencies.get_current_super_admin)
):
    return db.query(models.Company).all()

@app.post("/users/", response_model=schemas.User, status_code=201)
def create_user_endpoint(
    user: schemas.UserCreate, 
    db: Session = Depends(get_db),

    current_super_admin: models.User = Depends(dependencies.get_current_super_admin)
):

    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Un usuario con este email ya existe")
    
    if user.company_id: 
        db_company = crud.get_company(db, company_id=user.company_id)
        if not db_company:
            raise HTTPException(status_code=404, detail="La compañía especificada no existe")
            
    return crud.create_user(db=db, user=user)

@app.get("/users/me", response_model=schemas.User)
def read_users_me(
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    return current_user

@app.post("/projects/", response_model=schemas.Project, status_code=201)
def create_project(
    project_create_data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    if project_create_data.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    return crud.create_project(db=db, project=project_create_data)

@app.get("/projects/", response_model=List[schemas.Project])
def get_projects(
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    projects = crud.get_projects(db=db, company_id=current_user.company_id, skip=skip, limit=limit)
    return [schemas.Project.from_orm(p) for p in projects]

@app.get("/projects/{project_id}", response_model=schemas.Project)
def get_project_by_id(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = crud.get_project_details(
        db=db, project_id=project_id, company_id=current_user.company_id
    )
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    project_schema = schemas.Project.from_orm(db_project)
    project_schema.tasks = crud.get_project_tasks_as_tree(db=db, project_id=project_id)
    project_schema.folders = crud.get_all_project_folders(db=db, project_id=project_id)
    return project_schema

@app.post("/projects/{project_id}/tasks/", response_model=schemas.Task, status_code=201)
def create_task_for_project(
    project_id: int,
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Proyecto no encontrado o no autorizado para esta acción."
        )
    
    return crud.create_task(db=db, task=task, project_id=project_id)

@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task_endpoint(
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_task = crud.get_task(db, task_id=task_id)

    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    if db_task.project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No autorizado para modificar esta tarea."
        )

    updated_task = crud.update_task(db, task_id=task_id, task_update=task_update)
    return updated_task

@app.post("/projects/{project_id}/work_items/", response_model=schemas.WorkItem, status_code=201)
def create_work_item_for_project(
    project_id: int,
    work_item: schemas.WorkItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no autorizado para esta acción."
        )

    return crud.create_work_item(db=db, work_item=work_item, project_id=project_id)

@app.get("/projects/{project_id}/work_items/", response_model=List[schemas.WorkItem])
def get_work_items_for_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no autorizado."
        )
    
    return crud.get_project_work_items(db=db, project_id=project_id)

@app.get("/projects/{project_id}/contracts/", response_model=List[schemas.Contract])
def get_contracts_for_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no autorizado."
        )
    
    return crud.get_project_contracts(db=db, project_id=project_id)

@app.post("/projects/{project_id}/contracts/", response_model=schemas.Contract, status_code=201)
def create_contract_for_project(
    project_id: int,
    contract: schemas.ContractCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no autorizado para esta acción."
        )

    return crud.create_contract(db=db, contract=contract, project_id=project_id)

@app.post("/projects/{project_id}/estimates/", response_model=schemas.Estimate, status_code=201)
def create_estimate_for_project(
    project_id: int,
    estimate: schemas.EstimateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no autorizado para esta acción."
        )

    db_contract = crud.get_contract(db, contract_id=estimate.contract_id)
    if not db_contract or db_contract.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El contrato especificado no pertenece a este proyecto."
        )

    return crud.create_estimate(db=db, estimate=estimate, project_id=project_id)

@app.get("/projects/{project_id}/estimates/", response_model=List[schemas.Estimate])
def get_estimates_for_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no autorizado."
        )
    
    return crud.get_project_estimates(db=db, project_id=project_id)

@app.delete("/estimates/{estimate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_estimate_endpoint(
    estimate_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_estimate = crud.get_estimate_by_id(db, estimate_id=estimate_id)

    if not db_estimate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimación no encontrada.")

    if db_estimate.project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No autorizado para eliminar esta estimación."
        )

    crud.delete_estimate(db, estimate_id=estimate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/projects/{project_id}/folders/", response_model=schemas.Folder, status_code=201)
def create_folder_for_project(
    project_id: int,
    folder: schemas.FolderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o no autorizado para esta acción."
        )

    return crud.create_folder(db=db, folder=folder, project_id=project_id)

@app.get("/folders/{folder_id}", response_model=schemas.Folder)
def get_folder_contents_endpoint(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_folder = crud.get_folder_contents(db, folder_id=folder_id)

    if not db_folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carpeta no encontrada.")
  
    if db_folder.project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No autorizado para acceder a esta carpeta."
        )

    return db_folder

@app.post("/documents/", response_model=schemas.Document, status_code=201)
def create_document_concept_endpoint(
    document: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_folder = crud.get_folder_contents(db, folder_id=document.folder_id)

    if not db_folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La carpeta especificada no existe.")

    if db_folder.project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No autorizado para crear documentos en esta carpeta."
        )

    return crud.create_document_concept(db=db, document=document)

@app.post("/documents/{document_id}/upload_version/", response_model=schemas.DocumentVersion, status_code=201)
def upload_document_version_endpoint(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    """
    Sube una nueva versión de un archivo para un documento existente,
    verificando que el documento pertenezca a la compañía del usuario.
    """
    # Obtenemos el documento y sus relaciones para verificar la pertenencia
    db_document = db.query(models.Document).options(
        joinedload(models.Document.folder).joinedload(models.Folder.project)
    ).filter(models.Document.id == document_id).first()

    if not db_document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El documento no existe.")

    # Verificamos que el proyecto de la carpeta del documento pertenezca a la compañía del usuario
    if db_document.folder.project.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No autorizado para subir versiones a este documento."
        )

    return crud.create_new_document_version(db=db, file=file, document_id=document_id)

@app.post("/contractors/", response_model=schemas.Contractor, status_code=201)
def create_contractor_endpoint(
    contractor_data: schemas.ContractorCreateRequest, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_contractor = crud.get_contractor_by_razon_social(
        db, razon_social=contractor_data.razon_social, company_id=current_user.company_id
    )
    if db_contractor:
        raise HTTPException(status_code=400, detail="Ya existe un contratista con esta Razón Social")

    contractor = schemas.ContractorCreate(
        **contractor_data.model_dump(),
        company_id=current_user.company_id
    )

    return crud.create_contractor(db=db, contractor=contractor)

@app.get("/contractors/", response_model=List[schemas.Contractor])
def read_contractors_endpoint(
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    contractors = crud.get_contractors(db, company_id=current_user.company_id, skip=skip, limit=limit)
    return contractors