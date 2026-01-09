import os
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
# This allows us to access GITHUB_TOKEN for authenticated requests
load_dotenv()

def fetch_open_bug_issues(repo: str, max_issues: int = 50) -> List[Dict]:
    """
    Fetches open issues from a GitHub repository, filtering out Pull Requests.
    
    Args:
        repo: The repository in 'owner/repo' format (e.g., 'langchain-ai/langchain').
        max_issues: The maximum number of issues to retrieve (default 50).
        
    Returns:
        A list of normalized issue dictionaries.
    """
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        # Using a token increases rate limits from 60 to 5000 requests per hour
        headers["Authorization"] = f"token {token}"
    
    base_url = f"https://api.github.com/repos/{repo}/issues"
    all_normalized_issues = []
    page = 1
    per_page = 50 # GitHub max is 100, but 50 is safer for stability and matching our requirements
    
    now = datetime.now()
    
    print(f"[*] Starting ingestion for {repo}...")
    
    while len(all_normalized_issues) < max_issues:
        # Construct parameters for the GET request
        # We only want 'open' issues. GitHub sorts by 'created' descending by default.
        params = {
            "state": "open",
            "per_page": per_page,
            "page": page
        }
        
        response = requests.get(base_url, headers=headers, params=params)
        
        # Rate Limit Check
        # Robust systems MUST check headers to avoid being blocked
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            print("[!] WARNING: GitHub API Rate Limit reached. Stopping fetch.")
            break
            
        if response.status_code != 200:
            print(f"[!] ERROR: Failed to fetch page {page}. Status: {response.status_code}")
            break
            
        issues_data = response.json()
        
        # If no issues are returned, we've reached the end of the available data
        if not issues_data:
            break
            
        for raw_issue in issues_data:
            # PR Filtering: GitHub treats Issues and PRs similarly in this endpoint.
            # PRs have a 'pull_request' key; real Issues do not.
            if "pull_request" in raw_issue:
                continue
                
            # Normalization: Map noisy API response to our clean schema
            # created_at is converted to datetime for 'days_open' math
            created_at_dt = datetime.strptime(raw_issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            updated_at_dt = datetime.strptime(raw_issue["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
            
            normalized = {
                "id": raw_issue["id"],
                "number": raw_issue["number"],
                "title": raw_issue["title"],
                "state": raw_issue["state"],
                "created_at": raw_issue["created_at"],
                "updated_at": raw_issue["updated_at"],
                "days_open": (now - created_at_dt).days,
                "comment_count": raw_issue["comments"],
                "labels": [label["name"] for label in raw_issue.get("labels", [])],
                "author_association": raw_issue["author_association"],
                "body": raw_issue.get("body", "")
            }
            
            all_normalized_issues.append(normalized)
            
            # Stop if we hit the limit mid-page
            if len(all_normalized_issues) >= max_issues:
                break
        
        print(f"[*] Page {page}: Found {len(all_normalized_issues)} issues so far...")
        page += 1
        
    return all_normalized_issues[:max_issues]

if __name__ == "__main__":
    # Test case: Fetch small sample from LangChain
    REPO_NAME = "langchain-ai/langchain"
    print(f"--- Testing Issues Fetcher with {REPO_NAME} ---")
    
    results = fetch_open_bug_issues(REPO_NAME, max_issues=5)
    
    if results:
        print(f"\n[+] Successfully fetched {len(results)} issues.")
        print("\n--- Sample Normalized Issue ---")
        import json
        # Pretty print the first sample to verify the schema
        print(json.dumps(results[0], indent=2))
    else:
        print("[!] No issues found or fetch failed.")
