# app/schemas.py
from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import date, datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str
    company_id: Optional[int] = None 
    role: Optional[str] = "user"

class User(UserBase):
    id: int
    is_active: bool
    company_id: Optional[int] = None
    role: str
    class Config:
        from_attributes = True

class CompanyBase(BaseModel):
    name: str

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    users: List[User] = []
    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    parent_id: Optional[int] = None
    priority: Optional[int] = 2
    responsible_user_id: Optional[int] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: Optional[str] = "Pendiente"
    progress: Optional[int] = 0

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    parent_id: Optional[int] = None
    priority: Optional[int] = None
    responsible_user_id: Optional[int] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: Optional[str] = None
    progress: Optional[int] = None

class Task(TaskBase):
    id: int
    project_id: int
    subtasks: List["Task"] = []
    responsible_user: Optional[User] = None 
    class Config:
        from_attributes = True

class ContractorBase(BaseModel):
    razon_social: str
    responsable: Optional[str] = None
    telefono: Optional[str] = None
    correo_electronico: Optional[str] = None

class ContractorCreateRequest(ContractorBase):
    pass

class ContractorCreate(ContractorBase):
    company_id: int

class Contractor(ContractorBase):
    id: int
    company_id: int
    class Config:
        from_attributes = True

class ContractorUpdate(BaseModel):
    razon_social: Optional[str] = None
    responsable: Optional[str] = None
    telefono: Optional[str] = None
    correo_electronico: Optional[str] = None

class WorkItemBase(BaseModel):
    item_code: str
    description: Optional[str] = None
    presupuesto_base: float = 0.0

class WorkItemCreate(WorkItemBase):
    pass 

class WorkItemUpdate(BaseModel):
    item_code: Optional[str] = None
    description: Optional[str] = None
    presupuesto_base: Optional[float] = None

class WorkItemSimple(WorkItemBase):
    id: int
    project_id: int
    class Config:
        from_attributes = True

class ContractBase(BaseModel):
    numero_contrato: Optional[str] = None
    trabajos: Optional[str] = None
    contratado: float = 0.0
    aditiva: float = 0.0
    deductiva: float = 0.0
    anticipo: float = 0.0
    aplica_iva: bool = True
    contractor_id: int
    work_item_id: int

class ContractCreate(ContractBase):
    pass 

class ContractUpdate(BaseModel):
    numero_contrato: Optional[str] = None
    trabajos: Optional[str] = None
    contratado: Optional[float] = None
    aditiva: Optional[float] = None
    deductiva: Optional[float] = None
    anticipo: Optional[float] = None
    aplica_iva: Optional[bool] = None
    contractor_id: Optional[int] = None
    work_item_id: Optional[int] = None

class Contract(ContractBase):
    id: int
    project_id: int
    contractor: Contractor
    work_item: WorkItemSimple
    documents: List["Document"] = []

    @computed_field
    @property
    def total(self) -> float:
        return self.contratado + self.aditiva - self.deductiva
    
    @computed_field
    @property
    def iva(self) -> float:
        if not self.aplica_iva: return 0.0
        return (self.contratado + self.aditiva - self.deductiva) * 0.16
    
    @computed_field
    @property
    def total_con_iva(self) -> float:
        total = self.contratado + self.aditiva - self.deductiva
        iva = (total * 0.16) if self.aplica_iva else 0.0
        return total + iva

    class Config:
        from_attributes = True

class WorkItem(WorkItemBase):
    id: int
    project_id: int
    contracts: List[Contract] = []
    documents: List["Document"] = []
    
    @computed_field
    @property
    def costo_real(self) -> float:
        if not self.contracts: return 0.0
        return sum(c.total_con_iva for c in self.contracts)
    
    @computed_field
    @property
    def diferencia_costo(self) -> float:
        return self.presupuesto_base - self.costo_real

    class Config:
        from_attributes = True

# --- Schemas de Estimaciones ---

class EstimateBase(BaseModel):
    estimado: float = 0.0
    deductiva_estimacion: float = 0.0
    amortizado: float = 0.0
    fondo_garantia: float = 0.0
    retenciones: float = 0.0
    contract_id: int

class EstimateCreate(EstimateBase):
    pass 

class EstimateUpdate(BaseModel):
    estimado: Optional[float] = None
    deductiva_estimacion: Optional[float] = None
    amortizado: Optional[float] = None
    fondo_garantia: Optional[float] = None
    retenciones: Optional[float] = None
    contract_id: Optional[int] = None

class Estimate(EstimateBase):
    id: int
    project_id: int
    contract: Contract

    @computed_field
    @property
    def total(self) -> float:
        return self.estimado - self.deductiva_estimacion - self.fondo_garantia - self.retenciones
    
    @computed_field
    @property
    def iva(self) -> float:
        if not self.contract.aplica_iva: return 0.0
        total_estimacion = self.estimado - self.deductiva_estimacion - self.fondo_garantia - self.retenciones
        return total_estimacion * 0.16

    @computed_field
    @property
    def total_con_iva(self) -> float:
        total_estimacion = self.estimado - self.deductiva_estimacion - self.fondo_garantia - self.retenciones
        iva = (total_estimacion * 0.16) if self.contract.aplica_iva else 0.0
        return total_estimacion + iva

    class Config:
        from_attributes = True

class DocumentVersionBase(BaseModel):
    filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None

class DocumentVersion(DocumentVersionBase):
    id: int
    document_id: int
    version_number: int
    created_at: datetime
    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    name: str

class DocumentCreate(DocumentBase):
    folder_id: int

class Document(DocumentBase):
    id: int
    folder_id: int
    versions: List[DocumentVersion] = []
    class Config:
        from_attributes = True

class FolderBase(BaseModel):
    name: str
    
class FolderCreate(FolderBase):
    parent_id: Optional[int] = None

class Folder(FolderBase):
    id: int
    project_id: int
    parent_id: Optional[int] = None
    subfolders: List["Folder"] = []
    documents: List[Document] = []
    class Config:
        from_attributes = True

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    company_id: int 

class ProjectCreate(ProjectBase):
    pass
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Project(ProjectBase):
    id: int
    company: Company # <-- Añadir esta línea
    tasks: List[Task] = []
    folders: List[Folder] = []
    work_items: List[WorkItem] = []
    contracts: List[Contract] = []
    estimates: List[Estimate] = []
    class Config:
        from_attributes = True

Task.model_rebuild()
Contract.model_rebuild()
WorkItem.model_rebuild()
Estimate.model_rebuild()
Folder.model_rebuild()
Document.model_rebuild()
Project.model_rebuild()