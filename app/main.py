# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
from jose import JWTError, jwt

# Importamos todo desde nuestros nuevos archivos
from . import crud, models, schemas, security
from .database import get_db, engine # Import engine

# Esto crea las tablas en la BD si no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ConTech PM API")

# --- Dependencia de Seguridad ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


# === Endpoints de Autenticación ===

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

# === Endpoints de Proyectos ===

@app.post("/projects/", response_model=schemas.Project, status_code=201)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.create_project(db=db, project=project, owner_id=current_user.id)

@app.get("/projects/", response_model=List[schemas.Project])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    projects = crud.get_projects(db=db, skip=skip, limit=limit)
    return [schemas.Project.from_orm(p) for p in projects]

@app.get("/projects/{project_id}", response_model=schemas.Project)
def get_project_by_id(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_project = crud.get_project(db=db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if db_project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    project_schema = schemas.Project.from_orm(db_project)
    project_schema.tasks = crud.get_project_tasks_as_tree(db=db, project_id=project_id)
    return project_schema

# === Endpoints de Tareas ===

@app.post("/projects/{project_id}/tasks/", response_model=schemas.Task, status_code=201)
def create_task_for_project(project_id: int, task: schemas.TaskCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_project = crud.get_project(db=db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if db_project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this project")

    if task.parent_id:
        parent = db.query(models.Task).filter(models.Task.id == task.parent_id).first()
        if not parent or parent.project_id != project_id:
            raise HTTPException(status_code=400, detail="ID de tarea padre no válido")

    return crud.create_task(db=db, task=task, project_id=project_id)

@app.post("/projects/{project_id}/import-excel/", status_code=201)
async def import_project_tasks_excel(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_project = crud.get_project(db=db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if db_project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to import tasks to this project")

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Se requiere .xlsx")

    file_contents = await file.read()

    try:
        result = crud.import_tasks_from_excel(
            db=db,
            project_id=project_id,
            file_contents=file_contents
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {e}")
