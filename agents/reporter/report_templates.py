"""
Report generation templates and prompts
"""

from typing import Dict, List, Any

SYSTEM_PROMPT = """You are an expert HR professional generating comprehensive CV evaluation reports.

Your task is to:
1. Review all evaluation results for a candidate
2. Synthesize the findings into a clear, actionable report
3. Provide an overall recommendation (SUITABLE/REJECTED)
4. Explain the rationale for your recommendation
5. Highlight key strengths and areas of concern

Be professional, objective, and constructive in your feedback.
"""


def build_report_prompt(
    parsed_cv: dict,
    evaluations: List[Dict[str, Any]],
    criteria: List[Dict[str, Any]]
) -> str:
    """
    Build prompt for LLM to generate evaluation report.

    Args:
        parsed_cv: ParsedCV as dict
        evaluations: List of EvaluationResult dicts
        criteria: List of EvaluationCriterion dicts

    Returns:
        Formatted prompt string
    """
    # Format candidate info
    contact = parsed_cv.get("contact_info", {})
    candidate_name = contact.get("name", "Candidate")

    # Format evaluations
    eval_summaries = []
    total_score = 0
    total_weight = 0

    for eval_result in evaluations:
        # Find matching criterion
        criterion = next(
            (c for c in criteria if c["criterion_id"] == eval_result["criterion_id"]),
            None
        )

        if not criterion:
            continue

        weight = criterion.get("weight", 1.0)
        score = eval_result["score"]

        total_score += score * weight
        total_weight += weight

        eval_summary = f"""
**{criterion['name']}** (Weight: {weight})
- Score: {score}/100
- Confidence: {eval_result['confidence']:.2f}
- Evidence: {eval_result['evidence']}
- Reasoning: {eval_result['reasoning']}
"""
        eval_summaries.append(eval_summary)

    weighted_average = total_score / total_weight if total_weight > 0 else 0

    prompt = f"""
Generate a comprehensive CV evaluation report for {candidate_name}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANDIDATE INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Name: {contact.get('name', 'Not provided')}
Email: {contact.get('email', 'Not provided')}
Location: {contact.get('location', 'Not provided')}

Education: {len(parsed_cv.get('education', []))} entries
Experience: {len(parsed_cv.get('experience', []))} positions
Skills: {len(parsed_cv.get('skills', []))} skills identified
Certifications: {len(parsed_cv.get('certifications', []))} certifications

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EVALUATION RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Weighted Average Score: {weighted_average:.1f}/100

Individual Criterion Evaluations:
{''.join(eval_summaries)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Based on the evaluation results above, generate a comprehensive report in the following JSON format:

{{
    "recommendation": "<SUITABLE or REJECTED>",
    "overall_score": <weighted average score as float>,
    "summary": "<2-3 sentence executive summary of the candidate's fit>",
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "concerns": ["<concern 1>", "<concern 2>"],
    "rationale": "<detailed explanation of your recommendation, referencing specific evaluation results>"
}}

Guidelines:
- Recommendation should be SUITABLE if weighted_average >= 60, otherwise REJECTED
- Summary should be concise but informative
- Strengths should highlight what makes the candidate a good fit
- Concerns should mention any gaps or weaknesses (can be empty array if none)
- Rationale should be 3-5 sentences explaining the decision

Return ONLY the JSON, no other text.
"""

    return prompt


def format_markdown_report(
    candidate_name: str,
    report_data: Dict[str, Any],
    evaluations: List[Dict[str, Any]],
    criteria: List[Dict[str, Any]]
) -> str:
    """
    Format the report as a Markdown document.

    Args:
        candidate_name: Name of the candidate
        report_data: Generated report data from LLM
        evaluations: List of EvaluationResult dicts
        criteria: List of EvaluationCriterion dicts

    Returns:
        Markdown formatted report
    """
    recommendation = report_data["recommendation"]
    overall_score = report_data["overall_score"]
    summary = report_data["summary"]
    strengths = report_data.get("strengths", [])
    concerns = report_data.get("concerns", [])
    rationale = report_data["rationale"]

    # Determine status emoji
    status_emoji = "✅" if recommendation == "SUITABLE" else "❌"

    markdown = f"""# CV Evaluation Report: {candidate_name}

## {status_emoji} Recommendation: {recommendation}

**Overall Score:** {overall_score:.1f}/100

### Executive Summary

{summary}

---

## Detailed Analysis

### Strengths

"""

    for i, strength in enumerate(strengths, 1):
        markdown += f"{i}. {strength}\n"

    if concerns:
        markdown += "\n### Areas of Concern\n\n"
        for i, concern in enumerate(concerns, 1):
            markdown += f"{i}. {concern}\n"

    markdown += f"""
---

## Rationale

{rationale}

---

## Evaluation Breakdown

"""

    for eval_result in evaluations:
        criterion = next(
            (c for c in criteria if c["criterion_id"] == eval_result["criterion_id"]),
            None
        )

        if not criterion:
            continue

        markdown += f"""
### {criterion['name']}

- **Score:** {eval_result['score']}/100
- **Weight:** {criterion.get('weight', 1.0)}
- **Confidence:** {eval_result['confidence']:.2%}

**Evidence:**
{eval_result['evidence']}

**Reasoning:**
{eval_result['reasoning']}

---
"""

    markdown += """
## Scoring Guide

- **0-20:** Poor/Minimal fit
- **21-40:** Below average
- **41-60:** Average/Acceptable
- **61-80:** Good/Strong fit
- **81-100:** Excellent/Outstanding fit

---

*This report was generated automatically by CAVIA (CV Assessment via Intelligent Agents).*
"""

    return markdown
