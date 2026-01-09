import os
import json
from typing import List, Literal, Dict, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()

# --- STEP 1: Define the Schema ---

class ClaimJudgment(BaseModel):
    """
    Represents the final verdict on a claim based on evidence (Issues).
    """
    claim_text: str = Field(..., description="The original claim being judged.")
    category: str = Field(..., description="The technical category of the claim.")
    verdict: Literal["supported", "contradicted", "unproven"] = Field(
        ..., description="The final decision on whether the evidence supports the claim."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., 
        description="The certainty of the verdict. 'high' (>0.8 certainty), 'medium' (0.5-0.8), 'low' (<0.5)."
    )
    reasoning: str = Field(..., description="Technical explanation for the verdict.")
    evidence_refs: List[str] = Field(..., description="List of issue IDs or titles that serve as evidence.")
    penalty_score: int = Field(..., ge=0, le=100, description="The calculated penalty score (0-100).")

# --- STEP 2: Hard Rules (Deterministic Python Logic) ---

def calculate_base_penalty(issues: List[Dict]) -> int:
    """
    Applies deterministic rules to calculate a baseline penalty score.
    AI cannot override these rules.
    """
    penalty = 0
    
    for issue in issues:
        # Rule 1: "Zombie Bug"
        # If an issue is open > 60 days and is a bug/critical, it indicates tech debt.
        days_open = issue.get("days_open", 0)
        labels = [l.lower() for l in issue.get("labels", [])]
        is_high_priority = any(l in ["bug", "critical", "p0", "p1"] for l in labels)
        
        if days_open > 60 and is_high_priority:
            print(f"[*] Rule Triggered: Zombie Bug (+30) - Issue {issue.get('id')}")
            penalty += 30
            
        # Rule 2: "Silent Failure"
        # Certain keywords indicate high-risk failures that might not be immediately obvious.
        title = issue.get("title", "").lower()
        keywords = ["hangs", "deadlock", "silent", "freeze", "infinite loop"]
        if any(kw in title for kw in keywords):
            print(f"[*] Rule Triggered: Silent Failure (+20) - Issue {issue.get('id')}")
            penalty += 20
            
    # Cap penalty at 60 for the base layer (leaving room for semantic penalty)
    return min(penalty, 60)

# --- STEP 3: The Judgment Agent (LLM Integration) ---

class JudgmentAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def judge_claim(self, claim: Dict, issues: List[Dict], use_case: str) -> ClaimJudgment:
        """
        Combines base penalty with LLM's semantic reasoning to produce a final judgment.
        """
        # Calculate Python-based penalty first
        base_penalty = calculate_base_penalty(issues)
        
        system_prompt = (
            "You are a Senior Systems Architect performing a technical feasibility check. "
            "You are provided with a 'Claim' about a software library and a list of 'Open Issues'. "
            "Your goal is to determine if the issues semantically contradict or invalidate the claim, "
            "specifically considering the user's 'Use Case'.\n\n"
            "Verdict Definitions:\n"
            "- 'supported': No issues found that undermine the claim.\n"
            "- 'contradicted': Issues clearly show the claim is false or unreliable in practice.\n"
            "- 'unproven': Some issues exist but don't directly negate the claim, or evidence is weak.\n\n"
            "Confidence Mapping:\n"
            "- 'high': Direct, clear evidence or total lack of issues.\n"
            "- 'medium': Indirect evidence or mixed signals.\n"
            "- 'low': Speculative connection or very noisy data."
        )

        # Prepare evidence context for the LLM
        evidence_str = "\n".join([
            f"- [Issue #{i.get('id')}]: {i.get('title')}. Content: {i.get('body')[:200]}..." 
            for i in issues
        ])

        user_prompt = (
            f"Use Case: {use_case}\n"
            f"Claim: {claim.get('claim_text')}\n"
            f"Category: {claim.get('category')}\n\n"
            f"Open Issues:\n{evidence_str}"
        )

        print(f"[*] Calling LLM ({self.model}) for semantic verdict...")
        
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=ClaimJudgment, # We reuse the schema for structured output
            )
            
            judgment = response.choices[0].message.parsed
            
            # --- STEP 4: Aggregation Logic ---
            # We override the penalty_score provided by the LLM (or integrate it)
            # Strategy: Total = Base (Python) + Semantic (AI)
            # Semantic Penalty: +40 if contradicted, +10 if unproven, 0 if supported.
            semantic_bonus = 0
            if judgment.verdict == "contradicted":
                semantic_bonus = 40
            elif judgment.verdict == "unproven":
                semantic_bonus = 10
                
            final_penalty = min(base_penalty + semantic_bonus, 100)
            
            # Final update to the judgment object
            judgment.penalty_score = final_penalty
            judgment.claim_text = claim.get("claim_text") # Ensure consistency
            judgment.category = claim.get("category")
            
            return judgment
            
        except Exception as e:
            print(f"[!] Error during judgment: {e}")
            raise e

if __name__ == "__main__":
    # Test Data
    test_claim = {
        "claim_text": "Supports 1000+ concurrent users with low latency.",
        "category": "Concurrency & Scale"
    }
    
    test_issues = [
        {
            "id": "1",
            "title": "AsyncRetriever hangs indefinitely under load",
            "labels": ["bug"],
            "days_open": 63,
            "body": "System freezes when users > 50"
        }
    ]
    
    test_use_case = "Medical Chatbot"
    
    agent = JudgmentAgent()
    
    print("--- Testing Judgment Agent (The Judge) ---")
    try:
        result = agent.judge_claim(test_claim, test_issues, test_use_case)
        
        print("\n--- Final Claim Judgment (JSON) ---")
        print(result.model_dump_json(indent=2))
        
        print(f"\n[+] Final Penalty Score: {result.penalty_score}/100")
        print(f"[+] Verdict: {result.verdict.upper()}")
        
    except Exception as e:
        print(f"[!] Test Failed: {e}")
