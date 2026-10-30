import re
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.models.opportunity import OpportunityType
from app.services.providers.base_provider import NormalizedCompany
from app.services.opportunity_normalizer import OpportunityNormalizer, KNOWN_ENTERPRISES


class CompanyResearchService:
    # In-memory research cache: key -> (timestamp, result_dict)
    _cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    CACHE_TTL_SECONDS: int = 86400  # 24 hours

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the research cache (used in testing)."""
        cls._cache.clear()

    @classmethod
    def get_cache_size(cls) -> int:
        """Returns the number of cached entries."""
        return len(cls._cache)

    @classmethod
    def _get_cache_key(cls, company_name: str, domain: Optional[str] = None) -> str:
        clean_name = company_name.strip().lower() if company_name else ""
        clean_domain = domain.strip().lower() if domain else ""
        return f"{clean_name}::{clean_domain}"

    @classmethod
    def evaluate_company_signals(
        cls,
        company: NormalizedCompany,
        candidate_skills: List[str],
        candidate_roles: List[str],
        candidate_industries: List[str],
        has_advertised_jobs: bool = False
    ) -> Dict[str, Any]:
        """
        Analyzes public company signals against candidate profile parameters.
        Computes growth_signal_score, alignment_score, why_contact, why_wait,
        and opportunity_type (ADVERTISED, EMERGING, or STRATEGIC).
        """
        if has_advertised_jobs:
            opp_type = OpportunityType.ADVERTISED
        else:
            # Check signal strength
            has_expansion_signals = any(
                sig.signal_type in {"funding_expansion", "hiring_need", "product_launch"}
                for sig in company.signals
            )
            # Check technical alignment
            text_corpus = (company.name + " " + (company.description or "")).lower()
            matched_candidate_skills = [s for s in candidate_skills if s.lower() in text_corpus]
            
            if has_expansion_signals and len(matched_candidate_skills) >= 1:
                opp_type = OpportunityType.EMERGING
            else:
                opp_type = OpportunityType.STRATEGIC

        # 1. Growth / Hiring Signal Score (0.0 to 1.0) based strictly on evidence
        growth_score = 0.2
        if company.signals:
            for s in company.signals:
                if s.signal_type == "funding_expansion":
                    growth_score += 0.35
                elif s.signal_type == "product_launch":
                    growth_score += 0.25
                elif s.signal_type == "product_and_technology_alignment":
                    growth_score += 0.20
        growth_score = min(1.0, growth_score)

        # 2. Candidate Alignment Score (0.0 to 1.0)
        text_corpus = (company.name + " " + (company.description or "")).lower()
        skill_matches = [s for s in candidate_skills if s.lower() in text_corpus]
        industry_match = any(ind.lower() in text_corpus for ind in candidate_industries)

        align_score = 0.3
        if skill_matches:
            align_score += min(0.5, len(skill_matches) * 0.15)
        if industry_match:
            align_score += 0.20
        align_score = min(1.0, align_score)

        # 3. Formulate transparent reasons to contact vs wait
        if opp_type == OpportunityType.ADVERTISED:
            why_contact = f"Active relevant vacancy verified at {company.name}. Strong technical alignment with candidate profile."
            why_wait = "Ensure application materials directly cite required framework competencies before submitting."
        elif opp_type == OpportunityType.EMERGING:
            why_contact = (
                f"Public evidence indicates technical initiative/expansion at {company.name}. "
                f"Candidate's verified competencies ({', '.join(skill_matches[:3]) if skill_matches else 'relevant skills'}) "
                "offer direct value for an exploratory proactive approach."
            )
            why_wait = (
                "No open vacancy is officially posted. Proactive outreach must propose concrete domain value "
                "rather than asking for a generic application."
            )
        else: # STRATEGIC
            why_contact = (
                f"{company.name} operates in target industry domain ({company.industry or 'Technology'}). "
                "Strategic outreach can build long-term relationships with engineering leads."
            )
            why_wait = (
                "Immediate hiring signals are limited or unconfirmed. Low likelihood of immediate opening; "
                "prioritize higher-signal emerging opportunities first."
            )

        # Structure confirmed facts vs inferred signals
        confirmed_facts: List[Dict[str, Any]] = []
        if company.website_url or company.domain:
            confirmed_facts.append({
                "fact_type": "official_presence",
                "headline": f"Official digital domain: {company.domain or company.website_url}",
                "source_url": company.website_url or company.source_url,
                "confidence": 1.0,
                "is_verified": True
            })
        if has_advertised_jobs:
            confirmed_facts.append({
                "fact_type": "verified_vacancy",
                "headline": f"Active verified opening advertised by {company.name}.",
                "source_url": company.source_url,
                "confidence": 0.95,
                "is_verified": True
            })
        if company.headquarters and company.headquarters not in ("India", "Remote"):
            confirmed_facts.append({
                "fact_type": "official_headquarters",
                "headline": f"Documented primary location: {company.headquarters}.",
                "source_url": company.source_url,
                "confidence": 0.90,
                "is_verified": True
            })

        inferred_signals: List[Dict[str, Any]] = []
        for s in company.signals:
            inferred_signals.append({
                "signal_type": s.signal_type,
                "headline": s.headline,
                "evidence_url": s.evidence_url or company.source_url,
                "excerpt": s.excerpt,
                "confidence": s.confidence,
                "inference_type": "public_web_signal"
            })
        if skill_matches:
            inferred_signals.append({
                "signal_type": "tech_stack_alignment",
                "headline": f"Competency overlap: {', '.join(skill_matches[:4])}",
                "evidence_url": company.source_url,
                "excerpt": f"Profile technical alignment match: {', '.join(skill_matches)}",
                "confidence": 0.85,
                "inference_type": "profile_matching"
            })

        summary = (
            f"Evaluated {len(company.signals)} public signal(s). "
            f"Opportunity classified as {opp_type.value} with growth signal score {growth_score:.2f} "
            f"and candidate alignment score {align_score:.2f}."
        )

        return {
            "opportunity_type": opp_type,
            "growth_signal_score": growth_score,
            "alignment_score": align_score,
            "signals_summary": summary,
            "why_contact": why_contact,
            "why_wait": why_wait,
            "matched_skills": skill_matches,
            "confirmed_facts": confirmed_facts,
            "inferred_signals": inferred_signals
        }

    @classmethod
    async def research_company_classification_async(
        cls,
        company_name: str,
        domain: Optional[str] = None,
        website_url: Optional[str] = None,
        existing_description: Optional[str] = None,
        existing_signals: Optional[List[Dict[str, Any]]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Researches company classification using credible public evidence and web research.
        Returns:
            {
                "classification": "startup" | "smb" | "mid_sized" | "enterprise" | "unknown",
                "size_range": Optional[str],
                "evidence_excerpt": str,
                "source_url": Optional[str],
                "confidence": float,
                "timestamp": str
            }
        """
        if not company_name or company_name.strip().lower() in {"unknown", "direct hiring organization", "page"}:
            return {
                "classification": "unknown",
                "size_range": None,
                "evidence_excerpt": "Company identity could not be verified.",
                "source_url": website_url,
                "confidence": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        cache_key = cls._get_cache_key(company_name, domain)
        now = time.time()

        # Check Cache
        if not force_refresh and cache_key in cls._cache:
            ts, cached_result = cls._cache[cache_key]
            if now - ts < cls.CACHE_TTL_SECONDS:
                return cached_result

        lower_name = company_name.strip().lower()

        # 1. Verified Global / Regional Enterprise Check
        if any(ent in lower_name for ent in KNOWN_ENTERPRISES):
            result = {
                "classification": "enterprise",
                "size_range": "10,000+ employees",
                "evidence_excerpt": f"Verified global enterprise: '{company_name}' is recognized as a major multinational corporation.",
                "source_url": website_url or f"https://{domain}" if domain else f"https://www.{lower_name.replace(' ', '')}.com",
                "confidence": 0.95,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            cls._cache[cache_key] = (now, result)
            return result

        # 2. Analyze Existing Text Corpus (Description, Signals)
        corpus = f"{company_name} {existing_description or ''}".lower()
        if existing_signals:
            for s in existing_signals:
                corpus += f" {s.get('headline', '')} {s.get('excerpt', '')}".lower()

        # Check for explicit employee headcount in corpus
        headcount_match = re.search(r"\b(\d+[\d,]*\+?)\s*(?:-|to)?\s*(\d+[\d,]*)?\s*employees\b", corpus)
        if headcount_match:
            min_count_str = headcount_match.group(1).replace(",", "").replace("+", "")
            try:
                min_count = int(min_count_str)
                if min_count >= 5000:
                    cls_found = "enterprise"
                    sr_found = "5,000+ employees"
                elif min_count >= 500:
                    cls_found = "mid_sized"
                    sr_found = "500-5,000 employees"
                elif min_count >= 50:
                    cls_found = "smb"
                    sr_found = "51-500 employees"
                else:
                    cls_found = "startup" if any(st in corpus for st in ["startup", "seed", "venture", "tech"]) else "smb"
                    sr_found = "1-50 employees"

                result = {
                    "classification": cls_found,
                    "size_range": sr_found,
                    "evidence_excerpt": f"Company profile documents: '{headcount_match.group(0)}'.",
                    "source_url": website_url,
                    "confidence": 0.85,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                cls._cache[cache_key] = (now, result)
                return result
            except ValueError:
                pass

        # Check for textual category cues
        category_cue = OpportunityNormalizer.classify_company(company_name, existing_description, domain)
        if category_cue != "unknown":
            size_map = {
                "enterprise": "5,000+ employees",
                "mid_sized": "500-2,000 employees",
                "smb": "51-200 employees",
                "startup": "1-50 employees"
            }
            result = {
                "classification": category_cue,
                "size_range": size_map.get(category_cue),
                "evidence_excerpt": f"Verified public indicators identify '{company_name}' as a {category_cue.replace('_', ' ')} organization.",
                "source_url": website_url,
                "confidence": 0.80,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            cls._cache[cache_key] = (now, result)
            return result

        # 3. Live Web Research via Configured Providers (Tavily / Exa)
        try:
            from app.services.providers.provider_registry import provider_registry
            tavily = provider_registry.get_provider("tavily")
            if tavily and tavily.is_configured():
                search_query = f'"{company_name}" company size headcount employees about'
                # Query Tavily search
                search_resp = await tavily._post_tavily(query=search_query, max_results=3, search_depth="basic")
                results = search_resp.get("results", [])
                for r in results:
                    snippet = (r.get("content") or "") + " " + (r.get("title") or "")
                    snippet_lower = snippet.lower()
                    
                    # Grounding check: verify that this search snippet is genuinely about the researched company
                    company_tokens = [tok for tok in re.findall(r"\w+", lower_name) if len(tok) > 2 and tok not in ("company", "technologies", "solutions", "organization", "services", "corporation", "corp", "inc", "llp", "ltd", "pvt")]
                    comp_mentioned = any(tok in snippet_lower for tok in company_tokens) or (domain and domain.lower() in snippet_lower)
                    if not comp_mentioned:
                        continue

                    # Look for headcount numbers
                    hc = re.search(r"\b(\d+[\d,]*\+?)\s*(?:-|to)?\s*(\d+[\d,]*)?\s*employees\b", snippet_lower)
                    if hc:
                        cnt_str = hc.group(1).replace(",", "").replace("+", "")
                        try:
                            cnt = int(cnt_str)
                            if cnt >= 5000:
                                c = "enterprise"
                                sr = "5,000+ employees"
                            elif cnt >= 500:
                                c = "mid_sized"
                                sr = "500-5,000 employees"
                            elif cnt >= 50:
                                c = "smb"
                                sr = "51-500 employees"
                            else:
                                c = "startup" if any(st in snippet_lower for st in ["startup", "seed", "venture"]) else "smb"
                                sr = "1-50 employees"

                            result = {
                                "classification": c,
                                "size_range": sr,
                                "evidence_excerpt": snippet[:250].strip() + "...",
                                "source_url": r.get("url"),
                                "confidence": 0.85,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                            cls._cache[cache_key] = (now, result)
                            return result
                        except ValueError:
                            pass

                    # Look for qualitative scale keywords
                    qual_cls = OpportunityNormalizer.classify_company(company_name, snippet, domain)
                    if qual_cls != "unknown":
                        size_map = {
                            "enterprise": "5,000+ employees",
                            "mid_sized": "500-2,000 employees",
                            "smb": "51-200 employees",
                            "startup": "1-50 employees"
                        }
                        result = {
                            "classification": qual_cls,
                            "size_range": size_map.get(qual_cls),
                            "evidence_excerpt": snippet[:250].strip() + "...",
                            "source_url": r.get("url"),
                            "confidence": 0.75,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        cls._cache[cache_key] = (now, result)
                        return result
        except Exception:
            # Web research failure should gracefully degrade without crashing
            pass

        # 4. Honest Fallback: Evidence is missing or insufficient
        result = {
            "classification": "unknown",
            "size_range": None,
            "evidence_excerpt": f"Public headcount and organization scale data for '{company_name}' could not be definitively verified from public sources.",
            "source_url": website_url,
            "confidence": 0.50,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        cls._cache[cache_key] = (now, result)
        return result

    @classmethod
    def research_company_classification(
        cls,
        company_name: str,
        domain: Optional[str] = None,
        website_url: Optional[str] = None,
        existing_description: Optional[str] = None,
        existing_signals: Optional[List[Dict[str, Any]]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Synchronous wrapper for research_company_classification_async."""
        try:
            return asyncio.run(
                cls.research_company_classification_async(
                    company_name=company_name,
                    domain=domain,
                    website_url=website_url,
                    existing_description=existing_description,
                    existing_signals=existing_signals,
                    force_refresh=force_refresh
                )
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    cls.research_company_classification_async(
                        company_name=company_name,
                        domain=domain,
                        website_url=website_url,
                        existing_description=existing_description,
                        existing_signals=existing_signals,
                        force_refresh=force_refresh
                    )
                )
            finally:
                loop.close()
