"""
Entity extraction and structured data parsing from CV text
"""

import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import phonenumbers
from email_validator import validate_email, EmailNotValidError
import dateparser

logger = logging.getLogger(__name__)


class CVExtractor:
    """Extract structured data from CV text"""

    # Section detection patterns
    SECTION_PATTERNS = {
        'education': r'(?i)(education|academic|qualifications?|degrees?|university|college)',
        'experience': r'(?i)(experience|employment|work history|career|professional)',
        'skills': r'(?i)(skills?|competencies|expertise|technologies|proficiencies)',
        'certifications': r'(?i)(certifications?|licenses?|credentials?|certificates)',
        'projects': r'(?i)(projects?|portfolio|publications?)',
        'languages': r'(?i)(languages?|linguistic)',
    }

    # Contact info patterns
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    LINKEDIN_PATTERN = r'linkedin\.com/in/([\w-]+)'
    GITHUB_PATTERN = r'github\.com/([\w-]+)'
    URL_PATTERN = r'https?://[^\s<>"]+'

    # Date patterns
    DATE_PATTERNS = [
        r'(\d{4})\s*[-–—]\s*(\d{4}|present|current)',
        r'(\w+\s+\d{4})\s*[-–—]\s*(\w+\s+\d{4}|present|current)',
        r'(\d{1,2}/\d{4})\s*[-–—]\s*(\d{1,2}/\d{4}|present|current)',
    ]

    def __init__(self):
        self.logger = logger

    def extract_contact_info(self, text: str) -> Dict[str, Any]:
        """Extract contact information from CV text"""
        contact = {}

        # Extract name (usually first line or prominent)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            # Heuristic: name is usually in first few lines, not too long
            for line in lines[:5]:
                if 5 < len(line) < 50 and not any(char.isdigit() for char in line):
                    # Check if it looks like a name (2-4 words, capitalized)
                    words = line.split()
                    if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                        contact['name'] = line
                        break

        # Extract email
        emails = re.findall(self.EMAIL_PATTERN, text)
        if emails:
            # Validate and use first valid email
            for email in emails:
                try:
                    validate_email(email)
                    contact['email'] = email.lower()
                    break
                except EmailNotValidError:
                    continue

        # Extract phone
        phones = self._extract_phone_numbers(text)
        if phones:
            contact['phone'] = phones[0]

        # Extract LinkedIn
        linkedin = re.search(self.LINKEDIN_PATTERN, text, re.IGNORECASE)
        if linkedin:
            contact['linkedin'] = f"linkedin.com/in/{linkedin.group(1)}"

        # Extract GitHub
        github = re.search(self.GITHUB_PATTERN, text, re.IGNORECASE)
        if github:
            contact['github'] = f"github.com/{github.group(1)}"

        # Extract location (heuristic: look for city, state/country patterns)
        location = self._extract_location(text)
        if location:
            contact['location'] = location

        return contact

    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers using phonenumbers library"""
        phones = []
        try:
            # Try to parse phone numbers (assume US/international format)
            for match in phonenumbers.PhoneNumberMatcher(text, "US"):
                formatted = phonenumbers.format_number(
                    match.number,
                    phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
                phones.append(formatted)
        except Exception as e:
            self.logger.warning(f"Phone extraction error: {e}")

        return phones

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location using common patterns"""
        # Pattern: City, State/Country
        location_pattern = r'([A-Z][a-zA-Z\s]+),\s+([A-Z]{2,}|[A-Z][a-zA-Z\s]+)'
        matches = re.findall(location_pattern, text[:1000])  # Check first 1000 chars

        if matches:
            # Return first match that looks reasonable
            city, region = matches[0]
            return f"{city.strip()}, {region.strip()}"

        return None

    def extract_sections(self, text: str) -> Dict[str, str]:
        """
        Split CV text into sections (Education, Experience, etc.)

        Returns:
            Dict mapping section name to section text
        """
        sections = {}
        lines = text.split('\n')

        current_section = 'header'
        current_text = []
        section_order = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Check if line is a section header
            found_section = None
            for section_name, pattern in self.SECTION_PATTERNS.items():
                if re.search(pattern, line_stripped):
                    # Line looks like a section header
                    if len(line_stripped.split()) <= 5:  # Headers are usually short
                        found_section = section_name
                        break

            if found_section:
                # Save previous section
                if current_text:
                    sections[current_section] = '\n'.join(current_text)
                    section_order.append(current_section)

                # Start new section
                current_section = found_section
                current_text = []
            else:
                current_text.append(line)

        # Save last section
        if current_text:
            sections[current_section] = '\n'.join(current_text)

        return sections

    def extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education entries"""
        education = []

        # Common patterns for degrees
        degree_patterns = [
            r'(B\.?S\.?|Bachelor|BA|BS|B\.?A\.?)\s+(?:of\s+)?([A-Za-z\s&]+)',
            r'(M\.?S\.?|Master|MA|MS|M\.?A\.?|MBA)\s+(?:of\s+)?([A-Za-z\s&]+)',
            r'(Ph\.?D\.?|Doctorate|Doctor)\s+(?:of\s+)?([A-Za-z\s&]+)',
        ]

        # Try to find degree mentions
        for pattern in degree_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                degree_type = match.group(1)
                field = match.group(2).strip() if len(match.groups()) > 1 else ""

                # Try to find associated institution (usually nearby)
                context_start = max(0, match.start() - 200)
                context_end = min(len(text), match.end() + 200)
                context = text[context_start:context_end]

                # Look for university/college names (capitalized words)
                institution = self._find_institution(context)

                # Look for dates
                dates = self._extract_dates(context)

                entry = {
                    "degree": f"{degree_type} {field}".strip(),
                    "institution": institution or "",
                    "start_date": dates[0] if len(dates) > 0 else "",
                    "end_date": dates[1] if len(dates) > 1 else "",
                }

                education.append(entry)

        return education

    def _find_institution(self, text: str) -> Optional[str]:
        """Find institution name in text (heuristic)"""
        # Look for patterns like "University of X", "X Institute", "X College"
        institution_pattern = r'(?:University|Institute|College|School)\s+(?:of\s+)?([A-Z][A-Za-z\s&]+)'
        match = re.search(institution_pattern, text)
        if match:
            return match.group(0).strip()

        # Or reversed: "X University"
        reverse_pattern = r'([A-Z][A-Za-z\s&]+?)\s+(?:University|Institute|College)'
        match = re.search(reverse_pattern, text)
        if match:
            return match.group(0).strip()

        return None

    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        dates = []

        for pattern in self.DATE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.extend([m.strip() for m in match if m])

        return dates[:2]  # Return max 2 dates (start, end)

    def extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience entries"""
        experience = []

        # Split by likely entry boundaries (dates, company names)
        # This is a simplified heuristic
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        current_entry = {}
        for i, line in enumerate(lines):
            # Check if line contains dates (likely start of new entry)
            if re.search(self.DATE_PATTERNS[0], line, re.IGNORECASE):
                # Save previous entry
                if current_entry:
                    experience.append(current_entry)

                # Start new entry
                dates = self._extract_dates(line)
                current_entry = {
                    "title": "",
                    "company": "",
                    "start_date": dates[0] if len(dates) > 0 else "",
                    "end_date": dates[1] if len(dates) > 1 else "",
                    "description": "",
                    "location": "",
                }

                # Try to find job title and company in nearby lines
                context = ' '.join(lines[max(0, i - 2):min(len(lines), i + 3)])
                # Heuristics would go here

            elif current_entry:
                # Add to current entry description
                if 'description' in current_entry:
                    current_entry['description'] += line + ' '

        # Save last entry
        if current_entry:
            experience.append(current_entry)

        return experience

    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text"""
        skills = []

        # Common skill patterns (technologies, programming languages, tools)
        skill_keywords = [
            # Programming languages
            r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|Go|Rust|Ruby|PHP|Swift|Kotlin)\b',
            # Frameworks
            r'\b(React|Angular|Vue|Django|Flask|Spring|Node\.js|Express|FastAPI)\b',
            # Databases
            r'\b(PostgreSQL|MySQL|MongoDB|Redis|Oracle|SQL Server|Cassandra)\b',
            # Cloud/DevOps
            r'\b(AWS|Azure|GCP|Docker|Kubernetes|Jenkins|GitLab|Terraform)\b',
            # Tools
            r'\b(Git|GitHub|GitLab|Jira|Confluence|VS Code|IntelliJ)\b',
        ]

        for pattern in skill_keywords:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.strip()
                if skill and skill not in skills:
                    skills.append(skill)

        return skills

    def extract_certifications(self, text: str) -> List[Dict[str, Any]]:
        """Extract certifications"""
        certifications = []

        # Common certification patterns
        cert_patterns = [
            r'(?:Certified|Certification)\s+([A-Za-z\s\-&]+)',
            r'([A-Z]{2,})\s+(?:Certified|Certification)',
        ]

        for pattern in cert_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                cert_name = match.group(1).strip() if match.group(1) else match.group(0).strip()

                # Try to find issuer and date nearby
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end]

                dates = self._extract_dates(context)

                cert = {
                    "name": cert_name,
                    "issuer": "",  # Would need more sophisticated extraction
                    "date": dates[0] if dates else "",
                }

                certifications.append(cert)

        return certifications
