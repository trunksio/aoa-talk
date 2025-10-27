"""
Shared data models for CAVIA
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


class JobStatus(str, Enum):
    """CV job status enumeration"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


class AgentRegistration(BaseModel):
    """Agent registration model"""

    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: Dict[str, Any]
    queue_name: str
    status: AgentStatus = AgentStatus.STARTING
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentHeartbeat(BaseModel):
    """Agent heartbeat model"""

    agent_id: str
    status: AgentStatus
    metadata: Optional[Dict[str, Any]] = None


class CVJob(BaseModel):
    """CV processing job model"""

    job_id: str
    filename: str
    minio_path: str
    status: JobStatus = JobStatus.PENDING
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParsedCV(BaseModel):
    """Parsed CV data structure"""

    contact_info: Dict[str, str] = Field(default_factory=dict)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    raw_text: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationCriterion(BaseModel):
    """Evaluation criterion definition"""

    criterion_id: str
    name: str
    description: str
    evaluation_prompt: str
    weight: float = 1.0
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Single criterion evaluation result"""

    criterion_id: str
    agent_id: str
    score: float = Field(..., ge=0, le=100, description="Score from 0 to 100")
    confidence: float = Field(..., ge=0, le=1, description="Confidence from 0 to 1")
    evidence: str
    reasoning: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CVEvaluationReport(BaseModel):
    """Complete CV evaluation report"""

    job_id: str
    filename: str
    parsed_cv: ParsedCV
    evaluations: List[EvaluationResult]
    overall_score: float
    decision: str  # "accept" or "reject"
    decision_reasoning: str
    rejection_reasons: Optional[List[str]] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Intent Management Models
# ============================================================================


class IntentConstraint(BaseModel):
    """A constraint or business rule for the intent"""

    name: str = Field(..., description="Constraint name")
    description: str = Field(..., description="Human-readable description")
    value: Any = Field(..., description="Constraint value")
    required: bool = Field(default=True, description="Is this constraint mandatory")
    validation_rule: Optional[str] = Field(None, description="Optional validation expression")


class IntentSuccessCriteria(BaseModel):
    """Success criteria for validating intent completion"""

    criterion: str = Field(..., description="Name of the success criterion")
    description: str = Field(..., description="What this criterion measures")
    validation_rule: str = Field(..., description="Rule to evaluate success (e.g., 'score >= 70')")
    threshold: Optional[float] = Field(None, description="Numerical threshold if applicable")
    required: bool = Field(default=True, description="Is meeting this criterion required for success")


class StructuredIntent(BaseModel):
    """Rich intent model for agent chains with goals, constraints, and success criteria"""

    intent_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique intent ID")
    workflow_type: str = Field(..., description="Type of workflow (e.g., 'cv_evaluation', 'expense_evaluation')")
    goal: str = Field(..., description="High-level goal of this intent")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context and parameters")
    constraints: List[IntentConstraint] = Field(default_factory=list, description="Business rules and constraints")
    success_criteria: List[IntentSuccessCriteria] = Field(default_factory=list, description="Criteria for successful completion")
    current_stage: str = Field(default="initiated", description="Current stage in workflow")
    parent_intent_id: Optional[str] = Field(None, description="Parent intent if this is a sub-intent")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IntentValidation(BaseModel):
    """Result of intent validation at an agent"""

    validation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = Field(..., description="Agent that performed validation")
    agent_type: str = Field(..., description="Type of agent")
    is_aligned: bool = Field(..., description="Does agent's work align with intent?")
    alignment_score: float = Field(..., ge=0.0, le=1.0, description="Alignment score 0-1")
    drift_score: float = Field(..., ge=0.0, le=1.0, description="Drift from original intent 0-1 (0=no drift)")
    reasoning: str = Field(..., description="Explanation of validation result")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions if drift detected")
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    """Task model for agent queue (legacy - uses string intent)"""

    task_id: str
    task_type: str
    payload: Dict[str, Any]
    intent: str = Field(default="", description="Original intent/goal for this task chain (legacy)")
    steps_completed: list[str] = Field(default_factory=list, description="List of agent types that have processed this task")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentTaskV2(BaseModel):
    """Enhanced task model with structured intent"""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = Field(..., description="Type of task for the agent")
    payload: Dict[str, Any] = Field(..., description="Task-specific data")
    intent: StructuredIntent = Field(..., description="Structured intent for this task chain")
    intent_validations: List[IntentValidation] = Field(default_factory=list, description="Validation results from each agent")
    steps_completed: List[str] = Field(default_factory=list, description="Agent types that have processed this")
    current_agent: Optional[str] = Field(None, description="Current agent processing this task")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentTaskResult(BaseModel):
    """Result from agent task execution"""

    task_id: str
    agent_id: str
    status: str  # "success" or "error"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Structured Evaluation Models (for Instructor-based LLM evaluation)
# ============================================================================


class ReasoningStep(BaseModel):
    """A single step in Chain-of-Thought reasoning"""

    step_number: int = Field(..., description="Step number in the reasoning chain")
    observation: str = Field(..., description="What was observed in the CV data")
    analysis: str = Field(..., description="Analysis of this observation")


class SubCriterion(BaseModel):
    """Atomic sub-criterion evaluation"""

    name: str = Field(..., description="Name of the sub-criterion")
    description: str = Field(..., description="What this sub-criterion measures")
    score: int = Field(..., ge=1, le=5, description="Score from 1 (poor) to 5 (excellent)")
    evidence: str = Field(..., description="Specific evidence from CV supporting this score")
    reasoning: str = Field(..., description="Brief explanation of the score")


class StructuredEvaluation(BaseModel):
    """
    Complete structured evaluation with Chain-of-Thought reasoning.

    This model is used with Instructor library for automatic validation
    and structured output from LLM evaluations.
    """

    # Chain-of-Thought Reasoning
    reasoning_steps: List[ReasoningStep] = Field(
        ...,
        min_length=3,
        max_length=7,
        description="Chain-of-Thought reasoning steps (3-7 steps)"
    )

    # Atomic Criteria Breakdown
    sub_criteria: List[SubCriterion] = Field(
        ...,
        min_length=2,
        max_length=6,
        description="Atomic breakdown of the criterion (2-6 sub-criteria)"
    )

    # Overall Evaluation
    overall_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall score 0-100 (calculated from sub-criteria)"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this evaluation (0.0-1.0)"
    )

    key_strengths: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1-5 key strengths identified"
    )

    key_weaknesses: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1-5 key weaknesses identified"
    )

    summary: str = Field(
        ...,
        min_length=50,
        max_length=500,
        description="Summary of the evaluation (50-500 chars)"
    )
