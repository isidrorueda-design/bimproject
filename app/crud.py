# app/crud.py
from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Dict
import openpyxl
import io

def import_tasks_from_excel(db: Session, project_id: int, file_contents: bytes):
    """
    Importa tareas desde un archivo Excel (bytes) a un proyecto.
    
    Asume un formato de Excel específico:
    - Columna A: Nivel (ej. 1, 2, 3...)
    - Columna B: Nombre de la Tarea
    - Columna C: Fecha de Inicio (YYYY-MM-DD)
    - Columna D: Fecha de Fin (YYYY-MM-DD)
    - Columna E: Descripción (Opcional)
    """
    
    # Carga el archivo Excel desde los bytes en memoria
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active

    # --- Lógica de Jerarquía ---
    # Usaremos un diccionario para rastrear el ID del padre MÁS RECIENTE en cada nivel.
    # Ej: {1: task_id_A, 2: task_id_B, 3: task_id_C}
    # Si llega una tarea Nivel 3, su padre es task_id_C.
    # Si llega una tarea Nivel 2, su padre es task_id_A.
    last_parent_at_level: Dict[int, int] = {}
    
    tasks_created = 0
    
    # Iteramos por las filas, saltando el encabezado (fila 1)
    for row in sheet.iter_rows(min_row=2, values_only=True):
        try:
            level = int(row[0])
            name = str(row[1])
            start_date = row[2]
            end_date = row[3]
            description = str(row[4]) if row[4] else None

            if not name or not start_date or not end_date:
                # Si faltan datos clave, saltamos la fila
                continue

            parent_id = None
            if level > 1:
                # Si no es nivel 1, buscamos su padre en el nivel anterior (level - 1)
                parent_id = last_parent_at_level.get(level - 1)
            
            # 1. Creamos el Schema de la tarea
            task_schema = schemas.TaskCreate(
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date,
                parent_id=parent_id
            )
            
            # 2. Creamos la Tarea en la BD usando nuestra función CRUD existente
            db_task = create_task(db=db, task=task_schema, project_id=project_id)
            
            # 3. Actualizamos nuestro rastreador de jerarquía
            # Guardamos esta tarea como el último padre de SU nivel
            last_parent_at_level[level] = db_task.id
            
            # Limpiamos los niveles inferiores para evitar errores
            # (Si creamos un Nivel 2, ya no puede haber un Nivel 3 "hijo" del anterior)
            levels_to_clear = [lvl for lvl in last_parent_at_level if lvl > level]
            for lvl in levels_to_clear:
                del last_parent_at_level[lvl]

            tasks_created += 1

        except Exception as e:
            # En una app real, aquí registrarías el error
            print(f"Error procesando fila: {row}. Error: {e}")
            continue
            
    return {"message": f"{tasks_created} tareas importadas exitosamente."}
# === Funciones de Proyecto ===

def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Project).offset(skip).limit(limit).all()

def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

# === Funciones de Tarea ===

def create_task(db: Session, task: schemas.TaskCreate, project_id: int):
    db_task = models.Task(**task.model_dump(), project_id=project_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_project_tasks(db: Session, project_id: int):
    """
    Obtiene TODAS las tareas de un proyecto, pero como una lista plana.
    """
    return db.query(models.Task).filter(models.Task.project_id == project_id).all()

def get_project_tasks_as_tree(db: Session, project_id: int) -> List[schemas.Task]:
    """
    ¡Función clave! Obtiene todas las tareas y las ensambla en un árbol.
    """
    # 1. Obtenemos todas las tareas del proyecto de la BD
    db_tasks = get_project_tasks(db=db, project_id=project_id)
    
    # 2. Convertimos los modelos de BD (models.Task) a schemas (schemas.Task)
    #    y las ponemos en un mapa para acceso rápido por ID.
    task_schema_map = {}
    for db_task in db_tasks:
        task_schema = schemas.Task.from_orm(db_task)
        task_schema_map[task_schema.id] = task_schema

    # 3. Construimos el árbol
    root_tasks = []
    for task_id, task in task_schema_map.items():
        if task.parent_id:
            # Si tiene padre, la encontramos en el mapa...
            parent_task = task_schema_map.get(task.parent_id)
            if parent_task:
                # ...y la añadimos a la lista de 'subtasks' del padre.
                parent_task.subtasks.append(task)
        else:
            # Si no tiene padre, es una tarea raíz.
            root_tasks.append(task)
            
    return root_tasks