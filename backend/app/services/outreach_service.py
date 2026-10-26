import json
import logging
import re
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.outreach import OutreachDraft, OutreachPurpose, RecipientType, GenerationStatus
from app.models.user import User
from app.models.opportunity import Opportunity
from app.models.resume import Resume
from app.agents.llm_factory import LLMFactory, MockLLMClient
from app.services.outreach_context_builder import OutreachContextBuilder
from app.core.config import settings

logger = logging.getLogger(__name__)


class OutreachService:
    """
    Service for generating, editing, and persisting personalized, evidence-grounded outreach drafts.
    Leverages LLMFactory for provider-agnostic generation with strict grounding constraints.
    """

    @staticmethod
    def generate_draft_content(context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates an evidence-grounded outreach email draft using the configured LLM.
        Enforces negative constraints, truthfulness boundaries, and structured JSON output.
        """
        candidate = context.get("candidate", {})
        job = context.get("job", {})
        params = context.get("outreach_parameters", {})

        candidate_name = candidate.get("name", "Candidate")
        headline = candidate.get("headline") or ""
        verified_skills = candidate.get("verified_skills", [])
        highlight_skills = candidate.get("highlight_skills", [])
        relevant_projects = candidate.get("relevant_projects", [])
        relevant_experience = candidate.get("relevant_experience", [])
        education = candidate.get("education", [])

        job_title = job.get("title", "Position")
        company_name = job.get("company_name", "Company")
        job_location = job.get("location", "")
        work_arrangement = job.get("work_arrangement", "flexible")
        is_uncertain_or_closed = job.get("is_uncertain_or_closed", False)
        requirements = job.get("requirements", [])
        evidence_claims = job.get("evidence_claims", [])

        purpose = params.get("purpose", "full_time_application")
        recipient_type = params.get("recipient_type", "hiring_manager")
        recipient_name = params.get("recipient_name")
        recipient_role = params.get("recipient_role")

        # 1. Format candidate evidence string for the prompt
        skills_str = ", ".join(highlight_skills) if highlight_skills else ", ".join(verified_skills[:5])
        
        projects_summary = []
        for p in relevant_projects[:2]:
            p_desc = f"Project: '{p['title']}' using {', '.join(p.get('technologies', []))}"
            if p.get("description"):
                p_desc += f" - {p['description'][:150]}"
            projects_summary.append(p_desc)
        projects_str = "\n".join(projects_summary) if projects_summary else "No explicit portfolio projects cited."

        exp_summary = []
        for e in relevant_experience[:2]:
            e_desc = f"Role: {e.get('role')} at {e.get('company')} ({e.get('start_date')} - {e.get('end_date')})"
            if e.get("description"):
                e_desc += f": {e['description'][:150]}"
            exp_summary.append(e_desc)
        exp_str = "\n".join(exp_summary) if exp_summary else "No past work experience cited."

        edu_summary = []
        for ed in education[:1]:
            edu_summary.append(f"{ed.get('degree')} from {ed.get('institution')} ({ed.get('graduation_year', '')})")
        edu_str = "; ".join(edu_summary) if edu_summary else "Not specified."

        # 2. Build system instructions with strict grounding rules
        system_prompt = f"""You are the Outreach AI Agent for OutReachIQ.
Your role is to craft a concise, compelling, professional, and truthful outreach message from a candidate to a company contact.

TARGET CONTEXT:
Candidate Name: {candidate_name}
Candidate Headline: {headline}
Education: {edu_str}
Candidate Verified Skills: {skills_str}
Candidate Selected Projects:
{projects_str}
Candidate Relevant Experience:
{exp_str}

OPPORTUNITY EVIDENCE:
Role: {job_title}
Company: {company_name}
Location: {job_location} ({work_arrangement})
Requirements: {', '.join(requirements[:8]) if requirements else 'General engineering competencies'}
Opportunity Status Note: {'CAUTION: This listing may be unverified or previously closed. Frame inquiry as exploratory interest in potential opportunities at the team.' if is_uncertain_or_closed else 'Active opportunity opening.'}
Company Evidence Signals: {'; '.join(evidence_claims[:3]) if evidence_claims else 'None'}

OUTREACH PARAMETERS:
Purpose: {purpose.replace('_', ' ').title()}
Recipient Type: {recipient_type.replace('_', ' ').title()}
Recipient Name: {recipient_name if recipient_name else '[UNKNOWN - DO NOT INVENT A NAME. Use a professional greeting like "Dear ' + company_name + ' Team" or "Hi there"]'}
Recipient Role: {recipient_role if recipient_role else '[UNKNOWN - DO NOT INVENT A ROLE]'}

CRITICAL TRUTHFULNESS & GROUNDING RULES:
1. NEVER invent past work experience, metrics (e.g. 'increased sales by 40%'), company facts, awards, or certifications not in the candidate's context.
2. NEVER invent a recipient name, email, or title if not provided.
3. NEVER state that an application has been submitted unless confirmed.
4. Only cite skills and projects explicitly listed above.
5. Tone: Concise, professional, human, and direct. Avoid generic cliché openings like "I am writing to express my enthusiastic interest..." or overused AI words like "delve", "testament", "tapestry".
6. Keep email body between 120 and 220 words.
7. Output MUST be valid JSON with keys "subject", "body", "key_points_highlighted", and "missing_information_notes".
"""

        # 3. Invoke LLM via LLMFactory
        llm = LLMFactory.get_llm(temperature=0.2)

        # Handle MockLLMClient or offline mode
        if isinstance(llm, MockLLMClient):
            return OutreachService._generate_mock_draft(context)

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Please generate the personalized outreach email for {candidate_name} contacting {company_name} regarding {job_title}.")
            ]
            response = llm.invoke(messages)
            raw_content = response.content if hasattr(response, "content") else str(response)

            # Parse JSON
            parsed = OutreachService._extract_json(raw_content)
            if parsed and parsed.get("subject") and parsed.get("body"):
                return {
                    "subject": parsed["subject"].strip(),
                    "body": parsed["body"].strip(),
                    "key_points_highlighted": parsed.get("key_points_highlighted", []),
                    "missing_information_notes": parsed.get("missing_information_notes", []),
                    "model_provider": settings.LLM_PROVIDER,
                    "model_name": getattr(llm, "model_name", getattr(llm, "model", "default")),
                    "status": GenerationStatus.AI_GENERATED
                }
            else:
                logger.warning("LLM output could not be parsed as valid JSON. Falling back to grounded structure.")
                return OutreachService._fallback_structure(context, raw_content)

        except Exception as e:
            logger.error(f"Error calling LLM for outreach generation: {str(e)}", exc_info=True)
            raise RuntimeError(f"Outreach generation service unavailable: {str(e)}")

    @staticmethod
    def _extract_json(raw_text: str) -> Optional[Dict[str, Any]]:
        """Safely extracts JSON from LLM response even if enclosed in markdown code fences."""
        cleaned = raw_text.strip()
        # Remove markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return None

    @staticmethod
    def _fallback_structure(context: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """Provides a clean subject and body if the LLM output was unstructured plain text."""
        job = context.get("job", {})
        title = job.get("title", "Software Engineer")
        company = job.get("company_name", "Team")
        
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        subject = f"Inquiry regarding {title} role - {context.get('candidate', {}).get('name', '')}"
        body = raw_text.strip()

        # If first line looks like Subject:
        if lines and lines[0].lower().startswith("subject:"):
            subject = lines[0].split(":", 1)[1].strip()
            body = "\n\n".join(lines[1:]).strip()

        return {
            "subject": subject,
            "body": body,
            "key_points_highlighted": [f"Targeted inquiry for {title} at {company}"],
            "missing_information_notes": ["Generated from raw LLM output."],
            "model_provider": settings.LLM_PROVIDER,
            "model_name": "llm-text",
            "status": GenerationStatus.AI_GENERATED
        }

    @staticmethod
    def _generate_mock_draft(context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a high-quality, evidence-grounded deterministic draft for local development and unit tests.
        Uses exact persisted candidate and opportunity fields without external API calls.
        """
        candidate = context.get("candidate", {})
        job = context.get("job", {})
        params = context.get("outreach_parameters", {})

        candidate_name = candidate.get("name", "Candidate")
        skills = candidate.get("highlight_skills", []) or candidate.get("verified_skills", [])
        skills_phrase = ", ".join(skills[:3]) if skills else "modern software engineering"

        projects = candidate.get("relevant_projects", [])
        project_mention = ""
        if projects:
            p0 = projects[0]
            project_mention = f" In my project '{p0['title']}', I built solutions utilizing {', '.join(p0.get('technologies', []))}."

        job_title = job.get("title", "Software Engineering Opportunity")
        company_name = job.get("company_name", "your team")
        is_uncertain = job.get("is_uncertain_or_closed", False)

        purpose = params.get("purpose", "full_time_application")
        recipient_name = params.get("recipient_name")

        greeting = f"Hi {recipient_name}," if recipient_name else f"Hello {company_name} Team,"

        # Purpose-specific subject & narrative
        if purpose == "internship_application":
            subject = f"Internship Inquiry: {job_title} - {candidate_name}"
            opening = f"I am writing to express my strong interest in internship opportunities for the {job_title} role at {company_name}."
        elif purpose == "referral_request":
            subject = f"Question regarding {company_name} and {job_title} - {candidate_name}"
            opening = f"I hope you are doing well. I noticed your work at {company_name} and wanted to reach out regarding the {job_title} role."
        elif purpose == "recruiter_introduction":
            subject = f"{job_title} Opportunity - {candidate_name} Introduction"
            opening = f"I am reaching out to introduce myself regarding technical roles at {company_name}, specifically your {job_title} opening."
        elif purpose == "follow_up":
            subject = f"Following up on {job_title} application - {candidate_name}"
            opening = f"I hope you are having a productive week. I am following up on my application for the {job_title} position at {company_name}."
        else:
            subject = f"Application Interest: {job_title} - {candidate_name}"
            opening = f"I am reaching out regarding the {job_title} position at {company_name}."

        if is_uncertain:
            status_clause = "I noticed this role may be exploratory or previously listed, but I wanted to proactively share my background in case related openings are available."
        else:
            status_clause = f"Given my background with {skills_phrase},{project_mention} I would welcome the chance to contribute to {company_name}."

        body = (
            f"{greeting}\n\n"
            f"{opening}\n\n"
            f"{status_clause}\n\n"
            f"I have attached my relevant background details and would appreciate the opportunity to connect briefly if my experience aligns with your team's goals.\n\n"
            f"Thank you for your time and consideration.\n\n"
            f"Best regards,\n"
            f"{candidate_name}\n"
            f"{candidate.get('email', '')}"
        )

        return {
            "subject": subject,
            "body": body,
            "key_points_highlighted": [
                f"Referenced verified skills: {skills_phrase}",
                f"Referenced project: {projects[0]['title'] if projects else 'Portfolio competencies'}"
            ],
            "missing_information_notes": [
                "Recipient name was omitted" if not recipient_name else f"Addressed to {recipient_name}",
                "Exploratory inquiry note included due to listing status" if is_uncertain else "Confirmed active opening context"
            ],
            "model_provider": "mock",
            "model_name": "mock-llm-v1",
            "status": GenerationStatus.AI_GENERATED
        }

    @staticmethod
    def create_manual_starter_draft(context: Dict[str, Any]) -> Dict[str, Any]:
        """Creates an initial blank/structured template for manual drafting without LLM call."""
        job = context.get("job", {})
        candidate = context.get("candidate", {})
        params = context.get("outreach_parameters", {})

        recipient_name = params.get("recipient_name")
        greeting = f"Hi {recipient_name}," if recipient_name else f"Hello {job.get('company_name', 'Hiring')} Team,"
        subject = f"Inquiry regarding {job.get('title', 'Role')} - {candidate.get('name', 'Candidate')}"

        body = (
            f"{greeting}\n\n"
            f"I am writing to inquire about the {job.get('title', 'position')} at {job.get('company_name', 'your company')}.\n\n"
            f"[Add your personalized note here highlighting your relevant skills: {', '.join(candidate.get('highlight_skills', [])[:3])}]\n\n"
            f"Thank you for your time and consideration.\n\n"
            f"Best regards,\n"
            f"{candidate.get('name', 'Candidate')}"
        )

        return {
            "subject": subject,
            "body": body,
            "key_points_highlighted": ["Manual initial template created."],
            "missing_information_notes": ["Manual user draft."],
            "model_provider": None,
            "model_name": None,
            "status": GenerationStatus.DRAFT
        }
