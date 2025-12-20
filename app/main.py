# app/main.py
import os
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from starlette.concurrency import run_in_threadpool
from datetime import timedelta
from typing import List, Optional
from . import crud, models, schemas, security, dependencies
from .database import SessionLocal, engine, get_db
from .routers import bcf, ifc
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

app.include_router(bcf.router)
app.include_router(ifc.router)

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

def get_project_for_user(db: Session, project_id: int, company_id: int):
    db_project = crud.get_project_details(db, project_id=project_id, company_id=company_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado o no pertenece a su compañía")
    return db_project

@app.post("/projects/", response_model=schemas.Project, status_code=201)
def create_project(
    project_create_data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_admin)
):
    if current_user.role != "super_admin" and project_create_data.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="No autorizado para crear proyectos en esta compañía.")
    return crud.create_project(db=db, project=project_create_data)

@app.get("/projects/", response_model=List[schemas.Project])
def get_projects(
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    projects = crud.get_projects(db=db, company_id=current_user.company_id, skip=skip, limit=limit)
    return projects

@app.get("/projects/{project_id}", response_model=schemas.Project)
def get_project_by_id(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_project = get_project_for_user(
        db=db, project_id=project_id, company_id=current_user.company_id
    )
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    return db_project

@app.put("/projects/{project_id}", response_model=schemas.Project)
def update_project_endpoint(
    project_id: int,
    project_update: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_project = crud.update_project(
        db=db, project_id=project_id, 
        project_update=project_update, 
        company_id=current_user.company_id
    )
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return db_project

@app.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_admin)
):
    db_project = crud.delete_project_by_id( # La lógica de company_id ya está en el crud
        db=db, project_id=project_id, company_id=current_user.company_id
    )
    if not db_project: raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return Response(status_code=204)

@app.post("/projects/{project_id}/tasks/", response_model=schemas.Task, status_code=201)
def create_task_for_project(
    project_id: int, 
    task: schemas.TaskCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    return crud.create_task(db=db, task=task, project_id=project_id, creator_id=current_user.id)

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    crud.delete_task(db=db, task_id=task_id, user=current_user)
    return Response(status_code=204)

@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task_endpoint(
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    task = crud.get_task(db, task_id)
    if not task or task.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
        
    updated_task = crud.update_task(db=db, task_id=task_id, task_update=task_update)
    return updated_task

# --- Concept Endpoints ---
@app.post("/concepts/", response_model=schemas.Concept)
def create_concept_endpoint(
    concept: schemas.ConceptCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_admin)
):
    if concept.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="No puede crear conceptos para otra compañía")
    return crud.create_concept(db=db, concept=concept)

@app.get("/concepts/", response_model=List[schemas.Concept])
def read_concepts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    return crud.get_concepts(db, company_id=current_user.company_id, skip=skip, limit=limit)

@app.put("/concepts/{concept_id}", response_model=schemas.Concept)
def update_concept_endpoint(
    concept_id: int,
    concept_update: schemas.ConceptUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_admin)
):
    concept = crud.get_concept(db, concept_id)
    if not concept or concept.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")
    return crud.update_concept(db=db, concept_id=concept_id, concept_update=concept_update)

@app.delete("/concepts/{concept_id}", status_code=204)
def delete_concept_endpoint(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_admin)
):
    concept = crud.get_concept(db, concept_id)
    if not concept or concept.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")
    crud.delete_concept(db=db, concept_id=concept_id)
    return Response(status_code=204)

@app.post("/concepts/import-from-contracts", status_code=200)
def import_concepts_from_contracts_endpoint(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_admin)
):
    count = crud.import_concepts_from_contracts(db, current_user.company_id)
    return {"message": f"Se importaron {count} conceptos desde los contratos existentes"}

@app.post("/tasks/{task_id}/concepts", response_model=schemas.Task)
def assign_concept_to_task_endpoint(
    task_id: int,
    concept_assignment: schemas.TaskConceptCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    # Verify task access
    task = crud.get_task(db, task_id)
    if not task or task.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
        
    result = crud.assign_concept_to_task(db, task_id, concept_assignment.concept_id, concept_assignment.quantity)
    if not result:
        raise HTTPException(status_code=400, detail="Error al asignar concepto")
    return result

@app.delete("/tasks/{task_id}/concepts/{concept_id}", status_code=204)
def remove_concept_from_task_endpoint(
    task_id: int,
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    task = crud.get_task(db, task_id)
    if not task or task.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
        
    result = crud.remove_concept_from_task(db, task_id, concept_id)
    if not result:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    return Response(status_code=204)

@app.post("/tasks/{task_id}/dependencies/{predecessor_id}", status_code=201)
def add_task_dependency_endpoint(
    task_id: int,
    predecessor_id: int,
    type: str = "FS",
    lag: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    task = crud.get_task(db, task_id)
    pred = crud.get_task(db, predecessor_id)
    
    if not task or not pred:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if task.project.company_id != current_user.company_id or pred.project.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="No tiene permisos")
        
    result = crud.add_task_dependency(db, predecessor_id, task_id, type, lag)
    if not result:
        raise HTTPException(status_code=400, detail="Error al crear dependencia (posible ciclo)")
    return {"ok": True}

@app.delete("/tasks/{task_id}/dependencies/{predecessor_id}", status_code=204)
def remove_task_dependency_endpoint(
    task_id: int,
    predecessor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    task = crud.get_task(db, task_id)
    if not task or task.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
        
    crud.remove_task_dependency(db, predecessor_id, task_id)
    return Response(status_code=204)

@app.post("/tasks/{task_id}/cost", status_code=201)
def assign_cost_to_task_endpoint(
    task_id: int,
    cost_data: schemas.TaskCostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if task.project.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="No tiene permisos")
        
    return crud.assign_cost_to_task(db, task.project_id, task_id, cost_data.amount, cost_data.description)

@app.get("/tasks/{task_id}/cost", response_model=List[schemas.TaskCost])
def get_task_costs_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if task.project.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="No tiene permisos")
        
    items = crud.get_task_costs(db, task_id)
    # Transform ContractItem to TaskCost schema
    result = []
    for item in items:
        # Usamos la fecha del contrato como fecha del costo, si existe
        cost_date = item.contract.start_date if item.contract else None
        
        result.append({
            "id": item.id,
            "amount": item.precio_unitario, # Asumiendo cantidad 1
            "description": item.concepto,
            "date": cost_date,
            "contract_item": item # Pydantic se encargará de convertir esto a ContractItemBase si coinciden campos
        })
    return result

@app.get("/projects/{project_id}/tasks/root", response_model=List[schemas.Task])
def get_project_root_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    root_tasks = crud.get_root_tasks(db, project_id)
    return root_tasks

@app.get("/tasks/{task_id}/children", response_model=List[schemas.Task])
def get_task_children_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    task = crud.get_task(db, task_id)
    if not task or task.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no pertenece a su compañía")
    return task.subtasks

@app.post("/projects/{project_id}/tasks/import", status_code=201)
async def import_project_tasks_excel(
    project_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido.")
    file_contents = await file.read()
    try:
        result = crud.import_tasks_from_excel(db=db, project_id=project_id, file_contents=file_contents)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {e}")

@app.get("/projects/{project_id}/tasks/export")
def export_project_tasks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    file_stream = crud.export_project_tasks_to_excel(db, project_id)
    
    headers = {
        'Content-Disposition': f'attachment; filename="tareas_proyecto_{project_id}.xlsx"'
    }
    return StreamingResponse(file_stream, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.post("/projects/{project_id}/contractors", response_model=schemas.Contractor, status_code=201)
def create_contractor(
    project_id: int,
    contractor_data: schemas.ContractorBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    db_contractor = crud.get_contractor_by_razon_social(
        db, razon_social=contractor_data.razon_social, project_id=project_id
    )
    if db_contractor:
        raise HTTPException(status_code=400, detail="Ya existe un contratista con esta Razón Social")
    
    contractor_to_create = schemas.ContractorCreate(**contractor_data.model_dump(), project_id=project_id)
    return crud.create_contractor(db=db, contractor=contractor_to_create)

@app.get("/contractors/", response_model=List[schemas.Contractor])
def read_all_company_contractors(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    contractors = crud.get_all_company_contractors(db, company_id=current_user.company_id, skip=skip, limit=limit)
    return contractors

@app.post("/projects/{project_id}/contractors/import-excel/", status_code=201)
async def import_contractors(
    project_id: int,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido")
    file_contents = await file.read()
    try:
        result = crud.import_contractors_from_excel(
            db=db, file_contents=file_contents, project_id=project_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {e}")

@app.get("/projects/{project_id}/contractors", response_model=List[schemas.Contractor])
def read_contractors(
    project_id: int,
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    return crud.get_contractors(db, project_id=project_id, skip=skip, limit=limit)

@app.get("/contractors/{contractor_id}", response_model=schemas.Contractor)
def read_contractor_by_id(
    contractor_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_contractor = crud.get_contractor(db, contractor_id=contractor_id)
    if not db_contractor:
        raise HTTPException(status_code=404, detail="Contratista no encontrado")
    get_project_for_user(db, db_contractor.project_id, current_user.company_id)
    return db_contractor

@app.put("/contractors/{contractor_id}", response_model=schemas.Contractor)
def update_contractor(
    contractor_id: int,
    contractor_update: schemas.ContractorUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_contractor = crud.update_contractor(db, contractor_id=contractor_id, contractor_update=contractor_update, user_company_id=current_user.company_id)
    if not db_contractor:
        raise HTTPException(status_code=404, detail="Contratista no encontrado")
    return db_contractor

@app.delete("/contractors/{contractor_id}", status_code=204)
def delete_contractor(
    contractor_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_contractor = crud.delete_contractor(db, contractor_id=contractor_id, user_company_id=current_user.company_id)
    if not db_contractor:
        raise HTTPException(status_code=404, detail="Contratista no encontrado")
    return Response(status_code=204)

@app.post("/projects/{project_id}/work_items/", response_model=schemas.WorkItem, status_code=201)
def create_work_item_for_project_endpoint(
    project_id: int, 
    work_item: schemas.WorkItemCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    return crud.create_work_item(db=db, work_item=work_item, project_id=project_id)
@app.get("/projects/{project_id}/work_items/", response_model=List[schemas.WorkItem])
def read_project_work_items_endpoint(
    project_id: int, 
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    work_items = crud.get_project_work_items(db, project_id=project_id, skip=skip, limit=limit)
    return work_items
@app.get("/work_items/{work_item_id}", response_model=schemas.WorkItem)
def read_work_item_by_id_endpoint(
    work_item_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_work_item = crud.get_work_item(db, work_item_id=work_item_id)
    if not db_work_item:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    get_project_for_user(db, db_work_item.project_id, current_user.company_id)
    return db_work_item
@app.put("/work_items/{work_item_id}", response_model=schemas.WorkItem)
def update_work_item_endpoint(
    work_item_id: int,
    work_item_update: schemas.WorkItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_work_item = crud.get_work_item(db, work_item_id=work_item_id)
    if not db_work_item:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    get_project_for_user(db, db_work_item.project_id, current_user.company_id)
    db_work_item_updated = crud.update_work_item(db, work_item_id=work_item_id, work_item_update=work_item_update)
    return db_work_item_updated
@app.delete("/work_items/{work_item_id}", status_code=204)
def delete_work_item_endpoint(
    work_item_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_work_item = crud.get_work_item(db, work_item_id=work_item_id)
    if not db_work_item:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    get_project_for_user(db, db_work_item.project_id, current_user.company_id)
    crud.delete_work_item(db, work_item_id=work_item_id)
    return Response(status_code=204)

@app.post("/projects/{project_id}/contracts/", response_model=schemas.Contract, status_code=201)
def create_contract_for_project_endpoint(
    project_id: int, 
    contract: schemas.ContractCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    return crud.create_contract(db=db, contract=contract, project_id=project_id)
@app.get("/projects/{project_id}/contracts/", response_model=List[schemas.Contract])
def read_project_contracts_endpoint(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    return crud.get_project_contracts(db=db, project_id=project_id)
@app.get("/contracts/{contract_id}", response_model=schemas.Contract)
def read_contract_by_id_endpoint(
    contract_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_contract = crud.get_contract_details(db, contract_id=contract_id)
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    get_project_for_user(db, db_contract.project_id, current_user.company_id)
    return db_contract
@app.put("/contracts/{contract_id}", response_model=schemas.Contract)
def update_contract_endpoint(
    contract_id: int,
    contract_update: schemas.ContractUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_contract = crud.get_contract(db, contract_id=contract_id)
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    get_project_for_user(db, db_contract.project_id, current_user.company_id)
    db_contract_updated = crud.update_contract(db, contract_id=contract_id, contract_update=contract_update)
    return db_contract_updated
@app.delete("/contracts/{contract_id}", status_code=204)
def delete_contract_endpoint(
    contract_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_admin)
):
    db_contract = crud.get_contract(db, contract_id=contract_id)
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    get_project_for_user(db, db_contract.project_id, current_user.company_id)
    crud.delete_contract(db, contract_id=contract_id)
    return Response(status_code=204)

@app.post("/projects/{project_id}/import-contracts/", status_code=201)
async def import_contracts_endpoint(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)):
    get_project_for_user(db, project_id, current_user.company_id)
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Se requiere .xlsx")
    
    file_contents = await file.read()
    try:
        result = await run_in_threadpool(
            crud.import_contracts_from_excel, db=db, project_id=project_id, file_contents=file_contents
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {e}")

@app.get("/projects/{project_id}/export-contracts/")
def export_contracts_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)):
    get_project_for_user(db, project_id, current_user.company_id)
    try:
        excel_bytes = crud.export_contracts_to_excel(db=db, project_id=project_id)
        filename = f"proyecto_{project_id}_contratos.xlsx"
        return StreamingResponse(
            excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando el archivo de contratos: {e}")

@app.post("/contracts/{contract_id}/items/", response_model=schemas.ContractItem)
def create_contract_item_endpoint(
    contract_id: int,
    item: schemas.ContractItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_contract = crud.get_contract(db, contract_id=contract_id)
    if not db_contract or db_contract.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    return crud.create_contract_item(db=db, item=item, contract_id=contract_id)
@app.put("/contract_items/{item_id}", response_model=schemas.ContractItem)
def update_contract_item_endpoint(
    item_id: int,
    item_update: schemas.ContractItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_item = crud.get_contract_item(db, item_id=item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item de contrato no encontrado")
    get_project_for_user(db, db_item.contract.project_id, current_user.company_id)
    return crud.update_contract_item(db, item_id=item_id, item_update=item_update)
@app.delete("/contract_items/{item_id}", status_code=204)
def delete_contract_item_endpoint(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_item = crud.get_contract_item(db, item_id=item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item de contrato no encontrado")
    get_project_for_user(db, db_item.contract.project_id, current_user.company_id)
    crud.delete_contract_item(db, item_id=item_id)
    return Response(status_code=204)
@app.post("/contracts/{contract_id}/import_items/", status_code=201)
async def import_contract_items_endpoint(
    contract_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    db_contract = crud.get_contract_for_permission_check(db, contract_id=contract_id)
    if not db_contract:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    
    if current_user.role != "super_admin" and db_contract.project.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar este contrato")

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido.")
    file_contents = await file.read()
    try:
        result = await run_in_threadpool(
            crud.import_contract_items_from_excel, 
            db=db, contract_id=contract_id, file_contents=file_contents
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {e}")
@app.get("/contracts/{contract_id}/export_items/")
def export_contract_items_endpoint(
    contract_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_contract = crud.get_contract(db, contract_id=contract_id)
    if not db_contract or db_contract.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    try:
        excel_bytes = crud.export_contract_items_to_excel(db=db, contract_id=contract_id)
        filename = f"contrato_{db_contract.numero_contrato}_catalogo.xlsx"
        return StreamingResponse(
            excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando el archivo: {e}")

@app.post("/projects/{project_id}/estimates/", response_model=schemas.Estimate, status_code=201)
def create_estimate_for_project_endpoint(
    project_id: int, 
    estimate: schemas.EstimateCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    return crud.create_estimate(db=db, estimate=estimate, project_id=project_id)
@app.get("/projects/{project_id}/estimates/", response_model=List[schemas.Estimate])
def read_project_estimates_endpoint(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    return crud.get_project_estimates(db=db, project_id=project_id)
@app.get("/estimates/{estimate_id}", response_model=schemas.Estimate)
def read_estimate_by_id_endpoint(
    estimate_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_estimate = crud.get_estimate(db, estimate_id=estimate_id)
    if not db_estimate:
        raise HTTPException(status_code=404, detail="Estimación no encontrada")
    get_project_for_user(db, db_estimate.project_id, current_user.company_id)
    return db_estimate
@app.put("/estimates/{estimate_id}", response_model=schemas.Estimate)
def update_estimate_endpoint(
    estimate_id: int,
    estimate_update: schemas.EstimateUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_estimate = crud.get_estimate(db, estimate_id=estimate_id)
    if not db_estimate:
        raise HTTPException(status_code=404, detail="Estimación no encontrada")
    get_project_for_user(db, db_estimate.project_id, current_user.company_id)
    db_estimate_updated = crud.update_estimate(db, estimate_id=estimate_id, estimate_update=estimate_update)
    return db_estimate_updated
@app.delete("/estimates/{estimate_id}", status_code=204)
def delete_estimate_endpoint(
    estimate_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_admin)
):
    db_estimate = crud.get_estimate(db, estimate_id=estimate_id)
    if not db_estimate:
        raise HTTPException(status_code=404, detail="Estimación no encontrada")
    get_project_for_user(db, db_estimate.project_id, current_user.company_id) # Verifica pertenencia
    crud.delete_estimate(db, estimate_id=estimate_id)
    return Response(status_code=204)
@app.post("/projects/{project_id}/import-estimates/", status_code=201)
async def import_estimates_endpoint(
    project_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido.")
    
    file_contents = await file.read()
    try:
        result = await run_in_threadpool(crud.import_estimates_from_excel, db=db, project_id=project_id, file_contents=file_contents)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {e}")

@app.get("/projects/{project_id}/export-estimates/")
def export_estimates_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    try:
        excel_bytes = crud.export_estimates_to_excel(db=db, project_id=project_id)
        filename = f"proyecto_{project_id}_estimaciones.xlsx"
        return StreamingResponse(
            excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando el archivo: {e}")

@app.post("/estimates/{estimate_id}/items/", response_model=schemas.EstimateItem)
def create_estimate_item_endpoint(
    estimate_id: int,
    item: schemas.EstimateItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_estimate = crud.get_estimate(db, estimate_id=estimate_id)
    if not db_estimate or db_estimate.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Estimación no encontrada")
    return crud.create_estimate_item(db=db, item=item, estimate_id=estimate_id)
@app.put("/estimate_items/{item_id}", response_model=schemas.EstimateItem)
def update_estimate_item_endpoint(
    item_id: int,
    item_update: schemas.EstimateItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_item = crud.get_estimate_item(db, item_id=item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item de estimación no encontrado")
    get_project_for_user(db, db_item.estimate.project_id, current_user.company_id)
    return crud.update_estimate_item(db, item_id=item_id, item_update=item_update)
@app.delete("/estimate_items/{item_id}", status_code=204)
def delete_estimate_item_endpoint(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_item = crud.get_estimate_item(db, item_id=item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item de estimación no encontrado")
    get_project_for_user(db, db_item.estimate.project_id, current_user.company_id)
    crud.delete_estimate_item(db, item_id=item_id)
    return Response(status_code=204)

@app.post("/projects/{project_id}/folders/", response_model=schemas.Folder)
def create_folder_endpoint(
    project_id: int,
    folder: schemas.FolderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    get_project_for_user(db, project_id, current_user.company_id)
    return crud.create_folder(db=db, folder=folder, project_id=project_id)
@app.get("/folders/{folder_id}", response_model=schemas.Folder)
def get_folder_contents_endpoint(
    folder_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    db_folder = crud.get_folder_contents(db=db, folder_id=folder_id)
    if not db_folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    if current_user.role != "super_admin":
        get_project_for_user(db, db_folder.project_id, current_user.company_id)
    return db_folder
@app.put("/folders/{folder_id}/rename", response_model=schemas.Folder)
def rename_folder_endpoint(
    folder_id: int,
    folder_update: schemas.FolderBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    db_folder = crud.get_folder_contents(db, folder_id=folder_id)
    if not db_folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    if current_user.role != "super_admin":
        get_project_for_user(db, db_folder.project_id, current_user.company_id)
    db_folder_renamed = crud.rename_folder(db=db, folder_id=folder_id, new_name=folder_update.name)
    return db_folder_renamed
@app.delete("/folders/{folder_id}", status_code=204)
def delete_folder_endpoint(
    folder_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    db_folder = crud.get_folder_contents(db, folder_id=folder_id)
    if not db_folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    if current_user.role != "super_admin":
        get_project_for_user(db, db_folder.project_id, current_user.company_id)
    try:
        crud.delete_folder(db=db, folder_id=folder_id)
        return Response(status_code=204)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")
@app.post("/documents/", response_model=schemas.Document)
def create_document_concept_endpoint(
    document: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    db_folder = crud.get_folder_contents(db, folder_id=document.folder_id)
    if not db_folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    if current_user.role != "super_admin":
        get_project_for_user(db, db_folder.project_id, current_user.company_id)
    return crud.create_document_concept(db=db, document=document)

@app.delete("/documents/{document_id}", status_code=204)
def delete_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    db_doc = crud.get_document_concept_with_project(db, document_id)
    if not db_doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if current_user.role != "super_admin":
        get_project_for_user(db, db_doc.folder.project_id, current_user.company_id)
    crud.delete_document_and_versions(db=db, document_id=document_id)
    return Response(status_code=204)

@app.post("/documents/{document_id}/upload_version/", response_model=schemas.DocumentVersion)
async def upload_document_version_endpoint(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    db_doc = crud.get_document_concept_with_project(db, document_id)
    if not db_doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if current_user.role != "super_admin":
        get_project_for_user(db, db_doc.folder.project_id, current_user.company_id)        
    db_version = await run_in_threadpool(crud.create_new_document_version, db=db, file=file, document_id=document_id)
    if not db_version:
        raise HTTPException(status_code=404, detail="El 'Documento' conceptual no existe")
    return db_version
@app.get("/documents/file/{version_id}")
def get_document_file(
    version_id: int, 
    format: str = "ifc",  # <--- Agregamos este parámetro opcional
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    db_version = crud.get_document_version(db, version_id=version_id)
    if not db_version:
        raise HTTPException(status_code=404, detail="Versión del documento no encontrada")
    
    # Validación de permisos (sin cambios)
    if current_user.role != "super_admin":
        db_doc = crud.get_document_concept_with_project(db, db_version.document_id)
        get_project_for_user(db, db_doc.folder.project_id, current_user.company_id)
    
    file_path = db_version.file_path
    
    # --- LÓGICA NUEVA PARA SERVIR FRAGMENTS ---
    if format == "frag":
        # Cambiamos la extensión del path original (.ifc) a .frag
        # Asumimos que el convertidor ya creó este archivo en la misma carpeta
        file_path = file_path.rsplit('.', 1)[0] + ".frag"
        media_type = "application/octet-stream"
        filename = db_version.filename.rsplit('.', 1)[0] + ".frag"
    else:
        # Comportamiento normal (IFC)
        media_type = db_version.file_type
        filename = db_version.filename
    # ------------------------------------------

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado en el servidor: {file_path}")
        
    return FileResponse(path=file_path, media_type=media_type, filename=filename)
@app.post("/link/document/{document_id}/contract/{contract_id}")
def link_document_contract_endpoint(
    document_id: int,
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_company_user)
):
    db_contract = crud.get_contract(db, contract_id)
    if not db_contract or db_contract.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    crud.link_document_to_contract(db=db, document_id=document_id, contract_id=contract_id)
    return {"message": "Documento vinculado exitosamente al contrato."}
