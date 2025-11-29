from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Float
from sqlalchemy.orm import relationship
from .database import Base
import uuid
from datetime import datetime
class BCFTopic(Base):
    __tablename__ = "bcf_topics"
    guid = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    topic_type = Column(String, default="Issue") # Issue, Clash, Request, etc.
    topic_status = Column(String, default="Open") # Open, Closed, Resolved
    title = Column(String)
    description = Column(Text, nullable=True)
    priority = Column(String, nullable=True)
    index = Column(Integer, nullable=True) # For sorting
    
    creation_date = Column(DateTime, default=datetime.utcnow)
    creation_author = Column(String, nullable=True) # Email or User ID
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    modified_author = Column(String, nullable=True)
    
    assigned_to = Column(String, nullable=True) # Email or User ID
    
    # Relationships
    viewpoints = relationship("BCFViewpoint", back_populates="topic", cascade="all, delete-orphan")
    comments = relationship("BCFComment", back_populates="topic", cascade="all, delete-orphan")
    
    # Link to Extraordinary Concept (Budget)
    # extraordinary_concept_id = Column(Integer, ForeignKey("contract_items.id"), nullable=True)
class BCFViewpoint(Base):
    __tablename__ = "bcf_viewpoints"
    guid = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    topic_guid = Column(String, ForeignKey("bcf_topics.guid"))
    
    index = Column(Integer, default=0)
    
    # Camera Position
    camera_view_point_x = Column(Float)
    camera_view_point_y = Column(Float)
    camera_view_point_z = Column(Float)
    
    # Camera Direction (Target - Position) or Direction Vector
    camera_direction_x = Column(Float)
    camera_direction_y = Column(Float)
    camera_direction_z = Column(Float)
    
    # Up Vector
    camera_up_vector_x = Column(Float)
    camera_up_vector_y = Column(Float)
    camera_up_vector_z = Column(Float)
    
    field_of_view = Column(Float, nullable=True) # For Perspective
    view_to_world_scale = Column(Float, nullable=True) # For Orthogonal
    
    snapshot_img = Column(Text, nullable=True) # Base64 encoded image
    
    topic = relationship("BCFTopic", back_populates="viewpoints")
    components = relationship("BCFComponent", back_populates="viewpoint", cascade="all, delete-orphan")
class BCFComment(Base):
    __tablename__ = "bcf_comments"
    guid = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    topic_guid = Column(String, ForeignKey("bcf_topics.guid"))
    
    date = Column(DateTime, default=datetime.utcnow)
    author = Column(String)
    comment = Column(Text)
    
    topic = relationship("BCFTopic", back_populates="comments")
class BCFComponent(Base):
    __tablename__ = "bcf_components"
    
    id = Column(Integer, primary_key=True, index=True)
    viewpoint_guid = Column(String, ForeignKey("bcf_viewpoints.guid"))
    
    ifc_guid = Column(String) # The GlobalId in the IFC file
    authoring_tool_id = Column(String, nullable=True)
    originating_system = Column(String, nullable=True)
    
    viewpoint = relationship("BCFViewpoint", back_populates="components")
