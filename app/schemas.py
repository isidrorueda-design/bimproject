# app/schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

# --- Modelo Base para Tarea ---
class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    parent_id: Optional[int] = None # Permitimos recibir un ID de padre

# Schema para crear una tarea (usado en el POST)
class TaskCreate(TaskBase):
    pass

# Schema para LEER una tarea (lo que devolvemos)
class Task(TaskBase):
    id: int
    project_id: int
    subtasks: List["Task"] = [] # ¡Recursivo! Lista de tareas hijas

    class Config:
        orm_mode = True # Ahora se llama 'from_attributes' en Pydantic v2

# Reconstruimos las referencias (para que `subtasks: List["Task"]` funcione)
Task.model_rebuild()

# --- Modelo Base para Proyecto ---
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    tasks: List[Task] = [] # Devolverá solo las tareas RAÍZ

    class Config:
        orm_mode = True