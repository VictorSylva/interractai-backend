from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..base import Base
import uuid
# Import Business to avoid mapper errors (string lookup needs registry population or import)
# Ideally use string "Business" but ensure registry sees it.
# To be safe, we lazy import or ensure models are loaded.
from ..base import Base
# Note: We rely on string "Business" but if clean imports fail, we might need explicit import.
class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"))
    
    name = Column(String, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    trigger_type = Column(String) # message_created, manual, webhook
    trigger_config = Column(JSON, default={}) # e.g. {"keyword": "help"}
    definition = Column(JSON, default={}) # UI Graph (Nodes/Edges) for restoration
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="workflows")
    nodes = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    edges = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"))
    
    type = Column(String) # start, action, condition, ai_inference, delay, end
    label = Column(String)
    config = Column(JSON, default={}) # Params for the node logic
    
    # UI position (x, y) for the frontend graph
    platform_meta = Column(JSON, default={}) 

    workflow = relationship("Workflow", back_populates="nodes")
    # Edges where this node is the SOURCE
    outgoing_edges = relationship("WorkflowEdge", back_populates="source_node", foreign_keys="WorkflowEdge.source_id")
    # Edges where this node is the TARGET
    incoming_edges = relationship("WorkflowEdge", back_populates="target_node", foreign_keys="WorkflowEdge.target_id")

class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"))
    
    source_id = Column(String, ForeignKey("workflow_nodes.id"))
    target_id = Column(String, ForeignKey("workflow_nodes.id"))
    
    condition_value = Column(String, nullable=True) # For conditional branching (e.g. "yes", "no", "high_sentiment")

    workflow = relationship("Workflow", back_populates="edges")
    source_node = relationship("WorkflowNode", back_populates="outgoing_edges", foreign_keys=[source_id])
    target_node = relationship("WorkflowNode", back_populates="incoming_edges", foreign_keys=[target_id])

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"))
    business_id = Column(String, ForeignKey("businesses.id"))
    
    status = Column(String, default="pending") # pending, running, completed, failed
    trigger_event = Column(JSON) # The data that triggered this
    context_data = Column(JSON, default={}) # Global memory for this execution
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # For Orchestration (Suspended State)
    resume_payload = Column(JSON, nullable=True) # What we are waiting for / state to resume with

    workflow = relationship("Workflow", back_populates="executions")
    steps = relationship("ExecutionStep", back_populates="execution", cascade="all, delete-orphan")

class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String, ForeignKey("workflow_executions.id"))
    node_id = Column(String, ForeignKey("workflow_nodes.id"))
    
    status = Column(String) # pending, running, completed, failed, skipped
    input_data = Column(JSON)
    output_data = Column(JSON)
    error = Column(Text)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    execution = relationship("WorkflowExecution", back_populates="steps")
