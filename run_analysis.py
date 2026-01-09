import argparse
import json
import os
import sys
from datetime import datetime

# Import project modules
from ingestion.readme_fetcher import fetch_readme
from ingestion.issues_fetcher import fetch_open_bug_issues
from agents.claim_agent import ClaimExtractionAgent
from agents.judgment_agent import JudgmentAgent

def run_pipeline(repo: str, use_case: str, max_issues: int):
    """
    Orchestrates the full reality check pipeline.
    """
    print(f"\n{'='*60}")
    print(f"🚀 Starting Reality Check for: {repo}")
    print(f"📋 Context: {use_case}")
    print(f"{'='*60}\n")

    # --- STEP 1: Ingestion ---
    try:
        print("[*] Phase 1: Ingestion (The Detective)")
        readme_data = fetch_readme(repo)
        issues_list = fetch_open_bug_issues(repo, max_issues=max_issues)
        print(f"[+] Found README (SHA: {readme_data['commit_sha'][:7]}) and {len(issues_list)} issues.\n")
    except Exception as e:
        print(f"[!] INGESTION FAILED: {e}")
        sys.exit(1)

    # --- STEP 2: Claim Extraction ---
    print("[*] Phase 2: Claim Extraction (The Lawyer)")
    lawyer = ClaimExtractionAgent()
    sections = readme_data.get("sections", {})
    
    # Strategy for V1: Analyze Introduction and domain-specific sections
    # We also include the 'first' section if 'introduction' is missing.
    target_sections = ["introduction"]
    available_keys = list(sections.keys())
    
    if available_keys and "introduction" not in available_keys:
        target_sections.append(available_keys[0])

    for key in available_keys:
        keywords = ["concurrency", "scale", "performance", "features", "capabilities"]
        if any(kw in key for kw in keywords):
            target_sections.append(key)
    
    all_claims = []
    for section_name in set(target_sections): # Use set to avoid duplicates
        if section_name in sections:
            print(f"    - Analyzing section: {section_name}...")
            claims = lawyer.extract_claims(sections[section_name], section_name)
            all_claims.extend(claims)
    
    if not all_claims:
        print("[!] No verified claims extracted from the README. Stopping.")
        sys.exit(0)
    
    print(f"[+] Extracted {len(all_claims)} verified claims.\n")

    # --- STEP 3: Judgment ---
    print("[*] Phase 3: Judgment (The Judge)")
    judge = JudgmentAgent()
    final_judgments = []
    
    for claim in all_claims:
        print(f"    - Judging claim: \"{claim.claim_text[:50]}...\"")
        judgment = judge.judge_claim(claim.model_dump(), issues_list, use_case)
        final_judgments.append(judgment)

    # --- STEP 4: Reporting ---
    print("\n[*] Phase 4: Reporting")
    repo_slug = repo.replace("/", "_")
    report_path = f"reports/{repo_slug}_report.json"
    
    report_data = {
        "metadata": {
            "tool_version": "v0.1.0",
            "repo": repo,
            "use_case": use_case,
            "timestamp": datetime.now().isoformat(),
            "readme_sha": readme_data["commit_sha"],
            "issues_analyzed": len(issues_list)
        },
        "results": [j.model_dump() for j in final_judgments]
    }
    
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
    
    # --- STEP 5: Summary ---
    summary = {
        "supported": 0,
        "contradicted": 0,
        "unproven": 0
    }
    for j in final_judgments:
        summary[j.verdict] += 1
        
    print(f"\n{'-'*40}")
    print(f"✅ ANALYSIS COMPLETE")
    print(f"{'-'*40}")
    print(f"📄 Report Saved: {report_path}")
    print(f"📊 Summary: {len(final_judgments)} Claims Analyzed")
    print(f"    - {summary['supported']} Supported")
    print(f"    - {summary['contradicted']} Contradicted")
    print(f"    - {summary['unproven']} Unproven")
    print(f"{'-'*40}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TechStack Reality Check CLI")
    parser.add_argument("--repo", required=True, help="GitHub repository (owner/repo)")
    parser.add_argument("--use-case", required=True, help="Intended use case context")
    parser.add_argument("--issues", type=int, default=50, help="Max issues to analyze")
    
    args = parser.parse_args()
    
    run_pipeline(args.repo, args.use_case, args.issues)
