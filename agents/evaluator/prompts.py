"""
LLM prompt templates for CV evaluation with Chain-of-Thought reasoning
"""

SYSTEM_PROMPT = """You are an expert HR professional evaluating CVs against specific criteria.

Your evaluation approach:

1. CHAIN-OF-THOUGHT REASONING: Before making any judgments, work through 3-7 reasoning steps:
   - Observe what information is present in the CV
   - Analyze how it relates to the criterion
   - Build your understanding step-by-step

2. ATOMIC CRITERIA BREAKDOWN: Break down the main criterion into 2-6 specific sub-criteria:
   - Each sub-criterion should measure one specific aspect
   - Score each sub-criterion independently on a 1-5 scale:
     * 1 = Poor/Minimal
     * 2 = Below average
     * 3 = Average/Acceptable
     * 4 = Good/Strong
     * 5 = Excellent/Outstanding
   - Provide specific evidence from the CV for each sub-criterion

3. FINAL EVALUATION: Based on your reasoning and sub-criteria analysis:
   - Calculate an overall score (0-100)
   - Assess your confidence (0.0-1.0)
   - Identify key strengths and weaknesses
   - Write a concise summary

Be objective, fair, and thorough. Base your evaluation solely on information in the CV.
Always cite specific evidence when making claims."""


def build_evaluation_prompt(parsed_cv: dict, criterion: dict) -> str:
    """
    Build evaluation prompt for LLM.

    Args:
        parsed_cv: ParsedCV as dict
        criterion: EvaluationCriterion as dict

    Returns:
        Formatted prompt string
    """
    # Format CV data for prompt
    contact_summary = _format_contact_info(parsed_cv.get("contact_info", {}))
    education_summary = _format_education(parsed_cv.get("education", []))
    experience_summary = _format_experience(parsed_cv.get("experience", []))
    skills_list = ", ".join(parsed_cv.get("skills", []))
    certs_summary = _format_certifications(parsed_cv.get("certifications", []))

    prompt = f"""
Evaluation Criterion:
━━━━━━━━━━━━━━━━━━
Name: {criterion['name']}
Description: {criterion['description']}
Evaluation Prompt: {criterion['evaluation_prompt']}
Weight: {criterion.get('weight', 1.0)}

━━━━━━━━━━━━━━━━━━

Candidate CV Data:
━━━━━━━━━━━━━━━━━━

{contact_summary}

EDUCATION:
{education_summary}

WORK EXPERIENCE:
{experience_summary}

SKILLS:
{skills_list}

CERTIFICATIONS:
{certs_summary}

━━━━━━━━━━━━━━━━━━

EVALUATION INSTRUCTIONS:

Step 1: CHAIN-OF-THOUGHT REASONING
Work through 3-7 reasoning steps, each containing:
- step_number: The step number in your reasoning
- observation: What you observed in the CV data
- analysis: Your analysis of that observation

Step 2: ATOMIC CRITERIA BREAKDOWN
Break down the criterion "{criterion['name']}" into 2-6 specific, measurable sub-criteria.
For each sub-criterion provide:
- name: Name of the sub-criterion
- description: What this sub-criterion measures
- score: 1-5 rating (1=poor, 5=excellent)
- evidence: Specific evidence from the CV
- reasoning: Brief explanation of the score

Step 3: FINAL EVALUATION
Based on your Chain-of-Thought reasoning and sub-criteria analysis:
- overall_score: 0-100 aggregate score
- confidence: 0.0-1.0 confidence level
- key_strengths: List 1-5 key strengths
- key_weaknesses: List 1-5 key weaknesses
- summary: 50-500 character evaluation summary

Remember:
- Think step-by-step before making judgments
- Break down criteria into atomic, measurable aspects
- Cite specific evidence from the CV
- Be objective and fair
"""

    return prompt


def _format_contact_info(contact: dict) -> str:
    """Format contact info for prompt"""
    if not contact:
        return "Contact: Not provided"

    parts = []
    if contact.get("name"):
        parts.append(f"Name: {contact['name']}")
    if contact.get("email"):
        parts.append(f"Email: {contact['email']}")
    if contact.get("phone"):
        parts.append(f"Phone: {contact['phone']}")
    if contact.get("location"):
        parts.append(f"Location: {contact['location']}")
    if contact.get("linkedin"):
        parts.append(f"LinkedIn: {contact['linkedin']}")

    return "CONTACT INFO:\n" + "\n".join(parts)


def _format_education(education: list) -> str:
    """Format education entries for prompt"""
    if not education:
        return "No education information provided."

    entries = []
    for idx, edu in enumerate(education, 1):
        parts = [f"\n{idx}. {edu.get('degree', 'Degree not specified')}"]

        if edu.get("institution"):
            parts.append(f"   Institution: {edu['institution']}")
        if edu.get("start_date") or edu.get("end_date"):
            date_range = f"{edu.get('start_date', '?')} - {edu.get('end_date', 'Present')}"
            parts.append(f"   Dates: {date_range}")
        if edu.get("gpa"):
            parts.append(f"   GPA: {edu['gpa']}")

        entries.append("\n".join(parts))

    return "\n".join(entries)


def _format_experience(experience: list) -> str:
    """Format experience entries for prompt"""
    if not experience:
        return "No work experience provided."

    entries = []
    for idx, exp in enumerate(experience, 1):
        parts = [f"\n{idx}. {exp.get('title', 'Title not specified')}"]

        if exp.get("company"):
            parts.append(f"   Company: {exp['company']}")
        if exp.get("location"):
            parts.append(f"   Location: {exp['location']}")
        if exp.get("start_date") or exp.get("end_date"):
            date_range = f"{exp.get('start_date', '?')} - {exp.get('end_date', 'Present')}"
            parts.append(f"   Dates: {date_range}")
        if exp.get("description"):
            desc = exp['description'][:200]  # Truncate long descriptions
            parts.append(f"   Description: {desc}...")

        entries.append("\n".join(parts))

    return "\n".join(entries)


def _format_certifications(certifications: list) -> str:
    """Format certifications for prompt"""
    if not certifications:
        return "No certifications provided."

    entries = []
    for idx, cert in enumerate(certifications, 1):
        cert_str = f"{idx}. {cert.get('name', 'Certification not specified')}"
        if cert.get("issuer"):
            cert_str += f" (issued by {cert['issuer']})"
        if cert.get("date"):
            cert_str += f" - {cert['date']}"
        entries.append(cert_str)

    return "\n".join(entries)
