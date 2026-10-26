"""
Deduplication Cleanup Script for OutReachIQ Database
Safely merges duplicate Job and Opportunity records in outreachiq.db.

Usage:
    python backend/scripts/deduplicate_jobs_and_opportunities.py --dry-run
    python backend/scripts/deduplicate_jobs_and_opportunities.py --commit
"""

import sys
import os
import argparse
import sqlite3
import json
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from typing import Dict, List, Tuple, Set


TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'ref', 'trk', 'fbclid', 'gclid', 'subid', 'vjk'
}


def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    netloc = parts.netloc.lower()
    filtered_query = []
    if parts.query:
        for k, v in parse_qsl(parts.query, keep_blank_values=False):
            if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_"):
                filtered_query.append((k, v))
        filtered_query.sort()
    new_query = urlencode(filtered_query)
    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), netloc, path, new_query, ""))


def run_cleanup(db_path: str, commit: bool = False) -> None:
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)

    print(f"Opening database: {db_path}")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA integrity_check")
    ic = cur.fetchone()[0]
    if ic != "ok":
        print(f"Integrity check failed: {ic}")
        con.close()
        sys.exit(1)
    print("Pre-cleanup integrity check: OK")

    cur.execute("SELECT count(*) FROM jobs")
    job_count_before = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM opportunities")
    opp_count_before = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM evidence")
    ev_count_before = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM job_requirements")
    req_count_before = cur.fetchone()[0]

    print(f"Initial counts -> Jobs: {job_count_before}, Opportunities: {opp_count_before}, Evidence: {ev_count_before}, Requirements: {req_count_before}")

    # Step 1: Query all jobs ordered by created_at ascending (earliest created is canonical)
    cur.execute("""
        SELECT id, primary_url, company_id, company_name, title, normalized_title, 
               location, is_verified, verification_status, verification_details, 
               last_verified_at, salary_range, description, source_urls, source_name, created_at
        FROM jobs 
        ORDER BY created_at ASC
    """)
    rows = cur.fetchall()

    canonical_groups: Dict[str, List[tuple]] = {}
    for r in rows:
        curl = canonicalize_url(r[1])
        canonical_groups.setdefault(curl, []).append(r)

    dup_groups = {curl: jlist for curl, jlist in canonical_groups.items() if len(jlist) > 1}
    print(f"Identified {len(dup_groups)} duplicate URL groups across {len(canonical_groups)} total canonical URLs.")

    pruned_jobs = 0
    pruned_opps = 0
    pruned_ev = 0
    pruned_reqs = 0
    relinked_reqs = 0

    try:
        cur.execute("BEGIN TRANSACTION")

        for curl, jlist in dup_groups.items():
            canonical_job = jlist[0]
            canon_id = canonical_job[0]
            dup_jobs = jlist[1:]

            # Aggregate metadata into canonical job
            merged_source_urls = set()
            try:
                existing_surls = json.loads(canonical_job[13]) if canonical_job[13] else []
                if isinstance(existing_surls, list):
                    merged_source_urls.update(existing_surls)
            except Exception:
                pass
            merged_source_urls.add(canonical_job[1])

            has_verified = bool(canonical_job[7])
            best_ver_status = canonical_job[8]
            best_ver_details = canonical_job[9]
            best_ver_date = canonical_job[10]
            best_salary = canonical_job[11]

            for dj in dup_jobs:
                d_id = dj[0]
                d_purl = dj[1]
                merged_source_urls.add(d_purl)
                try:
                    surls = json.loads(dj[13]) if dj[13] else []
                    if isinstance(surls, list):
                        merged_source_urls.update(surls)
                except Exception:
                    pass

                if dj[7] and not has_verified:
                    has_verified = True
                    best_ver_status = dj[8]
                    best_ver_details = dj[9]
                    best_ver_date = dj[10]
                if dj[11] and not best_salary:
                    best_salary = dj[11]

            # Update canonical job with canonical URL and enriched attributes
            cur.execute("""
                UPDATE jobs 
                SET primary_url = ?, source_urls = ?, is_verified = ?, 
                    verification_status = ?, verification_details = ?, 
                    last_verified_at = ?, salary_range = ?
                WHERE id = ?
            """, (
                curl,
                json.dumps(sorted(list(merged_source_urls))),
                1 if has_verified else 0,
                best_ver_status,
                best_ver_details,
                best_ver_date,
                best_salary,
                canon_id
            ))

            # Deduplicate requirements for canonical job vs duplicates
            cur.execute("SELECT description, requirement_type FROM job_requirements WHERE job_id = ?", (canon_id,))
            canon_req_set = set(cur.fetchall())

            for dj in dup_jobs:
                d_id = dj[0]
                cur.execute("SELECT id, description, requirement_type FROM job_requirements WHERE job_id = ?", (d_id,))
                d_reqs = cur.fetchall()
                for rid, rdesc, rtype in d_reqs:
                    if (rdesc, rtype) in canon_req_set:
                        cur.execute("DELETE FROM job_requirements WHERE id = ?", (rid,))
                        pruned_reqs += 1
                    else:
                        cur.execute("UPDATE job_requirements SET job_id = ? WHERE id = ?", (canon_id, rid))
                        canon_req_set.add((rdesc, rtype))
                        relinked_reqs += 1

                # Re-link or prune opportunities pointing to d_id
                cur.execute("SELECT id, user_id FROM opportunities WHERE job_id = ?", (d_id,))
                d_opps = cur.fetchall()
                for d_opp_id, uid in d_opps:
                    # Does user already have an opportunity for canon_id?
                    cur.execute("SELECT id FROM opportunities WHERE user_id = ? AND job_id = ?", (uid, canon_id))
                    existing_canon_opp = cur.fetchone()

                    if existing_canon_opp:
                        canon_opp_id = existing_canon_opp[0]
                        # Merge evidence
                        cur.execute("SELECT source_url FROM evidence WHERE opportunity_id = ?", (canon_opp_id,))
                        canon_ev_urls = set(r[0] for r in cur.fetchall())

                        cur.execute("SELECT id, source_url FROM evidence WHERE opportunity_id = ?", (d_opp_id,))
                        for evid, eurl in cur.fetchall():
                            if eurl in canon_ev_urls:
                                cur.execute("DELETE FROM evidence WHERE id = ?", (evid,))
                                pruned_ev += 1
                            else:
                                cur.execute("UPDATE evidence SET opportunity_id = ?, job_id = ? WHERE id = ?", (canon_opp_id, canon_id, evid))
                                canon_ev_urls.add(eurl)

                        # Delete duplicate opportunity
                        cur.execute("DELETE FROM opportunities WHERE id = ?", (d_opp_id,))
                        pruned_opps += 1
                    else:
                        # Re-point opportunity to canonical job
                        cur.execute("UPDATE opportunities SET job_id = ? WHERE id = ?", (canon_id, d_opp_id))
                        cur.execute("UPDATE evidence SET job_id = ? WHERE opportunity_id = ?", (canon_id, d_opp_id))

                # Delete duplicate job
                cur.execute("DELETE FROM jobs WHERE id = ?", (d_id,))
                pruned_jobs += 1

        # Also normalize primary_url for singleton jobs
        for curl, jlist in canonical_groups.items():
            if len(jlist) == 1:
                cur.execute("UPDATE jobs SET primary_url = ? WHERE id = ?", (curl, jlist[0][0]))

        cur.execute("PRAGMA integrity_check")
        ic_post = cur.fetchone()[0]
        if ic_post != "ok":
            raise RuntimeError(f"Post-cleanup integrity check failed: {ic_post}")

        if commit:
            con.commit()
            print("Cleanup transaction committed successfully.")
        else:
            con.rollback()
            print("DRY RUN completed. Transaction rolled back without modifying database.")

    except Exception as e:
        con.rollback()
        print(f"Error encountered during cleanup, rolled back: {e}")
        con.close()
        raise e

    cur.execute("SELECT count(*) FROM jobs")
    job_count_after = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM opportunities")
    opp_count_after = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM evidence")
    ev_count_after = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM job_requirements")
    req_count_after = cur.fetchone()[0]

    print(f"\nSummary of Actions:")
    print(f"  Pruned Duplicate Jobs: {pruned_jobs}")
    print(f"  Pruned Duplicate Opportunities: {pruned_opps}")
    print(f"  Pruned Redundant Evidence: {pruned_ev}")
    print(f"  Pruned Redundant Job Requirements: {pruned_reqs}")
    print(f"  Relinked Job Requirements: {relinked_reqs}")
    print(f"\nFinal DB Counts:")
    print(f"  Jobs: {job_count_after} (was {job_count_before})")
    print(f"  Opportunities: {opp_count_after} (was {opp_count_before})")
    print(f"  Evidence: {ev_count_after} (was {ev_count_before})")
    print(f"  Job Requirements: {req_count_after} (was {req_count_before})")

    con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deduplicate OutReachIQ Jobs and Opportunities")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Perform dry run without committing changes")
    group.add_argument("--commit", action="store_true", help="Commit changes to database")
    parser.add_argument("--db-path", default="backend/outreachiq.db", help="Path to SQLite database")

    args = parser.parse_args()
    run_cleanup(db_path=args.db_path, commit=args.commit)
