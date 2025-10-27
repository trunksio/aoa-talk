"""
Workflow Templates for Intent-Driven Agent-Oriented Architecture

Defines standard workflows with intent templates for different business processes.
"""

from typing import Dict, List, Any
from pydantic import BaseModel, Field


class WorkflowTemplate(BaseModel):
    """Template for a workflow with default intent configuration"""

    workflow_id: str
    name: str
    description: str
    document_types: List[str]
    first_agent_query: str
    intent_template: Dict[str, Any]
    example_intents: List[str] = Field(default_factory=list)
    icon: str = "file"
    category: str = "general"


# ============================================================================
# CV EVALUATION WORKFLOWS
# ============================================================================

CV_EVALUATION_TEMPLATE = WorkflowTemplate(
    workflow_id="cv_evaluation",
    name="CV Evaluation",
    description="Evaluate candidate CV against job requirements and criteria",
    document_types=["pdf", "docx"],
    first_agent_query="parse standard CV and extract structured candidate data",
    intent_template={
        "workflow_type": "cv_evaluation",
        "goal": "Evaluate candidate suitability for {{position}} position",
        "context": {
            "position": "Software Engineer",
            "department": "Engineering",
            "level": "Senior"
        },
        "constraints": [
            {
                "name": "minimum_experience",
                "description": "Minimum years of relevant experience required",
                "value": 3,
                "required": True
            },
            {
                "name": "required_skills",
                "description": "Must-have technical skills",
                "value": ["Python", "JavaScript"],
                "required": True
            },
            {
                "name": "education_level",
                "description": "Minimum education level",
                "value": "Bachelor's degree",
                "required": False
            }
        ],
        "success_criteria": [
            {
                "criterion": "overall_score",
                "description": "Candidate overall evaluation score",
                "validation_rule": "score >= 70",
                "threshold": 70.0,
                "required": True
            },
            {
                "criterion": "experience_match",
                "description": "Experience aligns with position requirements",
                "validation_rule": "experience_years >= 3",
                "threshold": 3.0,
                "required": True
            }
        ]
    },
    example_intents=[
        "Evaluate senior software engineer candidate with 5+ years experience",
        "Assess candidate for data scientist role requiring Python and ML expertise",
        "Review CV for project manager position with Agile experience"
    ],
    icon="user-check",
    category="hr"
)

CV_EVALUATION_SCANNED_TEMPLATE = WorkflowTemplate(
    workflow_id="cv_evaluation_scanned",
    name="Scanned CV Evaluation (OCR)",
    description="Extract and evaluate scanned or image-based CV with charts/graphs",
    document_types=["pdf", "jpg", "jpeg", "png", "tiff"],
    first_agent_query="extract structured data from scanned image-based CV using OCR",
    intent_template={
        "workflow_type": "cv_evaluation",
        "goal": "Extract and evaluate scanned CV for {{position}} position",
        "context": {
            "position": "Software Engineer",
            "ocr_required": True,
            "has_charts": False
        },
        "constraints": [
            {
                "name": "ocr_required",
                "description": "Document requires OCR processing",
                "value": True,
                "required": True
            },
            {
                "name": "minimum_experience",
                "description": "Minimum years of relevant experience required",
                "value": 3,
                "required": True
            }
        ],
        "success_criteria": [
            {
                "criterion": "ocr_confidence",
                "description": "OCR extraction confidence level",
                "validation_rule": "confidence >= 0.8",
                "threshold": 0.8,
                "required": True
            },
            {
                "criterion": "overall_score",
                "description": "Candidate overall evaluation score",
                "validation_rule": "score >= 70",
                "threshold": 70.0,
                "required": True
            }
        ]
    },
    example_intents=[
        "Extract and evaluate scanned CV with visual charts",
        "Process image-based resume for senior position",
        "OCR and assess candidate from photographed document"
    ],
    icon="scan",
    category="hr"
)

# ============================================================================
# EXPENSE EVALUATION WORKFLOWS
# ============================================================================

EXPENSE_RECEIPT_TEMPLATE = WorkflowTemplate(
    workflow_id="expense_evaluation",
    name="Expense/Receipt Evaluation",
    description="Validate expense receipts against company reimbursement policies",
    document_types=["pdf", "jpg", "jpeg", "png"],
    first_agent_query="extract receipt/invoice data for expense policy evaluation",
    intent_template={
        "workflow_type": "expense_evaluation",
        "goal": "Evaluate {{expense_type}} expense for reimbursement approval",
        "context": {
            "expense_type": "lunch",
            "employee_id": "",
            "project_code": "",
            "date": ""
        },
        "constraints": [
            {
                "name": "expense_category",
                "description": "Type of expense (lunch, transportation, accommodation)",
                "value": "lunch",
                "required": True
            },
            {
                "name": "max_amount",
                "description": "Maximum allowable amount for this expense type",
                "value": 25.00,
                "required": True
            },
            {
                "name": "no_alcohol",
                "description": "Alcohol purchases not allowed",
                "value": True,
                "required": True
            },
            {
                "name": "business_hours",
                "description": "Must be during business hours (weekdays)",
                "value": True,
                "required": False
            }
        ],
        "success_criteria": [
            {
                "criterion": "within_policy",
                "description": "Expense complies with company policy",
                "validation_rule": "approved == true",
                "required": True
            },
            {
                "criterion": "amount_valid",
                "description": "Amount within allowed limit",
                "validation_rule": "amount <= max_amount",
                "required": True
            }
        ]
    },
    example_intents=[
        "Evaluate lunch receipt for $18.50 reimbursement",
        "Process dinner expense claim within $50 limit",
        "Validate taxi receipt for transportation reimbursement"
    ],
    icon="receipt",
    category="finance"
)

INVOICE_PROCESSING_TEMPLATE = WorkflowTemplate(
    workflow_id="invoice_processing",
    name="Invoice Processing",
    description="Extract and validate vendor invoices for payment approval",
    document_types=["pdf", "jpg", "jpeg", "png"],
    first_agent_query="extract invoice data and validate against purchase order",
    intent_template={
        "workflow_type": "invoice_processing",
        "goal": "Process vendor invoice for payment approval",
        "context": {
            "vendor_name": "",
            "purchase_order_number": "",
            "department": "",
            "approval_required": True
        },
        "constraints": [
            {
                "name": "has_purchase_order",
                "description": "Invoice must match a valid purchase order",
                "value": True,
                "required": True
            },
            {
                "name": "payment_terms_valid",
                "description": "Payment terms within acceptable range (net 30-90)",
                "value": True,
                "required": True
            },
            {
                "name": "max_amount_threshold",
                "description": "Invoices over this amount require additional approval",
                "value": 10000.00,
                "required": False
            }
        ],
        "success_criteria": [
            {
                "criterion": "invoice_valid",
                "description": "Invoice data is complete and valid",
                "validation_rule": "has_required_fields == true",
                "required": True
            },
            {
                "criterion": "po_match",
                "description": "Invoice matches purchase order",
                "validation_rule": "po_number_valid == true",
                "required": True
            }
        ]
    },
    example_intents=[
        "Process vendor invoice for $5,000 office supplies",
        "Validate software license invoice against PO-12345",
        "Review consulting services invoice for payment approval"
    ],
    icon="file-text",
    category="finance"
)

# ============================================================================
# WORKFLOW REGISTRY
# ============================================================================

WORKFLOW_TEMPLATES: Dict[str, WorkflowTemplate] = {
    "cv_evaluation": CV_EVALUATION_TEMPLATE,
    "cv_evaluation_scanned": CV_EVALUATION_SCANNED_TEMPLATE,
    "expense_evaluation": EXPENSE_RECEIPT_TEMPLATE,
    "invoice_processing": INVOICE_PROCESSING_TEMPLATE,
}


def get_workflow_template(workflow_id: str) -> WorkflowTemplate:
    """Get a workflow template by ID"""
    return WORKFLOW_TEMPLATES.get(workflow_id)


def list_workflow_templates() -> List[WorkflowTemplate]:
    """List all available workflow templates"""
    return list(WORKFLOW_TEMPLATES.values())


def get_workflows_by_category(category: str) -> List[WorkflowTemplate]:
    """Get workflows filtered by category"""
    return [wf for wf in WORKFLOW_TEMPLATES.values() if wf.category == category]
