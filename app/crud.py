import os
import shutil
import uuid
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func
from typing import List, Dict
from datetime import date
import openpyxl
import io
import pandas as pd

from . import models, schemas, security 
UPLOAD_DIRECTORY = "uploads"

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    """
    Crea un nuevo usuario con una contraseña hasheada.
    """
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        email=user.email, 
        hashed_password=hashed_password,
        company_id=user.company_id,
        role=user.role  # <-- Añadir esta línea
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_company(db: Session, company_id: int):
    return db.query(models.Company).filter(models.Company.id == company_id).first()

def get_company_by_name(db: Session, name: str):
    return db.query(models.Company).filter(models.Company.name == name).first()

def create_company(db: Session, company: schemas.CompanyCreate):
    db_company = models.Company(name=company.name)
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

def authenticate_user(db: Session, email: str, password: str):
    """
    Verifica el email y la contraseña para el login.
    Devuelve el usuario si tiene éxito, o False si no.
    """
    user = get_user_by_email(db, email=email)
    if not user:
        return False # El usuario no existe
    if not security.verify_password(password, user.hashed_password):
        return False 
    
    return user 

def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_projects(db: Session, company_id: int, skip: int = 0, limit: int = 100):

    return db.query(models.Project).filter(
        models.Project.company_id == company_id
    ).offset(skip).limit(limit).all()

def get_project_details(db: Session, project_id: int, company_id: int):
    """
    Obtiene los detalles de un proyecto, verificando que pertenezca a la compañía.
    """
    return db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.company_id == company_id
    ).options(
        joinedload(models.Project.company).joinedload(models.Company.users),
        joinedload(models.Project.tasks).options(joinedload(models.Task.responsible_user)),
        joinedload(models.Project.work_items).options(
            joinedload(models.WorkItem.contracts).options(
                joinedload(models.Contract.contractor),
                joinedload(models.Contract.work_item)
            )
        ),
        joinedload(models.Project.contracts).options(
            joinedload(models.Contract.contractor),
            joinedload(models.Contract.work_item)
        ),
        joinedload(models.Project.estimates).options(
            joinedload(models.Estimate.contract).options(
                joinedload(models.Contract.contractor),
                joinedload(models.Contract.work_item)
            )
        )
    ).first()

def create_project(db: Session, project: schemas.ProjectCreate):
    # El 'company_id' viene en el schema 'ProjectCreate'
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def delete_project_by_id(db: Session, project_id: int, company_id: int):

    db_project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.company_id == company_id
    ).first()
    if not db_project:
        return None
    
    db.delete(db_project)
    db.commit()
    return db_project
def update_project(db: Session, project_id: int, project_update: schemas.ProjectUpdate, company_id: int):

    db_project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.company_id == company_id
    ).first()
    
    if not db_project:
        return None
    update_data = project_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_project, key, value)
        
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def create_task(db: Session, task: schemas.TaskCreate, project_id: int):
    db_task = models.Task(**task.model_dump(), project_id=project_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task(db: Session, task_id: int):
    """Obtiene una tarea específica con su proyecto cargado."""
    return db.query(models.Task).options(joinedload(models.Task.project)).filter(models.Task.id == task_id).first()

def update_task(db: Session, task_id: int, task_update: schemas.TaskUpdate):
    """Actualiza una tarea."""
    db_task = get_task(db, task_id=task_id)
    if not db_task:
        return None
    
    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
        
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_project_tasks(db: Session, project_id: int):
    return db.query(models.Task).filter(models.Task.project_id == project_id).all()

def get_project_tasks_as_tree(db: Session, project_id: int) -> List[schemas.Task]:
    db_tasks = get_project_tasks(db=db, project_id=project_id)
    task_schema_map = {}
    for db_task in db_tasks:
        task_schema = schemas.Task.from_orm(db_task)
        task_schema.subtasks = []
        task_schema_map[task_schema.id] = task_schema
    root_tasks = []
    for task_id, task in task_schema_map.items():
        if task.parent_id:
            parent_task = task_schema_map.get(task.parent_id)
            if parent_task:
                parent_task.subtasks.append(task)
        else:
            root_tasks.append(task)
    
    def _calculate_parent_dates(task: schemas.Task):
        if not task.subtasks:
            return task.start_date, task.end_date
        min_start, max_end = date.max, date.min
        for subtask in task.subtasks:
            child_start, child_end = _calculate_parent_dates(subtask)
            if child_start < min_start: min_start = child_start
            if child_end > max_end: max_end = child_end
        task.start_date, task.end_date = min_start, max_end
        return min_start, max_end

    for root_task in root_tasks:
        _calculate_parent_dates(root_task)
            
    return root_tasks
    
def import_tasks_from_excel(db: Session, project_id: int, file_contents: bytes):
    # ... (Esta función no necesita cambios, ya que la seguridad
    # se maneja en el endpoint de main.py)
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active
    last_parent_at_level: Dict[int, int] = {}
    tasks_created = 0
    for row in sheet.iter_rows(min_row=2, values_only=True):
        try:
            level, name, start_date, end_date = int(row[0]), str(row[1]), row[2], row[3]
            description = str(row[4]) if row[4] else None
            if not name or not start_date or not end_date: continue
            parent_id = last_parent_at_level.get(level - 1) if level > 1 else None
            task_schema = schemas.TaskCreate(
                name=name, description=description, start_date=start_date,
                end_date=end_date, parent_id=parent_id
            )
            db_task = create_task(db=db, task=task_schema, project_id=project_id)
            last_parent_at_level[level] = db_task.id
            levels_to_clear = [lvl for lvl in last_parent_at_level if lvl > level]
            for lvl in levels_to_clear: del last_parent_at_level[lvl]
            tasks_created += 1
        except Exception as e:
            print(f"Error procesando fila: {row}. Error: {e}")
            continue
    return {"message": f"{tasks_created} tareas importadas exitosamente."}


def create_contractor(db: Session, contractor: schemas.ContractorCreate):
    # company_id viene del schema
    db_contractor = models.Contractor(**contractor.model_dump())
    db.add(db_contractor)
    db.commit()
    db.refresh(db_contractor)
    return db_contractor

def get_contractors(db: Session, company_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Contractor).filter(
        models.Contractor.company_id == company_id
    ).offset(skip).limit(limit).all()

def get_contractor(db: Session, contractor_id: int, company_id: int):
    return db.query(models.Contractor).filter(
        models.Contractor.id == contractor_id,
        models.Contractor.company_id == company_id
    ).first()

def get_contractor_by_razon_social(db: Session, razon_social: str, company_id: int):
    return db.query(models.Contractor).filter(
        models.Contractor.razon_social == razon_social,
        models.Contractor.company_id == company_id
    ).first()

def update_contractor(db: Session, contractor_id: int, contractor_update: schemas.ContractorUpdate, company_id: int):
    db_contractor = get_contractor(db, contractor_id=contractor_id, company_id=company_id)
    if not db_contractor:
        return None
    update_data = contractor_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_contractor, key, value)
    db.add(db_contractor)
    db.commit()
    db.refresh(db_contractor)
    return db_contractor

def delete_contractor(db: Session, contractor_id: int, company_id: int):
    db_contractor = get_contractor(db, contractor_id=contractor_id, company_id=company_id)
    if not db_contractor:
        return None
    db.delete(db_contractor)
    db.commit()
    return db_contractor

def import_contractors_from_excel(db: Session, file_contents: bytes, company_id: int):
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active
    created_count = 0
    skipped_count = 0
    
    for row in sheet.iter_rows(min_row=2, values_only=True):
        try:
            razon_social = str(row[0]).strip()
            if not razon_social: continue
            
            db_contractor = get_contractor_by_razon_social(db, razon_social=razon_social, company_id=company_id)
            if db_contractor:
                skipped_count += 1
                continue

            contractor_data = schemas.ContractorCreate(
                razon_social=razon_social,
                responsable=str(row[1]) if row[1] else None,
                telefono=str(row[2]) if row[2] else None,
                correo_electronico=str(row[3]) if row[3] else None,
                company_id=company_id # <-- Vínculo a la empresa
            )
            create_contractor(db=db, contractor=contractor_data)
            created_count += 1
        except Exception as e:
            print(f"Error procesando fila de contratista: {row}. Error: {e}")
            continue
            
    return {"message": f"{created_count} contratistas creados, {skipped_count} omitidos (duplicados)."}

def create_work_item(db: Session, work_item: schemas.WorkItemCreate, project_id: int):
    db_work_item = models.WorkItem(**work_item.model_dump(), project_id=project_id)
    db.add(db_work_item)
    db.commit()
    db.refresh(db_work_item)
    return db_work_item

def get_project_work_items(db: Session, project_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.WorkItem).filter(models.WorkItem.project_id == project_id).options(
        joinedload(models.WorkItem.contracts).options(
            joinedload(models.Contract.contractor),
            joinedload(models.Contract.work_item)
        )
    ).offset(skip).limit(limit).all()

def get_work_item(db: Session, work_item_id: int):
    return db.query(models.WorkItem).filter(models.WorkItem.id == work_item_id).options(
        joinedload(models.WorkItem.contracts).options(
            joinedload(models.Contract.contractor),
            joinedload(models.Contract.work_item)
        )
    ).first()

def update_work_item(db: Session, work_item_id: int, work_item_update: schemas.WorkItemUpdate):
    db_work_item = get_work_item(db, work_item_id=work_item_id)
    if not db_work_item: return None
    update_data = work_item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_work_item, key, value)
    db.add(db_work_item)
    db.commit()
    db.refresh(db_work_item)
    return db_work_item

def delete_work_item(db: Session, work_item_id: int):
    db_work_item = get_work_item(db, work_item_id=work_item_id)
    if not db_work_item: return None
    db.delete(db_work_item)
    db.commit()
    return db_work_item

# === FUNCIONES DE CONTRATOS (TABLA 3) ===
def create_contract(db: Session, contract: schemas.ContractCreate, project_id: int):
    db_contract = models.Contract(**contract.model_dump(), project_id=project_id)
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    # Recargamos con las relaciones
    return get_contract(db, db_contract.id)

def get_project_contracts(db: Session, project_id: int):
    return db.query(models.Contract).filter(models.Contract.project_id == project_id).options(
        joinedload(models.Contract.contractor),
        joinedload(models.Contract.work_item)
    ).all()

def get_contract(db: Session, contract_id: int):
    return db.query(models.Contract).filter(models.Contract.id == contract_id).options(
        joinedload(models.Contract.contractor),
        joinedload(models.Contract.work_item)
    ).first()

def update_contract(db: Session, contract_id: int, contract_update: schemas.ContractUpdate):
    db_contract = db.query(models.Contract).filter(models.Contract.id == contract_id).first()
    if not db_contract: return None
    update_data = contract_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_contract, key, value)
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    return get_contract(db, contract_id=contract_id)

def delete_contract(db: Session, contract_id: int):
    db_contract = get_contract(db, contract_id=contract_id)
    if not db_contract: return None
    db.delete(db_contract)
    db.commit()
    return db_contract

def import_contracts_from_excel(db: Session, project_id: int, file_contents: bytes, company_id: int):
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active
    created_count = 0
    errors = []
    
    # Mapas de búsqueda (restringidos a la compañía y proyecto)
    contractors_map = {c.razon_social: c.id for c in db.query(models.Contractor).filter(models.Contractor.company_id == company_id).all()}
    work_items_map = {w.item_code: w.id for w in db.query(models.WorkItem).filter(models.WorkItem.project_id == project_id).all()}

    for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        try:
            numero_contrato, razon_social_contratista, codigo_partida = str(row[0]), str(row[1]), str(row[2])
            if not all([numero_contrato, razon_social_contratista, codigo_partida]):
                errors.append(f"Fila {i}: Faltan datos obligatorios.")
                continue
            
            contractor_id = contractors_map.get(razon_social_contratista)
            if not contractor_id:
                errors.append(f"Fila {i}: No se encontró el Contratista '{razon_social_contratista}'.")
                continue
                
            work_item_id = work_items_map.get(codigo_partida)
            if not work_item_id:
                errors.append(f"Fila {i}: No se encontró la Partida '{codigo_partida}'.")
                continue

            contract_data = schemas.ContractCreate(
                numero_contrato=numero_contrato,
                contractor_id=contractor_id,
                work_item_id=work_item_id,
                trabajos=str(row[3]) if row[3] else None,
                contratado=float(row[4]) if row[4] else 0.0,
                aditiva=float(row[5]) if row[5] else 0.0,
                deductiva=float(row[6]) if row[6] else 0.0,
                anticipo=float(row[7]) if row[7] else 0.0,
                aplica_iva=True if str(row[8]).lower() == 'si' else False
            )
            create_contract(db=db, contract=contract_data, project_id=project_id)
            created_count += 1
        except Exception as e:
            errors.append(f"Fila {i}: Error inesperado - {e}")
            continue
    return {"message": f"{created_count} contratos creados.", "errors": errors}

def export_contracts_to_excel(db: Session, project_id: int):
    contracts = get_project_contracts(db=db, project_id=project_id)
    if not contracts:
        # Devolvemos un BytesIO vacío si no hay datos
        return io.BytesIO()
    data_list = []
    for c in contracts:
        data_list.append({
            "No. Contrato": c.numero_contrato,
            "Contratista": c.contractor.razon_social,
            "Código Partida": c.work_item.item_code,
            "Descripción Partida": c.work_item.description,
            "Trabajos": c.trabajos,
            "Contratado ($)": c.contratado,
            "Aditiva ($)": c.aditiva,
            "Deductiva ($)": c.deductiva,
            "Anticipo ($)": c.anticipo,
            "Aplica IVA": "SI" if c.aplica_iva else "NO",
            "Total (Calculado)": c.total,
            "IVA (Calculado)": c.iva,
            "Total c/IVA (Calculado)": c.total_con_iva,
        })
    df = pd.DataFrame(data_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Contratos', index=False)
    output.seek(0)
    return output

# === FUNCIONES DE ESTIMACIONES (TABLA 4) ===
def create_estimate(db: Session, estimate: schemas.EstimateCreate, project_id: int):
    db_estimate = models.Estimate(**estimate.model_dump(), project_id=project_id)
    db.add(db_estimate)
    db.commit()
    db.refresh(db_estimate)
    return get_estimate_by_id(db, db_estimate.id)

def get_project_estimates(db: Session, project_id: int):
    return db.query(models.Estimate).filter(models.Estimate.project_id == project_id).options(
        joinedload(models.Estimate.contract).options(
            joinedload(models.Contract.contractor),
            joinedload(models.Contract.work_item)
        )
    ).all()

def get_estimate_by_id(db: Session, estimate_id: int):
    return db.query(models.Estimate).filter(models.Estimate.id == estimate_id).options(
        joinedload(models.Estimate.contract).options(
            joinedload(models.Contract.contractor),
            joinedload(models.Contract.work_item)
        )
    ).first()

def update_estimate(db: Session, estimate_id: int, estimate_update: schemas.EstimateUpdate):
    db_estimate = db.query(models.Estimate).filter(models.Estimate.id == estimate_id).first()
    if not db_estimate: return None
    update_data = estimate_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_estimate, key, value)
    db.add(db_estimate)
    db.commit()
    db.refresh(db_estimate)
    return get_estimate_by_id(db, estimate_id=estimate_id)

def delete_estimate(db: Session, estimate_id: int):
    db_estimate = get_estimate_by_id(db, estimate_id=estimate_id)
    if not db_estimate: return None
    db.delete(db_estimate)
    db.commit()
    return db_estimate

def import_estimates_from_excel(db: Session, project_id: int, file_contents: bytes):
    workbook = openpyxl.load_workbook(io.BytesIO(file_contents))
    sheet = workbook.active
    created_count = 0
    errors = []
    
    contracts_map = {
        c.numero_contrato: c.id 
        for c in db.query(models.Contract).filter(models.Contract.project_id == project_id).all()
    }

    for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        try:
            numero_contrato = str(row[0])
            if not numero_contrato:
                errors.append(f"Fila {i}: Falta el Número de Contrato.")
                continue
            
            contract_id = contracts_map.get(numero_contrato)
            if not contract_id:
                errors.append(f"Fila {i}: No se encontró el Contrato '{numero_contrato}'.")
                continue
                
            estimate_data = schemas.EstimateCreate(
                contract_id=contract_id,
                estimado=float(row[1]) if row[1] else 0.0,
                deductiva_estimacion=float(row[2]) if row[2] else 0.0,
                amortizado=float(row[3]) if row[3] else 0.0,
                fondo_garantia=float(row[4]) if row[4] else 0.0,
                retenciones=float(row[5]) if row[5] else 0.0,
            )
            create_estimate(db=db, estimate=estimate_data, project_id=project_id)
            created_count += 1
        except Exception as e:
            errors.append(f"Fila {i}: Error inesperado - {e}")
            continue
    return {"message": f"{created_count} estimaciones creadas.", "errors": errors}

def export_estimates_to_excel(db: Session, project_id: int):
    estimates = get_project_estimates(db=db, project_id=project_id)
    if not estimates:
        return io.BytesIO()
    data_list = []
    for e in estimates:
        data_list.append({
            "No. Contrato": e.contract.numero_contrato,
            "Contratista": e.contract.contractor.razon_social,
            "Partida": e.contract.work_item.item_code,
            "Estimado ($)": e.estimado,
            "Deductiva ($)": e.deductiva_estimacion,
            "Amortizado ($)": e.amortizado,
            "Fondo Garantía ($)": e.fondo_garantia,
            "Retenciones ($)": e.retenciones,
            "Aplica IVA": "SI" if e.contract.aplica_iva else "NO",
            "Total (Calculado)": e.total,
            "IVA (Calculado)": e.iva,
            "Total c/IVA (Calculado)": e.total_con_iva,
        })
    df = pd.DataFrame(data_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Estimaciones', index=False)
    output.seek(0)
    return output

# === FUNCIONES DEL MÓDULO DMS ===
def create_folder(db: Session, folder: schemas.FolderCreate, project_id: int):
    db_folder = models.Folder(name=folder.name, parent_id=folder.parent_id, project_id=project_id)
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return db_folder

def get_all_project_folders(db: Session, project_id: int):
    return db.query(models.Folder).filter(models.Folder.project_id == project_id).all()

def get_folder_contents(db: Session, folder_id: int):
    return db.query(models.Folder).filter(models.Folder.id == folder_id).options(
        # Usamos selectinload para cargar colecciones de forma más eficiente
        joinedload(models.Folder.subfolders), 
        joinedload(models.Folder.documents).joinedload(models.Document.versions)
    ).first()

def rename_folder(db: Session, folder_id: int, new_name: str):
    db_folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
    if not db_folder: return None
    db_folder.name = new_name
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return db_folder

def delete_folder(db: Session, folder_id: int):
    db_folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
    if not db_folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    has_subfolders = db.query(models.Folder).filter(models.Folder.parent_id == folder_id).first()
    if has_subfolders:
        raise HTTPException(status_code=400, detail="No se puede eliminar: La carpeta contiene subcarpetas.")
    has_documents = db.query(models.Document).filter(models.Document.folder_id == folder_id).first()
    if has_documents:
        raise HTTPException(status_code=400, detail="No se puede eliminar: La carpeta contiene documentos.")
    db.delete(db_folder)
    db.commit()
    return True

def create_document_concept(db: Session, document: schemas.DocumentCreate):
    db_document = models.Document(name=document.name, folder_id=document.folder_id)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

def create_new_document_version(db: Session, file: UploadFile, document_id: int):
    db_document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not db_document:
        return None
    
    latest_version = db.query(func.max(models.DocumentVersion.version_number)).filter(
        models.DocumentVersion.document_id == document_id
    ).scalar() or 0
    new_version_number = latest_version + 1

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
    
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    file_size = os.path.getsize(file_path)

    db_version = models.DocumentVersion(
        document_id=document_id,
        version_number=new_version_number,
        filename=file.filename,
        file_path=file_path,
        file_type=file.content_type,
        file_size=file_size
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version

def get_document_version(db: Session, version_id: int):
    return db.query(models.DocumentVersion).filter(models.DocumentVersion.id == version_id).first()

def link_document_to_contract(db: Session, document_id: int, contract_id: int):
    statement = models.document_contract_link.insert().values(
        document_id=document_id, 
        contract_id=contract_id
    )
    db.execute(statement)
    db.commit()
    return True

def link_document_to_work_item(db: Session, document_id: int, work_item_id: int):
    statement = models.document_workitem_link.insert().values(
        document_id=document_id, 
        work_item_id=work_item_id
    )
    db.execute(statement)
    db.commit()
    return True
    
