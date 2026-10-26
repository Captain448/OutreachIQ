import time
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.discovery import AgentRun, RunStatus
from app.models.company import Company
from app.models.job import Job, JobRequirement
from app.models.opportunity import Opportunity, OpportunityType, OpportunityStatus, Source, Evidence, ClaimType
from app.schemas.opportunity import DiscoveryRunRequest
from app.services.profile_intelligence import ProfileIntelligenceService
from app.services.providers.provider_registry import provider_registry
from app.services.providers.base_provider import NormalizedJob, NormalizedCompany
from app.services.opportunity_normalizer import OpportunityNormalizer
from app.services.opportunity_deduplicator import OpportunityDeduplicator
from app.services.company_research_service import CompanyResearchService
from app.services.matching_service import MatchingService
from app.db.session import SessionLocal


class OpportunityOrchestrator:
    @staticmethod
    def start_discovery_run(
        db: Session,
        user: User,
        request: DiscoveryRunRequest
    ) -> AgentRun:
        """
        Creates an AgentRun record and dispatches background discovery.
        """
        run = AgentRun(
            user_id=user.id,
            run_type="opportunity_discovery",
            status=RunStatus.QUEUED,
            query_params=request.model_dump(),
            providers_queried=[],
            providers_succeeded=[],
            providers_failed=[],
            results_discovered_count=0,
            results_deduplicated_count=0,
            opportunities_created_count=0,
            execution_time_seconds=0.0
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def execute_discovery_run_sync(run_id: str, user_id: str, request_params: Dict[str, Any]) -> None:
        """
        Synchronous wrapper allowing background task execution in worker pools and test harnesses.
        """
        try:
            asyncio.run(OpportunityOrchestrator.execute_discovery_run_async(run_id, user_id, request_params))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(OpportunityOrchestrator.execute_discovery_run_async(run_id, user_id, request_params))
            loop.close()

    @staticmethod
    async def execute_discovery_run_async(run_id: str, user_id: str, request_params: Dict[str, Any]) -> None:
        """
        Background worker executing multi-provider opportunity discovery.
        Grounded in verified evidence with transparent deduplication and duplicate database prevention.
        """
        db = SessionLocal()
        start_time = time.perf_counter()
        try:
            run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
            user = db.query(User).filter(User.id == user_id).first()
            if not run or not user:
                return

            run.status = RunStatus.RUNNING
            db.commit()

            # 1. Fetch Candidate Profile Intelligence
            candidate_intel = ProfileIntelligenceService.generate_candidate_intelligence(db, user)

            # Resolve query filters (use candidate preferences if not specified in request)
            target_roles = request_params.get("target_roles") or candidate_intel.preferences.get("desired_roles") or ["Software Engineer"]
            skills = request_params.get("skills") or [s.name for s in candidate_intel.verified_skills][:5] or ["Python"]
            industries = request_params.get("industries") or candidate_intel.preferences.get("preferred_industries") or ["Technology"]
            locations = request_params.get("locations") or candidate_intel.preferences.get("preferred_locations") or ["India", "Remote"]
            remote_preference = request_params.get("remote_preference") or candidate_intel.preferences.get("remote_preference") or "flexible"
            work_arrangement = request_params.get("work_arrangement")
            employment_type = request_params.get("employment_type")
            experience_level = request_params.get("experience_level") or candidate_intel.preferences.get("experience_level") or "mid"
            opp_type_filter = request_params.get("opportunity_type")
            limit = request_params.get("limit") or settings.DISCOVERY_DEFAULT_LIMIT

            # 2. Inspect Configured Providers
            configured_providers = provider_registry.get_configured_providers()
            providers_queried: List[str] = [p.provider_name for p in configured_providers]
            providers_succeeded: List[str] = []
            providers_failed: List[Dict[str, Any]] = []

            run.providers_queried = providers_queried
            db.commit()

            discovered_jobs: List[NormalizedJob] = []
            discovered_companies: List[NormalizedCompany] = []

            # 3. Concurrent Multi-Source Querying
            # Construct focused role query incorporating relevant variants
            primary_role = target_roles[0].strip() if target_roles else "Software Engineer"
            role_terms = primary_role
            if "aiml" in primary_role.lower() or "ai/ml" in primary_role.lower():
                role_terms = "AI/ML Engineer Machine Learning"
            
            top_skills = " ".join(skills[:2]) if skills else ""
            job_query = f"{role_terms} {top_skills}".strip()
            
            # Clean and normalize target locations (up to 4 locations searched with bounded concurrency)
            cleaned_locations: List[str] = []
            if locations:
                for l in locations:
                    if isinstance(l, str) and l.strip():
                        val = l.strip()
                        if val.lower() not in [x.lower() for x in cleaned_locations]:
                            cleaned_locations.append(val)
            if not cleaned_locations:
                cleaned_locations = ["India"]

            target_locations_to_query = cleaned_locations[:4]
            per_loc_limit = max(5, limit // len(target_locations_to_query))
            is_remote_only = remote_preference == "remote" or (work_arrangement and work_arrangement.lower() == "remote")

            sem = asyncio.Semaphore(4)

            async def query_provider_jobs_for_loc(p, target_loc: str):
                async with sem:
                    try:
                        jobs = await p.search_jobs(
                            query=job_query,
                            location=target_loc,
                            remote_only=is_remote_only,
                            limit=per_loc_limit,
                            skills=skills,
                            target_roles=target_roles,
                            experience_level=experience_level
                        )
                        return p.provider_name, "jobs", jobs, None
                    except TypeError:
                        try:
                            jobs = await p.search_jobs(
                                query=job_query,
                                location=target_loc,
                                remote_only=is_remote_only,
                                limit=per_loc_limit
                            )
                            return p.provider_name, "jobs", jobs, None
                        except Exception as e:
                            return p.provider_name, "jobs", [], str(e)
                    except Exception as e:
                        return p.provider_name, "jobs", [], str(e)

            async def query_provider_companies(p):
                try:
                    comps = await p.search_companies(
                        skills=skills,
                        industries=industries,
                        roles=target_roles,
                        locations=cleaned_locations,
                        limit=min(limit, 10)
                    )
                    return p.provider_name, "companies", comps, None
                except Exception as e:
                    return p.provider_name, "companies", [], str(e)

            tasks = []
            for p in configured_providers:
                for target_loc in target_locations_to_query:
                    tasks.append(query_provider_jobs_for_loc(p, target_loc))
                tasks.append(query_provider_companies(p))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, tuple):
                        p_name, kind, data, err = res
                        if err:
                            providers_failed.append({"provider": p_name, "type": kind, "error": err})
                        else:
                            if p_name not in providers_succeeded:
                                providers_succeeded.append(p_name)
                            if kind == "jobs":
                                discovered_jobs.extend(data)
                            elif kind == "companies":
                                discovered_companies.extend(data)

            total_discovered = len(discovered_jobs) + len(discovered_companies)
            run.results_discovered_count = total_discovered

            # 4. Deduplication & Quality Filtering Gate
            deduped_jobs = OpportunityDeduplicator.deduplicate_jobs(discovered_jobs)
            deduped_companies = OpportunityDeduplicator.deduplicate_companies(discovered_companies)
            total_deduped = len(deduped_jobs) + len(deduped_companies)
            run.results_deduplicated_count = total_deduped

            # 5. Candidate Matching, Scoring, and Persistence
            created_count = 0

            # A. Process Advertised Jobs
            for job_item in deduped_jobs:
                if opp_type_filter and opp_type_filter != OpportunityType.ADVERTISED.value:
                    continue

                # Clean employer name and research company classification
                employer_name = OpportunityNormalizer.clean_employer_name(
                    company_name=job_item.company_name,
                    title=job_item.title,
                    url=job_item.primary_url
                )
                research_res = await CompanyResearchService.research_company_classification_async(
                    company_name=employer_name,
                    website_url=job_item.primary_url,
                    existing_description=job_item.description
                )
                classification = research_res["classification"]
                size_range = research_res.get("size_range")

                # Find or create company
                company = db.query(Company).filter(Company.name == employer_name).first()
                if not company:
                    clean_norm = OpportunityNormalizer.normalize_title(employer_name).lower().replace(" ", "")
                    domain = f"{clean_norm}.com" if clean_norm else "unknown.com"
                    company = Company(
                        name=employer_name,
                        domain=domain,
                        website_url=job_item.primary_url,
                        description=f"{classification.replace('_', ' ').capitalize()} hiring organization for {job_item.title}.",
                        industry=industries[0] if industries else "Technology",
                        size_range=size_range,
                        classification=classification,
                        headquarters=job_item.location or "India",
                        growth_signal_score=0.7,
                        alignment_score=0.8,
                        signals_summary="Active verified job advertisement discovered.",
                        signals_data=[{
                            "signal_type": "active_job_posting",
                            "headline": f"Hiring for {job_item.title}",
                            "date": datetime.now(timezone.utc).isoformat(),
                            "evidence_url": job_item.primary_url,
                            "confidence": job_item.confidence,
                            "classification": classification,
                            "size_range": size_range,
                            "evidence_excerpt": research_res.get("evidence_excerpt")
                        }],
                        why_contact=f"Active verified opening for {job_item.title}.",
                        why_wait="Ensure required competencies are cited in application materials.",
                        has_advertised_openings=True
                    )
                    db.add(company)
                    db.flush()
                else:
                    company.has_advertised_openings = True
                    if (company.classification == "unknown" or not company.classification) and classification != "unknown":
                        company.classification = classification
                    if not company.size_range and size_range:
                        company.size_range = size_range

                norm_title = OpportunityNormalizer.normalize_title(job_item.title)
                salary_extracted = OpportunityNormalizer.extract_salary(job_item.description)

                # Canonicalize URL before DB lookup and insertion
                clean_primary_url = OpportunityDeduplicator.canonicalize_url(job_item.primary_url)
                job_item.primary_url = clean_primary_url

                # Prevent Duplicate Jobs in DB: Find existing Job by primary_url or (company_id, normalized_title)
                job_record = (
                    db.query(Job)
                    .filter(
                        (Job.primary_url == clean_primary_url) |
                        ((Job.company_id == company.id) & (Job.normalized_title == norm_title))
                    )
                    .first()
                )

                if not job_record:
                    parsed_verified_at = None
                    if job_item.last_verified_at:
                        try:
                            parsed_verified_at = datetime.fromisoformat(str(job_item.last_verified_at).replace("Z", "+00:00"))
                        except Exception:
                            parsed_verified_at = datetime.now(timezone.utc)

                    job_record = Job(
                        company_id=company.id,
                        company_name=company.name,
                        title=job_item.title,
                        normalized_title=norm_title,
                        location=job_item.location,
                        is_remote=job_item.is_remote,
                        work_arrangement=job_item.work_arrangement,
                        employment_type=job_item.employment_type,
                        description=job_item.description,
                        primary_url=job_item.primary_url,
                        application_url=job_item.application_url or job_item.primary_url,
                        salary_range=job_item.salary_range or salary_extracted,
                        verification_status=job_item.verification_status or "LISTING_FOUND_STATUS_UNVERIFIED",
                        verification_details=job_item.verification_details or {},
                        is_verified=bool(job_item.is_verified),
                        last_verified_at=parsed_verified_at,
                        source_urls=[job_item.primary_url],
                        posting_date=job_item.posting_date,
                        source_name=job_item.source_name,
                        experience_required=salary_extracted
                    )
                    db.add(job_record)
                    db.flush()

                    # Add extracted requirements
                    for sk in job_item.extracted_skills:
                        req = JobRequirement(
                            job_id=job_record.id,
                            requirement_type="skill",
                            description=sk,
                            is_critical=False
                        )
                        db.add(req)
                else:
                    # Enrich existing job if new information discovered
                    if salary_extracted and not job_record.experience_required:
                        job_record.experience_required = salary_extracted
                    if (job_item.salary_range or salary_extracted) and not job_record.salary_range:
                        job_record.salary_range = job_item.salary_range or salary_extracted
                    if job_item.application_url and not job_record.application_url:
                        job_record.application_url = job_item.application_url
                    if job_item.is_verified and not job_record.is_verified:
                        job_record.is_verified = True
                        job_record.verification_status = job_item.verification_status
                        job_record.verification_details = job_item.verification_details or {}
                        try:
                            job_record.last_verified_at = datetime.fromisoformat(str(job_item.last_verified_at).replace("Z", "+00:00")) if job_item.last_verified_at else datetime.now(timezone.utc)
                        except Exception:
                            job_record.last_verified_at = datetime.now(timezone.utc)
                    if job_item.primary_url not in (job_record.source_urls or []):
                        job_record.source_urls = list(set((job_record.source_urls or []) + [job_item.primary_url]))

                # Match against candidate using calibrated scoring
                match_result = MatchingService.match_job(
                    job=job_item,
                    candidate_intel=candidate_intel,
                    preferred_locations=locations,
                    remote_preference=remote_preference,
                    experience_level=experience_level
                )

                # Prevent Duplicate Opportunity for this user
                existing_opp = (
                    db.query(Opportunity)
                    .filter(Opportunity.user_id == user.id, Opportunity.job_id == job_record.id)
                    .first()
                )

                if existing_opp:
                    # Update scores and link to latest run
                    existing_opp.discovery_run_id = run.id
                    existing_opp.match_score = match_result["match_score"]
                    existing_opp.evidence_confidence = match_result["evidence_confidence"]
                    existing_opp.recommended_action = match_result["recommended_action"]
                    existing_opp.matched_skills = match_result["matched_skills"]
                    existing_opp.missing_skills = match_result["missing_skills"]
                    existing_opp.critical_failures = match_result["critical_failures"]
                    existing_opp.explanation = match_result["explanation"]
                    if job_item.extraction_quality:
                        existing_opp.extraction_quality = job_item.extraction_quality
                    if job_item.company_confidence:
                        existing_opp.company_confidence = job_item.company_confidence
                    opp = existing_opp
                else:
                    opp = Opportunity(
                        user_id=user.id,
                        job_id=job_record.id,
                        company_id=company.id,
                        discovery_run_id=run.id,
                        opportunity_type=OpportunityType.ADVERTISED,
                        status=OpportunityStatus.ACTIVE,
                        match_score=match_result["match_score"],
                        evidence_confidence=match_result["evidence_confidence"],
                        recommended_action=match_result["recommended_action"],
                        matched_skills=match_result["matched_skills"],
                        missing_skills=match_result["missing_skills"],
                        critical_failures=match_result["critical_failures"],
                        explanation=match_result["explanation"],
                        extraction_quality=job_item.extraction_quality or 0.85,
                        company_confidence=job_item.company_confidence or 0.85
                    )
                    db.add(opp)
                    db.flush()
                    created_count += 1

                # Record Evidence if not already existing
                existing_evidence = (
                    db.query(Evidence)
                    .filter(Evidence.opportunity_id == opp.id, Evidence.source_url == job_item.primary_url)
                    .first()
                )
                if not existing_evidence:
                    source_record = Source(
                        name=job_item.source_name,
                        provider=job_item.source_provider,
                        url=job_item.primary_url,
                        raw_content_preview=job_item.description[:300] if job_item.description else None
                    )
                    db.add(source_record)
                    db.flush()

                    evidence_record = Evidence(
                        opportunity_id=opp.id,
                        company_id=company.id,
                        job_id=job_record.id,
                        source_id=source_record.id,
                        claim_type=ClaimType.OBSERVED_FACT,
                        claim_text=f"Confirmed active job posting: {job_item.title} at {company.name}.",
                        source_url=job_item.primary_url,
                        supporting_excerpt=job_item.evidence_excerpt,
                        confidence=job_item.confidence
                    )
                    db.add(evidence_record)

            # B. Process Unadvertised Companies
            for comp_item in deduped_companies:
                evaluation = CompanyResearchService.evaluate_company_signals(
                    company=comp_item,
                    candidate_skills=skills,
                    candidate_roles=target_roles,
                    candidate_industries=industries,
                    has_advertised_jobs=False
                )

                opp_type = evaluation["opportunity_type"]
                if opp_type_filter and opp_type_filter != opp_type.value:
                    continue

                research_res = await CompanyResearchService.research_company_classification_async(
                    company_name=comp_item.name,
                    domain=comp_item.domain,
                    website_url=comp_item.website_url,
                    existing_description=comp_item.description,
                    existing_signals=[s.model_dump() for s in comp_item.signals]
                )
                classification = research_res["classification"]
                size_range = research_res.get("size_range")

                company = db.query(Company).filter(Company.name == comp_item.name).first()
                if not company:
                    company = Company(
                        name=comp_item.name,
                        domain=comp_item.domain,
                        website_url=comp_item.website_url,
                        description=comp_item.description or f"{classification.replace('_', ' ').capitalize()} organization.",
                        industry=comp_item.industry or "Technology",
                        size_range=size_range,
                        classification=classification,
                        headquarters=comp_item.headquarters or "India",
                        growth_signal_score=evaluation["growth_signal_score"],
                        alignment_score=evaluation["alignment_score"],
                        signals_summary=evaluation["signals_summary"],
                        signals_data=[s.model_dump() for s in comp_item.signals],
                        why_contact=evaluation["why_contact"],
                        why_wait=evaluation["why_wait"],
                        has_advertised_openings=False
                    )
                    db.add(company)
                    db.flush()
                else:
                    if (company.classification == "unknown" or not company.classification) and classification != "unknown":
                        company.classification = classification
                    if not company.size_range and size_range:
                        company.size_range = size_range

                match_result = MatchingService.match_company(
                    company=comp_item,
                    candidate_intel=candidate_intel,
                    evaluation=evaluation
                )

                # Check for existing opportunity
                existing_comp_opp = (
                    db.query(Opportunity)
                    .filter(
                        Opportunity.user_id == user.id,
                        Opportunity.company_id == company.id,
                        Opportunity.job_id.is_(None)
                    )
                    .first()
                )

                if existing_comp_opp:
                    existing_comp_opp.discovery_run_id = run.id
                    existing_comp_opp.match_score = match_result["match_score"]
                    existing_comp_opp.evidence_confidence = match_result["evidence_confidence"]
                    existing_comp_opp.recommended_action = match_result["recommended_action"]
                    existing_comp_opp.explanation = match_result["explanation"]
                    opp = existing_comp_opp
                else:
                    opp = Opportunity(
                        user_id=user.id,
                        job_id=None,
                        company_id=company.id,
                        discovery_run_id=run.id,
                        opportunity_type=opp_type,
                        status=OpportunityStatus.ACTIVE,
                        match_score=match_result["match_score"],
                        evidence_confidence=match_result["evidence_confidence"],
                        recommended_action=match_result["recommended_action"],
                        matched_skills=match_result["matched_skills"],
                        missing_skills=match_result["missing_skills"],
                        critical_failures=match_result["critical_failures"],
                        explanation=match_result["explanation"]
                    )
                    db.add(opp)
                    db.flush()
                    created_count += 1

                existing_evidence = (
                    db.query(Evidence)
                    .filter(Evidence.opportunity_id == opp.id, Evidence.source_url == comp_item.source_url)
                    .first()
                )
                if not existing_evidence:
                    source_record = Source(
                        name=comp_item.source_name,
                        provider=comp_item.source_provider,
                        url=comp_item.source_url,
                        raw_content_preview=comp_item.description[:300] if comp_item.description else None
                    )
                    db.add(source_record)
                    db.flush()

                    evidence_record = Evidence(
                        opportunity_id=opp.id,
                        company_id=company.id,
                        job_id=None,
                        source_id=source_record.id,
                        claim_type=ClaimType.SYSTEM_INFERENCE if opp_type == OpportunityType.EMERGING else ClaimType.OBSERVED_FACT,
                        claim_text=f"Company alignment and growth signals evaluated for {company.name}.",
                        source_url=comp_item.source_url,
                        supporting_excerpt=comp_item.evidence_excerpt,
                        confidence=comp_item.confidence
                    )
                    db.add(evidence_record)

            # 6. Finalize Run Status with Honest Accounting
            run.opportunities_created_count = created_count
            run.providers_succeeded = providers_succeeded
            run.providers_failed = providers_failed
            run.execution_time_seconds = round(time.perf_counter() - start_time, 2)
            run.diagnostics = {
                "providers_queried": providers_queried,
                "providers_succeeded": providers_succeeded,
                "providers_failed": providers_failed,
                "total_candidates_discovered": total_discovered,
                "total_candidates_deduplicated": total_deduped,
                "opportunities_created_count": created_count,
                "verification_breakdown": {
                    "verified_open": sum(1 for j in deduped_jobs if getattr(j, "verification_status", None) == "VERIFIED_OPEN"),
                    "listing_found_unverified": sum(1 for j in deduped_jobs if getattr(j, "verification_status", None) == "LISTING_FOUND_STATUS_UNVERIFIED")
                },
                "execution_time_seconds": run.execution_time_seconds
            }

            if len(configured_providers) == 0:
                run.status = RunStatus.FAILED
                run.error_summary = "No live external search providers configured (TAVILY_API_KEY / EXA_API_KEY). Please configure an API key to discover live web openings."
            elif len(providers_failed) > 0 and len(providers_succeeded) == 0:
                run.status = RunStatus.FAILED
                run.error_summary = f"All {len(providers_failed)} configured provider(s) failed during search."
            elif len(providers_failed) > 0 and len(providers_succeeded) > 0:
                run.status = RunStatus.PARTIAL
                run.error_summary = f"Partial discovery: {len(providers_succeeded)} provider(s) succeeded; {len(providers_failed)} failed."
            else:
                run.status = RunStatus.COMPLETED
                run.error_summary = None

            db.commit()

        except Exception as e:
            db.rollback()
            try:
                run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
                if run:
                    run.status = RunStatus.FAILED
                    run.error_summary = f"Discovery run failed: {str(e)}"
                    run.execution_time_seconds = round(time.perf_counter() - start_time, 2)
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()
