from sqlalchemy import Table, Column, Integer, String, Date, ForeignKey, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

document_contract_link = Table('document_contract_link', Base.metadata,
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True),
    Column('contract_id', Integer, ForeignKey('contracts.id'), primary_key=True)
)
document_workitem_link = Table('document_workitem_link', Base.metadata,
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True),
    Column('work_item_id', Integer, ForeignKey('work_items.id'), primary_key=True)
)

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    users = relationship("User", back_populates="company")
    projects = relationship("Project", back_populates="company")
    contractors = relationship("Contractor", back_populates="company")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company = relationship("Company", back_populates="users")
    tasks = relationship("Task", back_populates="responsible_user")

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

class Contractor(Base):
    __tablename__ = "contractors"
    id = Column(Integer, primary_key=True, index=True)
    razon_social = Column(String, index=True, nullable=False)
    responsable = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    correo_electronico = Column(String, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    company = relationship("Company", back_populates="contractors")
    contracts = relationship("Contract", back_populates="contractor") 

class WorkItem(Base):
    __tablename__ = "work_items"
    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String, index=True) 
    description = Column(String)
    presupuesto_base = Column(Float, default=0.0)    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="work_items")    
    contracts = relationship("Contract", back_populates="work_item")
    documents = relationship("Document", secondary="document_workitem_link", back_populates="work_items")

class Contract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True, index=True)
    numero_contrato = Column(String, index=True)
    trabajos = Column(String)
    contratado = Column(Float, default=0.0)
    aditiva = Column(Float, default=0.0)
    deductiva = Column(Float, default=0.0)
    anticipo = Column(Float, default=0.0)
    aplica_iva = Column(Boolean, default=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)
    work_item_id = Column(Integer, ForeignKey("work_items.id"), nullable=False)
    project = relationship("Project", back_populates="contracts")
    contractor = relationship("Contractor", back_populates="contracts")
    work_item = relationship("WorkItem", back_populates="contracts")
    estimates = relationship("Estimate", back_populates="contract", cascade="all, delete-orphan")
    documents = relationship("Document", secondary="document_contract_link", back_populates="contracts")

class Estimate(Base):
    __tablename__ = "estimates"
    id = Column(Integer, primary_key=True, index=True)
    estimado = Column(Float, default=0.0)
    deductiva_estimacion = Column(Float, default=0.0)
    amortizado = Column(Float, default=0.0)
    fondo_garantia = Column(Float, default=0.0)
    retenciones = Column(Float, default=0.0)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    project = relationship("Project", back_populates="estimates")
    contract = relationship("Contract", back_populates="estimates")
    
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
    responsible_user = relationship("User", back_populates="tasks")
    subtasks = relationship("Task", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("Task", back_populates="subtasks", remote_side=[id])
    project = relationship("Project", back_populates="tasks")

class Folder(Base):
    __tablename__ = "folders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True) 
    project = relationship("Project", back_populates="folders")
    parent = relationship("Folder", back_populates="subfolders", remote_side=[id])
    subfolders = relationship("Folder", back_populates="parent", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="folder", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=False)
    folder = relationship("Folder", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    contracts = relationship("Contract", secondary="document_contract_link", back_populates="documents")
    work_items = relationship("WorkItem", secondary="document_workitem_link", back_populates="documents")

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    filename = Column(String)
    file_path = Column(String, unique=True, nullable=False)
    file_type = Column(String)
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    document = relationship("Document", back_populates="versions")