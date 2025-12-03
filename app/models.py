from sqlalchemy import Table, Column, Integer, String, Date, ForeignKey, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .database import Base

# --- TABLAS DE UNIÓN (DMS) ---
document_contract_link = Table('document_contract_link', Base.metadata,
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True),
    Column('contract_id', Integer, ForeignKey('contracts.id'), primary_key=True)
)

# --- TABLAS DE USUARIOS/EMPRESAS ---
class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    users = relationship("User", back_populates="company")
    projects = relationship("Project", back_populates="company")
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)    
    company = relationship("Company", back_populates="users")
    responsible_tasks = relationship("Task", foreign_keys="[Task.responsible_user_id]", back_populates="responsible_user")
    created_tasks = relationship("Task", foreign_keys="[Task.creator_id]", back_populates="creator")

class Project(Base):
    __tablename__ = "projects"    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    company = relationship("Company", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    work_items = relationship("WorkItem", back_populates="project", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="project", cascade="all, delete-orphan")
    estimates = relationship("Estimate", back_populates="project", cascade="all, delete-orphan")
    folders = relationship("Folder", back_populates="project", cascade="all, delete-orphan")
    contractors = relationship("Contractor", back_populates="project", cascade="all, delete-orphan")
    bcf_topics = relationship("BCFTopic", back_populates="project", cascade="all, delete-orphan")

class Contractor(Base):
    __tablename__ = "contractors"
    id = Column(Integer, primary_key=True, index=True)
    razon_social = Column(String, index=True, nullable=False)
    responsable = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    correo_electronico = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="contractors")
    contracts = relationship("Contract", back_populates="contractor") 

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    status = Column(String, default="Pendiente")
    progress = Column(Integer, default=0)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    priority = Column(Integer, default=2)
    responsible_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)    
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    responsible_user = relationship("User", foreign_keys=[responsible_user_id], back_populates="responsible_tasks")
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_tasks")
    subtasks = relationship("Task", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("Task", back_populates="subtasks", remote_side=[id])
    project = relationship("Project", back_populates="tasks")


class WorkItem(Base):

    __tablename__ = "work_items"
    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String, index=True) 
    description = Column(String)
    presupuesto_base = Column(Float, default=0.0)     
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="work_items")    
    contracts = relationship("Contract", back_populates="work_item")

class Contract(Base):

    __tablename__ = "contracts"    
    id = Column(Integer, primary_key=True, index=True)
    numero_contrato = Column(String, index=True)
    trabajos = Column(String) 
    monto_contratado_manual = Column(Float, default=0.0)
    anticipo = Column(Float, default=0.0)
    aplica_iva = Column(Boolean, default=True)
    dms_folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    status = Column(String, default="Borrador")
    external_url = Column(String, nullable=True)  
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)
    work_item_id = Column(Integer, ForeignKey("work_items.id"), nullable=True)
    work_item = relationship("WorkItem", back_populates="contracts")
    project = relationship("Project", back_populates="contracts")
    contractor = relationship("Contractor", back_populates="contracts")
    dms_folder = relationship("Folder")
    contract_items = relationship("ContractItem", back_populates="contract", cascade="all, delete-orphan")
    estimates = relationship("Estimate", back_populates="contract", cascade="all, delete-orphan")
    documents = relationship("Document", secondary="document_contract_link", back_populates="contracts")

class ContractItem(Base):

    __tablename__ = "contract_items"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    is_group = Column(Boolean, default=False, nullable=False)
    parent_id = Column(Integer, ForeignKey("contract_items.id"), nullable=True)
    nivel_zona = Column(String, nullable=True)
    tipo_concepto = Column(String, default="Ordinario", nullable=False)
    avance_fisico = Column(Float, default=0.0)
    clave = Column(String, index=True, nullable=True)
    concepto = Column(String, nullable=False)
    unidad = Column(String, nullable=True)
    precio_unitario = Column(Float, default=0.0)
    cantidad_contratada = Column(Float, default=0.0)
    cantidad_aditiva = Column(Float, default=0.0)
    cantidad_deductiva = Column(Float, default=0.0)    
    contract = relationship("Contract", back_populates="contract_items")
    estimate_items = relationship("EstimateItem", back_populates="contract_item", cascade="all, delete-orphan")    
    parent = relationship("ContractItem", back_populates="subitems", remote_side=[id])
    subitems = relationship("ContractItem", back_populates="parent", cascade="all, delete-orphan")

class Estimate(Base):
    __tablename__ = "estimates"    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    numero_estimacion = Column(String, index=True)
    fecha = Column(Date, nullable=True)
    monto_estimado_manual = Column(Float, default=0.0) 
    amortizacion_anticipo = Column(Float, default=0.0)
    fondo_garantia = Column(Float, default=0.0)
    otras_retenciones = Column(Float, default=0.0)
    otras_deductivas = Column(Float, default=0.0)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)    
    project = relationship("Project", back_populates="estimates")
    contract = relationship("Contract", back_populates="estimates")
    estimate_items = relationship("EstimateItem", back_populates="estimate", cascade="all, delete-orphan")

class EstimateItem(Base):

    __tablename__ = "estimate_items"    
    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False)
    contract_item_id = Column(Integer, ForeignKey("contract_items.id"), nullable=False)    
    cantidad_estimada = Column(Float, default=0.0)    
    estimate = relationship("Estimate", back_populates="estimate_items")
    contract_item = relationship("ContractItem", back_populates="estimate_items")

class Folder(Base):
    __tablename__ = "folders"
    id = Column(Integer, primary_key=True, index=True); name = Column(String, index=True); project_id = Column(Integer, ForeignKey("projects.id"), nullable=False); parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True) 
    project = relationship("Project", back_populates="folders"); parent = relationship("Folder", back_populates="subfolders", remote_side=[id]); subfolders = relationship("Folder", back_populates="parent", cascade="all, delete-orphan"); documents = relationship("Document", back_populates="folder", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True); name = Column(String, index=True); folder_id = Column(Integer, ForeignKey("folders.id"), nullable=False)
    folder = relationship("Folder", back_populates="documents"); versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    contracts = relationship("Contract", secondary="document_contract_link", back_populates="documents")

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True, index=True); document_id = Column(Integer, ForeignKey("documents.id"), nullable=False); version_number = Column(Integer, nullable=False); filename = Column(String); file_path = Column(String, unique=True, nullable=False); file_type = Column(String); file_size = Column(Integer); created_at = Column(DateTime(timezone=True), server_default=func.now())
    document = relationship("Document", back_populates="versions"); bim_elements = relationship("BimElement", back_populates="document_version", cascade="all, delete-orphan")

class BimElement(Base):
    __tablename__ = "bim_elements"
    id = Column(Integer, primary_key=True, index=True); guid = Column(String, index=True, nullable=False); ifc_type = Column(String, index=True); name = Column(String); properties = Column(JSON, nullable=True); document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False)
    document_version = relationship("DocumentVersion", back_populates="bim_elements")

# --- BCF (BIM Collaboration Format) Tables ---

class BCFTopic(Base):
    __tablename__ = "bcf_topics"
    guid = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    topic_type = Column(String, default="Issue")
    topic_status = Column(String, default="Open")
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String, nullable=True)
    index = Column(Integer, nullable=True)
    
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    creation_author = Column(String, nullable=True)
    modified_date = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    modified_author = Column(String, nullable=True)
    
    assigned_to = Column(String, nullable=True)
    
    project = relationship("Project", back_populates="bcf_topics")
    viewpoints = relationship("BCFViewpoint", back_populates="topic", cascade="all, delete-orphan")
    comments = relationship("BCFComment", back_populates="topic", cascade="all, delete-orphan")

class BCFViewpoint(Base):
    __tablename__ = "bcf_viewpoints"
    guid = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    topic_guid = Column(String, ForeignKey("bcf_topics.guid"), nullable=False)
    
    index = Column(Integer, default=0)
    camera_view_point_x = Column(Float); camera_view_point_y = Column(Float); camera_view_point_z = Column(Float)
    camera_direction_x = Column(Float); camera_direction_y = Column(Float); camera_direction_z = Column(Float)
    camera_up_vector_x = Column(Float); camera_up_vector_y = Column(Float); camera_up_vector_z = Column(Float)
    
    field_of_view = Column(Float, nullable=True)
    view_to_world_scale = Column(Float, nullable=True)
    
    snapshot_img = Column(Text, nullable=True) # Base64 encoded image
    
    topic = relationship("BCFTopic", back_populates="viewpoints")
    components = relationship("BCFComponent", back_populates="viewpoint", cascade="all, delete-orphan")

class BCFComment(Base):
    __tablename__ = "bcf_comments"
    guid = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    topic_guid = Column(String, ForeignKey("bcf_topics.guid"), nullable=False)
    
    date = Column(DateTime(timezone=True), server_default=func.now())
    author = Column(String, nullable=False)
    comment = Column(Text)
    
    topic = relationship("BCFTopic", back_populates="comments")

class BCFComponent(Base):
    __tablename__ = "bcf_components"
    id = Column(Integer, primary_key=True, index=True)
    viewpoint_guid = Column(String, ForeignKey("bcf_viewpoints.guid"), nullable=False)
    
    ifc_guid = Column(String)
    authoring_tool_id = Column(String, nullable=True)
    originating_system = Column(String, nullable=True)
    
    viewpoint = relationship("BCFViewpoint", back_populates="components")