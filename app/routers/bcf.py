# app/routers/bcf.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas, dependencies
from ..database import get_db

router = APIRouter(
    prefix="/bcf",
    tags=["BCF"],
    responses={404: {"description": "Not found"}},
)

@router.get("/projects/{project_id}/topics", response_model=List[schemas.BCFTopic])
def read_project_topics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    """
    Obtiene todos los BCF Topics para un proyecto específico.
    """
    # Verificar que el usuario tiene acceso al proyecto
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    return crud.get_bcf_topics_by_project(db=db, project_id=project_id)

@router.post("/projects/{project_id}/topics", response_model=schemas.BCFTopic, status_code=status.HTTP_201_CREATED)
def create_project_topic(
    project_id: int,
    topic: schemas.BCFTopicCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    """
    Crea un nuevo BCF Topic, junto con sus viewpoints y comentarios iniciales, para un proyecto.
    """
    db_project = crud.get_project(db, project_id=project_id)
    if not db_project or db_project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    return crud.create_bcf_topic(db=db, topic_data=topic, project_id=project_id, author_email=current_user.email)

@router.get("/topics/{topic_guid}", response_model=schemas.BCFTopic)
def read_topic_details(
    topic_guid: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    """
    Obtiene los detalles completos de un BCF Topic por su GUID.
    """
    db_topic = crud.get_bcf_topic(db, topic_guid=topic_guid)
    if not db_topic or db_topic.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="BCF Topic no encontrado")
    return db_topic

@router.put("/topics/{topic_guid}", response_model=schemas.BCFTopic)
def update_topic(
    topic_guid: str,
    topic_update: schemas.BCFTopicUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user_in_company)
):
    db_topic = crud.get_bcf_topic(db, topic_guid=topic_guid)
    if not db_topic or db_topic.project.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="BCF Topic no encontrado")
    
    return crud.update_bcf_topic(db=db, topic_guid=topic_guid, topic_update=topic_update, author_email=current_user.email)