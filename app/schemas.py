from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import date, datetime
class Token(BaseModel): access_token: str; token_type: str
class UserBase(BaseModel):
    email: str
class UserCreate(UserBase):
    password: str; company_id: Optional[int] = None; role: Optional[str] = "user"
class User(UserBase):
    id: int; is_active: bool; role: str; company_id: Optional[int] = None 
    class Config: from_attributes = True
class CompanyBase(BaseModel):
    name: str
class CompanyCreate(CompanyBase):
    pass
class Company(CompanyBase):
    id: int; users: List[User] = []
    class Config: from_attributes = True

class TaskBase(BaseModel):
    name: str; description: Optional[str] = None; start_date: date; end_date: date   
    parent_id: Optional[int] = None; priority: Optional[int] = 2; responsible_user_id: Optional[int] = None
    actual_start_date: Optional[date] = None; actual_end_date: Optional[date] = None
    status: Optional[str] = "Pendiente"; progress: Optional[int] = 0
class TaskCreate(TaskBase):
    pass
class Task(TaskBase):
    id: int; project_id: int; creator_id: Optional[int] = None; subtasks: List["Task"] = []; responsible_user: Optional[User] = None
    class Config: from_attributes = True
class TaskUpdate(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None; start_date: Optional[date] = None
    end_date: Optional[date] = None; parent_id: Optional[int] = None; priority: Optional[int] = None
    responsible_user_id: Optional[int] = None; actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None; status: Optional[str] = None; progress: Optional[int] = None

class ContractorBase(BaseModel):
    razon_social: str; responsable: Optional[str] = None; telefono: Optional[str] = None; correo_electronico: Optional[str] = None
class ContractorCreate(ContractorBase):
    project_id: int
class Contractor(ContractorBase):
    id: int; project_id: int
    class Config: from_attributes = True
class ContractorUpdate(BaseModel):
    razon_social: Optional[str] = None; responsable: Optional[str] = None; telefono: Optional[str] = None; correo_electronico: Optional[str] = None

class DocumentVersionBase(BaseModel):
    filename: str; file_type: Optional[str] = None; file_size: Optional[int] = None
class DocumentVersion(DocumentVersionBase):
    id: int; document_id: int; version_number: int; created_at: datetime
    class Config: from_attributes = True
class DocumentBase(BaseModel):
    name: str
class DocumentCreate(DocumentBase):
    folder_id: int
class Document(DocumentBase):
    id: int; folder_id: int; versions: List[DocumentVersion] = []
    class Config: from_attributes = True
class FolderBase(BaseModel):
    name: str
class FolderCreate(FolderBase):
    parent_id: Optional[int] = None
class Folder(FolderBase):
    id: int; project_id: int; parent_id: Optional[int] = None
    subfolders: List["Folder"] = []; documents: List[Document] = []
    class Config: from_attributes = True
class BimElementBase(BaseModel):
    guid: str; ifc_type: Optional[str] = None; name: Optional[str] = None; properties: Optional[dict] = None
class BimElement(BimElementBase):
    id: int; document_version_id: int
    class Config: from_attributes = True

class WorkItemBase(BaseModel):
    item_code: str
    description: Optional[str] = None
    presupuesto_base: float = 0.0
class WorkItemCreate(WorkItemBase):
    pass
class WorkItemUpdate(BaseModel):
    item_code: Optional[str] = None; description: Optional[str] = None; presupuesto_base: Optional[float] = None
class WorkItemSimple(WorkItemBase):
    id: int; project_id: int
    class Config: from_attributes = True

class EstimateItemBase(BaseModel):
    contract_item_id: int
    cantidad_estimada: float = 0.0
class EstimateItemCreate(EstimateItemBase):
    pass
class EstimateItemUpdate(BaseModel):
    cantidad_estimada: Optional[float] = None
class EstimateItemSimple(EstimateItemBase):
    id: int; estimate_id: int
    class Config: from_attributes = True

class ContractItemBase(BaseModel):
    concepto: str
    clave: Optional[str] = None; unidad: Optional[str] = None; nivel_zona: Optional[str] = None
    avance_fisico: Optional[float] = 0.0; tipo_concepto: Optional[str] = "Ordinario"
    is_group: bool = False; parent_id: Optional[int] = None
    precio_unitario: float = 0.0; cantidad_contratada: float = 0.0
    cantidad_aditiva: float = 0.0; cantidad_deductiva: float = 0.0
class ContractItemCreate(ContractItemBase):
    pass
class ContractItemUpdate(BaseModel):
    concepto: Optional[str] = None; clave: Optional[str] = None; unidad: Optional[str] = None
    nivel_zona: Optional[str] = None; avance_fisico: Optional[float] = None
    tipo_concepto: Optional[str] = None; is_group: Optional[bool] = None
    parent_id: Optional[int] = None; precio_unitario: Optional[float] = None
    cantidad_contratada: Optional[float] = None; cantidad_aditiva: Optional[float] = None
    cantidad_deductiva: Optional[float] = None

class ContractItem(ContractItemBase):
    id: int
    contract_id: int
    estimate_items: List[EstimateItemSimple] = []
    subitems: List["ContractItem"] = []
    
    @computed_field
    @property
    def cantidad_total_vigente(self) -> float:
        if self.is_group: return sum(item.cantidad_total_vigente for item in self.subitems)
        return self.cantidad_contratada + self.cantidad_aditiva - self.cantidad_deductiva
    @computed_field
    @property
    def total_contratado_vigente(self) -> float:
        if self.is_group: return sum(item.total_contratado_vigente for item in self.subitems)
        return self.cantidad_total_vigente * self.precio_unitario
    @computed_field
    @property
    def cantidad_estimada_acumulada(self) -> float:
        if self.is_group: return sum(item.cantidad_estimada_acumulada for item in self.subitems)
        return sum(item.cantidad_estimada for item in self.estimate_items)
    @computed_field
    @property
    def cantidad_por_estimar(self) -> float:
        return self.cantidad_total_vigente - self.cantidad_estimada_acumulada
    @computed_field
    @property
    def avance_financiero_pct(self) -> float:
        if self.cantidad_total_vigente == 0: return 0.0
        return (self.cantidad_estimada_acumulada / self.cantidad_total_vigente) * 100
    class Config:
        from_attributes = True

class EstimateItem(EstimateItemBase):
    id: int; estimate_id: int
    contract_item: ContractItem 
    @computed_field
    @property
    def total_estimado(self) -> float:
        return self.cantidad_estimada * self.contract_item.precio_unitario
    class Config: from_attributes = True

class EstimateBase(BaseModel):
    numero_estimacion: str; fecha: Optional[date] = None; contract_id: int; monto_estimado_manual: Optional[float] = 0.0
    amortizacion_anticipo: Optional[float] = 0.0
    fondo_garantia: Optional[float] = 0.0
    otras_retenciones: Optional[float] = 0.0
    otras_deductivas: Optional[float] = 0.0
class EstimateCreate(EstimateBase):
    pass
class EstimateUpdate(BaseModel):
    numero_estimacion: Optional[str] = None; fecha: Optional[date] = None; monto_estimado_manual: Optional[float] = None; amortizacion_anticipo: Optional[float] = None; fondo_garantia: Optional[float] = None; otras_retenciones: Optional[float] = None; otras_deductivas: Optional[float] = None

class EstimateSimple(EstimateBase):
    id: int; project_id: int
    estimate_items: List[EstimateItem] = []
    @computed_field
    @property
    def total_items_calculado(self) -> float:
        return sum(item.total_estimado for item in self.estimate_items)
    @computed_field
    @property
    def total_estimado(self) -> float:
        if self.total_items_calculado > 0: return self.total_items_calculado
        return self.monto_estimado_manual
    class Config: from_attributes = True

class ContractBase(BaseModel):
    numero_contrato: str; contractor_id: int; trabajos: Optional[str] = None; aplica_iva: bool = True; monto_contratado_manual: Optional[float] = 0.0; anticipo: Optional[float] = 0.0
    dms_folder_id: Optional[int] = None; status: Optional[str] = "Borrador"; external_url: Optional[str] = None
    work_item_id: Optional[int] = None
class ContractCreate(ContractBase):
    pass
class ContractUpdate(BaseModel):
    numero_contrato: Optional[str] = None; contractor_id: Optional[int] = None; trabajos: Optional[str] = None; aplica_iva: Optional[bool] = None; monto_contratado_manual: Optional[float] = None
    anticipo: Optional[float] = None
    dms_folder_id: Optional[int] = None
    status: Optional[str] = None; external_url: Optional[str] = None; work_item_id: Optional[int] = None

class ContractSimple(ContractBase):
    id: int
    project_id: int
    contract_items: List[ContractItem] = []

    @computed_field
    @property
    def total_contratado_vigente(self) -> float:
        total_items = sum(item.total_contratado_vigente for item in self.contract_items if not item.is_group)
        if total_items > 1.0:
            return total_items
        return self.monto_contratado_manual

    @computed_field
    @property
    def total_extraordinario(self) -> float:
        return sum(item.total_contratado_vigente for item in self.contract_items if item.tipo_concepto == 'Extraordinario' and not item.is_group)

    @computed_field
    @property
    def iva(self) -> float:
        if not self.aplica_iva:
            return 0.0
        return self.total_contratado_vigente * 0.16

    @computed_field
    @property
    def total_con_iva(self) -> float:
        return self.total_contratado_vigente + self.iva

    class Config: from_attributes = True

class WorkItem(WorkItemBase):
    id: int
    project_id: int
    contracts: List[ContractSimple] = []

    @computed_field
    @property
    def costo_real(self) -> float:
        if not self.contracts:
            return 0.0
        return sum(c.total_contratado_vigente * (1.16 if c.aplica_iva else 1.0) for c in self.contracts)

    @computed_field
    @property
    def diferencia_costo(self) -> float:
        return self.presupuesto_base - self.costo_real

    class Config: from_attributes = True

class Contract(ContractBase):
    id: int
    project_id: int
    contractor: Contractor
    contract_items: List[ContractItem] = []
    dms_folder: Optional[Folder] = None
    estimates: List[EstimateSimple] = []
    work_item: Optional[WorkItemSimple] = None
    
    @computed_field
    @property
    def total_ordinario(self) -> float:
        return sum(item.total_contratado_vigente for item in self.contract_items if item.tipo_concepto == 'Ordinario' and not item.is_group)
    @computed_field
    @property
    def total_extraordinario(self) -> float:
        return sum(item.total_contratado_vigente for item in self.contract_items if item.tipo_concepto == 'Extraordinario' and not item.is_group)
    @computed_field
    @property
    def total_contratado_vigente(self) -> float:
        total_items = self.total_ordinario + self.total_extraordinario
        if total_items > 1.0: 
            return total_items
        return self.monto_contratado_manual
    @computed_field
    @property
    def total_estimado_acumulado(self) -> float:
        return sum(est.total_estimado for est in self.estimates)
    
    @computed_field
    @property
    def total_aditivas(self) -> float:
        return sum(item.cantidad_aditiva * item.precio_unitario for item in self.contract_items if not item.is_group)

    @computed_field
    @property
    def total_deductivas(self) -> float:
        return sum(item.cantidad_deductiva * item.precio_unitario for item in self.contract_items if not item.is_group)

    @computed_field
    @property
    def iva(self) -> float:
        if not self.aplica_iva:
            return 0.0
        return self.total_contratado_vigente * 0.16

    @computed_field
    @property
    def total_con_iva(self) -> float:
        return self.total_contratado_vigente + self.iva

    @computed_field
    @property
    def progress(self) -> float:
        total_contratado_val = self.total_contratado_vigente
        if total_contratado_val == 0: return 0.0
        avance = (self.total_estimado_acumulado / total_contratado_val) * 100
        return round(avance, 2)
    class Config:
        from_attributes = True

class Estimate(EstimateBase):
    id: int; project_id: int
    contract: Contract 
    estimate_items: List[EstimateItem] = []
    
    @computed_field
    @property
    def total_items_calculado(self) -> float:
        return sum(item.total_estimado for item in self.estimate_items)
    @computed_field
    @property
    def total_estimado(self) -> float:
        if self.total_items_calculado > 0: return self.total_items_calculado
        return self.monto_estimado_manual

    @computed_field
    @property
    def subtotal(self) -> float:
        return self.total_estimado

    @computed_field
    @property
    def total_deducciones(self) -> float:
        return self.amortizacion_anticipo + self.fondo_garantia + self.otras_retenciones + self.otras_deductivas

    @computed_field
    @property
    def total_a_pagar(self) -> float:
        return self.subtotal - self.total_deducciones
    class Config: from_attributes = True

class ProjectBase(BaseModel):
    name: str; description: Optional[str] = None; company_id: int

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None

class Project(ProjectBase):
    id: int
    company: Company
    tasks: List[Task] = []
    folders: List[Folder] = []
    work_items: List["WorkItem"] = []
    contracts: List[Contract] = []
    estimates: List[Estimate] = []
    contractors: List[Contractor] = [] # Aseguramos que la lista de contratistas esté aquí
    class Config:
        from_attributes = True

class BCFComponentBase(BaseModel):
    ifc_guid: str
    originating_system: Optional[str] = None
    authoring_tool_id: Optional[str] = None

class BCFComponentCreate(BCFComponentBase):
    pass

class BCFComponent(BCFComponentBase):
    guid: str
    viewpoint_guid: str
    class Config: from_attributes = True

class BCFViewpointBase(BaseModel):
    index: Optional[int] = 0
    camera_view_point_x: float
    camera_view_point_y: float
    camera_view_point_z: float
    camera_direction_x: float
    camera_direction_y: float
    camera_direction_z: float
    camera_up_vector_x: float
    camera_up_vector_y: float
    camera_up_vector_z: float
    field_of_view: Optional[float] = None
    view_to_world_scale: Optional[float] = None
    snapshot_img: Optional[str] = None # Base64

class BCFViewpointCreate(BCFViewpointBase):
    components: List[BCFComponentCreate] = []

class BCFViewpoint(BCFViewpointBase):
    guid: str
    topic_guid: str
    components: List[BCFComponent] = []
    class Config: from_attributes = True

class BCFCommentBase(BaseModel):
    comment: str

class BCFCommentCreate(BCFCommentBase):
    pass

class BCFComment(BCFCommentBase):
    guid: str
    topic_guid: str
    date: datetime
    author: str
    class Config: from_attributes = True

class BCFTopicBase(BaseModel):
    title: str
    topic_type: Optional[str] = "Issue"
    topic_status: Optional[str] = "Open"
    description: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None

class BCFTopicCreate(BCFTopicBase):
    viewpoints: List[BCFViewpointCreate] = []
    comments: List[BCFCommentCreate] = []

class BCFTopic(BCFTopicBase):
    guid: str
    project_id: int
    creation_date: datetime
    creation_author: str
    modified_date: datetime
    modified_author: str
    viewpoints: List[BCFViewpoint] = []
    comments: List[BCFComment] = []
    class Config: from_attributes = True

class BCFTopicUpdate(BaseModel):
    title: Optional[str] = None
    topic_type: Optional[str] = None
    topic_status: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None