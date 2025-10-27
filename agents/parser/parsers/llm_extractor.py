"""
LLM-based CV extractor using Ollama for reliable structured data extraction
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class LLMCVExtractor:
    """
    Extract structured data from CV text using LLM with context engineering.

    This approach is much more reliable than regex patterns because:
    - LLM understands context and semantics
    - Works with any CV format/layout
    - Can infer information that's implicit
    - Handles variations in terminology
    """

    def __init__(self, ollama_client):
        """
        Initialize with Ollama client

        Args:
            ollama_client: Instance of OllamaClient from cavia_common
        """
        self.ollama = ollama_client
        self.logger = logger

    def extract_all_sections(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract all CV sections in one LLM call for efficiency.

        Returns structured data including:
        - contact_info
        - education
        - experience
        - skills
        - certifications
        """
        self.logger.info("Extracting CV data using LLM")

        prompt = self._build_extraction_prompt(raw_text)

        try:
            # Call Ollama with structured prompt
            response = self.ollama.chat(
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for factual extraction
            )

            if not response:
                raise ValueError("LLM returned empty response")

            # Parse JSON response
            extracted_data = self._parse_llm_response(response)

            # Validate extracted data
            self._validate_extracted_data(extracted_data)

            self.logger.info(
                "CV extraction completed",
                education_count=len(extracted_data.get("education", [])),
                experience_count=len(extracted_data.get("experience", [])),
                skills_count=len(extracted_data.get("skills", [])),
            )

            return extracted_data

        except Exception as e:
            self.logger.error(f"LLM extraction failed: {e}")
            # Fallback to empty structure
            return self._empty_structure()

    def _get_system_prompt(self) -> str:
        """System prompt that defines the extraction task"""
        return """You are a professional CV/resume parser. Your task is to extract structured information from CVs/resumes with high accuracy.

Extract the following information:
1. Contact Information: name, email, phone, location, linkedin, github
2. Education: degree, institution, field of study, start date, end date, GPA (if mentioned)
3. Work Experience: job title, company, start date, end date, location, description/achievements
4. Skills: technical skills, tools, languages, frameworks (categorized if possible)
5. Certifications: certification name, issuer, date obtained

Guidelines:
- Extract ONLY information that is explicitly present in the CV
- Use "Unknown" or empty string if information is not found
- Dates should be in YYYY or MM/YYYY format when possible
- For "present" or "current" positions, use "Present" as end_date
- Be precise and factual - do NOT infer or make up information
- Return valid JSON only, no additional text

Output format: JSON object with keys: contact_info, education, experience, skills, certifications"""

    def _build_extraction_prompt(self, raw_text: str) -> str:
        """Build the extraction prompt with the CV text"""
        # Truncate if too long (keep first 8000 chars to fit context window)
        text_sample = raw_text[:8000] if len(raw_text) > 8000 else raw_text

        return f"""Extract structured information from the following CV/resume:

<CV_TEXT>
{text_sample}
</CV_TEXT>

Return a JSON object with this exact structure:
{{
  "contact_info": {{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1-XXX-XXX-XXXX",
    "location": "City, State/Country",
    "linkedin": "linkedin.com/in/username",
    "github": "github.com/username"
  }},
  "education": [
    {{
      "degree": "Bachelor of Science in Computer Science",
      "institution": "University Name",
      "field": "Computer Science",
      "start_date": "2018",
      "end_date": "2022",
      "gpa": "3.8/4.0"
    }}
  ],
  "experience": [
    {{
      "title": "Software Engineer",
      "company": "Company Name",
      "location": "City, State",
      "start_date": "01/2022",
      "end_date": "Present",
      "description": "Detailed description of responsibilities and achievements"
    }}
  ],
  "skills": [
    "Python", "JavaScript", "React", "PostgreSQL", "Docker", "AWS"
  ],
  "certifications": [
    {{
      "name": "AWS Certified Solutions Architect",
      "issuer": "Amazon Web Services",
      "date": "2023"
    }}
  ]
}}

Extract only factual information present in the CV. Return ONLY the JSON, no additional text."""

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM.

        Handles cases where LLM wraps JSON in markdown code blocks.
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM JSON response: {e}")
            self.logger.error(f"Response was: {response[:500]}")
            raise ValueError(f"Invalid JSON in LLM response: {e}")

    def _validate_extracted_data(self, data: Dict[str, Any]):
        """Validate that extracted data has expected structure"""
        required_keys = ["contact_info", "education", "experience", "skills", "certifications"]

        for key in required_keys:
            if key not in data:
                self.logger.warning(f"Missing key in extracted data: {key}")
                # Add empty structure
                if key == "contact_info":
                    data[key] = {}
                elif key == "skills":
                    data[key] = []
                else:
                    data[key] = []

    def _empty_structure(self) -> Dict[str, Any]:
        """Return empty data structure as fallback"""
        return {
            "contact_info": {},
            "education": [],
            "experience": [],
            "skills": [],
            "certifications": [],
        }

    def extract_contact_info(self, text: str) -> Dict[str, Any]:
        """
        Extract just contact info (for backward compatibility).
        Uses LLM extraction on full text.
        """
        full_data = self.extract_all_sections(text)
        return full_data.get("contact_info", {})

    def extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract just education (for backward compatibility)"""
        full_data = self.extract_all_sections(text)
        return full_data.get("education", [])

    def extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract just experience (for backward compatibility)"""
        full_data = self.extract_all_sections(text)
        return full_data.get("experience", [])

    def extract_skills(self, text: str) -> List[str]:
        """Extract just skills (for backward compatibility)"""
        full_data = self.extract_all_sections(text)
        return full_data.get("skills", [])

    def extract_certifications(self, text: str) -> List[Dict[str, Any]]:
        """Extract just certifications (for backward compatibility)"""
        full_data = self.extract_all_sections(text)
        return full_data.get("certifications", [])
