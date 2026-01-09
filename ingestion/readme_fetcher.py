import os
import requests
import base64
import re
from typing import Dict
from dotenv import load_dotenv

# Load environment variables (GITHUB_TOKEN)
load_dotenv()

def normalize_key(text: str) -> str:
    """
    Converts a Markdown header string into a clean dictionary key.
    Example: '## 🚀 Quick Start' -> 'quick_start'
    """
    # Remove Markdown hash marks and leading/trailing whitespace
    text = re.sub(r'^#+\s*', '', text).strip()
    # Remove emojis and special characters (non-alphanumeric/non-space)
    text = re.sub(r'[^\w\s-]', '', text)
    # Convert to lowercase, replace spaces/hyphens with underscores
    text = text.lower().replace(' ', '_').replace('-', '_')
    # Collapse multiple underscores
    text = re.sub(r'_+', '_', text)
    return text.strip('_')

def fetch_readme(repo: str) -> Dict:
    """
    Fetches the README for a repo, decodes it, and splits it into sections.
    
    Args:
        repo: Repository in 'owner/repo' format.
        
    Returns:
        Dict containing commit_sha, content, and sections.
    """
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    url = f"https://api.github.com/repos/{repo}/readme"
    
    print(f"[*] Fetching README for {repo}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch README. Status code: {response.status_code}")
        
    data = response.json()
    sha = data.get("sha")
    encoded_content = data.get("content", "")
    
    # Decoding Base64
    # GitHub folds long Base64 strings with newlines; b64decode handles this.
    try:
        decoded_bytes = base64.b64decode(encoded_content)
        content = decoded_bytes.decode("utf-8")
    except Exception as e:
        print(f"[!] ERROR: Failed to decode README content.")
        raise e

    # Section Splitting using Regex
    # Pattern: Line starts with 1-6 '#' followed by a space and header text.
    # re.MULTILINE ensures ^ matches the start of every line in the block.
    header_pattern = r'(^#{1,6}\s+.*$)'
    parts = re.split(header_pattern, content, flags=re.MULTILINE)
    
    sections = {}
    
    # The first part is always the "Introduction" (text before the first header)
    if parts:
        intro_text = parts[0].strip()
        if intro_text:
            sections["introduction"] = intro_text
            
    # Following parts alternate: [Header, Content, Header, Content...]
    # We iterate in steps of 2 starting from index 1.
    for i in range(1, len(parts), 2):
        header = parts[i]
        # The content for this header is the next element in the list
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        
        key = normalize_key(header)
        if key:
            sections[key] = body
            
    return {
        "commit_sha": sha,
        "content": content,
        "sections": sections
    }

if __name__ == "__main__":
    REPO_NAME = "langchain-ai/langchain"
    print(f"--- Testing README Fetcher with {REPO_NAME} ---")
    
    try:
        result = fetch_readme(REPO_NAME)
        
        print(f"\n[+] Successfully fetched README.")
        print(f"[+] Commit SHA: {result['commit_sha']}")
        
        # Display the detected keys
        keys = list(result['sections'].keys())
        print(f"[+] Detected {len(keys)} sections:")
        for k in keys:
            print(f"    - {k}")
            
        # Verify a specific section exists (common in LangChain)
        if "quick_start" in result['sections']:
            print("\n--- Quick Start Preview ---")
            # Print first 100 characters of Quick Start
            preview = result['sections']['quick_start'][:100]
            print(f"{preview}...")
            
    except Exception as e:
        print(f"[!] Test Failed: {e}")
