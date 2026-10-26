import json
import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.models.company import Company
from app.models.job import Job
from app.services.opportunity_normalizer import OpportunityNormalizer
from app.services.company_research_service import CompanyResearchService


def backfill_company_classifications():
    """
    Backfills and enriches company classifications and true employer names
    for all existing company records in the database.
    """
    db = SessionLocal()
    try:
        # 1. Ensure SQLite column exists
        from sqlalchemy import text
        with engine.begin() as conn:
            res = conn.execute(text("PRAGMA table_info(companies)"))
            cols = [r[1] for r in res.fetchall()]
            if "classification" not in cols:
                conn.execute(text("ALTER TABLE companies ADD COLUMN classification VARCHAR(50) DEFAULT 'unknown' NOT NULL"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_companies_classification ON companies(classification)"))

        companies = db.query(Company).all()
        print(f"Total companies to inspect and enrich: {len(companies)}")

        updated_count = 0
        cleaned_employer_count = 0

        for company in companies:
            # Check related jobs for better signal extraction if name was an aggregator or city
            jobs = db.query(Job).filter(Job.company_id == company.id).all()
            first_job = jobs[0] if jobs else None
            job_title = first_job.title if first_job else ""
            job_url = first_job.primary_url if first_job else (company.website_url or "")

            cleaned_name = OpportunityNormalizer.clean_employer_name(
                company_name=company.name,
                title=job_title,
                url=job_url
            )

            if cleaned_name and cleaned_name != company.name and cleaned_name not in ("Direct Hiring Organization", "Naukri", "Internshala"):
                print(f"Cleaned employer name: '{company.name}' -> '{cleaned_name}'")
                company.name = cleaned_name
                cleaned_employer_count += 1
                for j in jobs:
                    j.company_name = cleaned_name

            # Research company classification
            research = CompanyResearchService.research_company_classification(
                company_name=company.name,
                domain=company.domain,
                website_url=company.website_url,
                existing_description=company.description,
                existing_signals=company.signals_data if isinstance(company.signals_data, list) else []
            )

            new_classification = research.get("classification") or "unknown"
            new_size_range = research.get("size_range")

            company.classification = new_classification
            if new_size_range and not company.size_range:
                company.size_range = new_size_range

            # Update signals data with evidence record if missing
            signals = company.signals_data if isinstance(company.signals_data, list) else []
            has_class_signal = any(s.get("classification") for s in signals if isinstance(s, dict))
            if not has_class_signal:
                signals.append({
                    "signal_type": "company_classification_evidence",
                    "headline": f"Classified as {new_classification.replace('_', ' ').capitalize()}",
                    "classification": new_classification,
                    "size_range": new_size_range,
                    "excerpt": research.get("evidence_excerpt"),
                    "evidence_url": research.get("source_url") or company.website_url,
                    "confidence": research.get("confidence", 0.5)
                })
                company.signals_data = list(signals)

            updated_count += 1

        db.commit()
        print(f"Backfill successfully completed. Updated: {updated_count}, Cleaned employers: {cleaned_employer_count}")

    except Exception as e:
        db.rollback()
        print(f"Error during backfill: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill_company_classifications()
