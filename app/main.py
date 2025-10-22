# app/main.py
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

# Importamos todo desde nuestros nuevos archivos
from . import crud, models, schemas
from .database import get_db

# Esto crea las tablas en la BD si no existen
# (lo detecta al correr models.py)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ConTech PM API")


# === Endpoints de Proyectos ===

@app.post("/projects/", response_model=schemas.Project, status_code=201)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    # La lógica ahora está en crud.py
    return crud.create_project(db=db, project=project)

@app.get("/projects/", response_model=List[schemas.Project])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    projects = crud.get_projects(db=db, skip=skip, limit=limit)
    # Convertimos la lista de BD a la lista de Schemas
    return [schemas.Project.from_orm(p) for p in projects]

@app.get("/projects/{project_id}", response_model=schemas.Project)
def get_project_by_id(project_id: int, db: Session = Depends(get_db)):
    db_project = crud.get_project(db=db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Convertimos el proyecto de BD a Schema
    project_schema = schemas.Project.from_orm(db_project)
    
    # ¡Usamos nuestra nueva función para obtener el árbol de tareas!
    project_schema.tasks = crud.get_project_tasks_as_tree(db=db, project_id=project_id)
    return project_schema

# === Endpoints de Tareas ===

@app.post("/projects/{project_id}/tasks/", response_model=schemas.Task, status_code=201)
def create_task_for_project(project_id: int, task: schemas.TaskCreate, db: Session = Depends(get_db)):
    # Verificamos que el proyecto exista
    db_project = crud.get_project(db=db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
    # (Opcional) Verificar que el parent_id (si existe) sea válido
    if task.parent_id:
        parent = db.query(models.Task).filter(models.Task.id == task.parent_id).first()
        if not parent or parent.project_id != project_id:
            raise HTTPException(status_code=400, detail="ID de tarea padre no válido")
            
    return crud.create_task(db=db, task=task, project_id=project_id)
@app.post("/projects/{project_id}/import-excel/", status_code=201)
async def import_project_tasks_excel(
    project_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Importa tareas desde un archivo Excel (.xlsx).
    
    El archivo debe tener las columnas:
    A: Nivel, B: Nombre, C: Fecha Inicio, D: Fecha Fin, E: Descripción
    """
    db_project = crud.get_project(db=db, project_id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificamos que sea un archivo Excel
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato de archivo inválido. Se requiere .xlsx")
        
    # Leemos el contenido del archivo en bytes
    file_contents = await file.read()
    
    try:
        # Llamamos a nuestra nueva función CRUD
        result = crud.import_tasks_from_excel(
            db=db, 
            project_id=project_id, 
            file_contents=file_contents
        )
        return result
    except Exception as e:
        # Capturamos errores generales (ej. archivo corrupto)
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {e}")