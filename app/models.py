# app/models.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)

    # Relación: Un proyecto tiene muchas tareas
    tasks = relationship("Task", back_populates="project")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    
    project_id = Column(Integer, ForeignKey("projects.id"))

    # --- ¡Aquí está la magia del árbol! ---
    # Un ID que apunta a otra tarea en esta misma tabla
    parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)

    # Relaciones de SQLAlchemy para el árbol:
    # 1. Una tarea tiene muchas "subtasks" (hijos)
    subtasks = relationship("Task", back_populates="parent")
    # 2. Una tarea tiene un "parent" (padre)
    parent = relationship("Task", back_populates="subtasks", remote_side=[id])
    # -------------------------------------

    project = relationship("Project", back_populates="tasks")