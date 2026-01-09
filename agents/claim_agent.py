import os
import json
from typing import List, Literal, Dict
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()

# --- STEP 1: Define the Schema ---
# We use Pydantic to enforce structure on the LLM's output.
# Literal types constrain the model to specific technical domains.

class ExtractedClaim(BaseModel):
    """
    Represents a single verifiable claim extracted from technical documentation.
    """
    claim_text: str = Field(..., description="A concise summary of the claim being made.")
    category: Literal[
        "Performance", 
        "Concurrency & Scale", 
        "Reliability", 
        "Abstraction", 
        "Security"
    ] = Field(..., description="The technical domain the claim belongs to.")
    confidence_tone: Literal["assertive", "suggestive", "aspirational"] = Field(
        ..., 
        description=(
            "The strength of the claim's language. "
            "'assertive': Strong language (guarantees, must, always). "
            "'suggestive': Capabilities (supports, allows, can). "
            "'aspirational': Future or weak goals (aims to, experimental, roadmap)."
        )
    )
    implied_commitments: List[str] = Field(
        ..., description="A list of technical expectations this claim creates for a developer."
    )
    source_section: str = Field(..., description="The name of the section where this claim was found.")
    quote: str = Field(
        ..., description="The EXACT, VERBATIM string from the original text that supports this claim."
    )

class ClaimList(BaseModel):
    """Container for multiple claims."""
    claims: List[ExtractedClaim]

# --- STEP 2: The Logic Flow ---

class ClaimExtractionAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def extract_claims(self, text: str, section_name: str) -> List[ExtractedClaim]:
        """
        Calls the LLM to extract claims and performs verbatim quote verification.
        """
        system_prompt = (
            "You are a Senior Technical Auditor (The Lawyer). Your job is to extract specific, "
            "verifiable claims from software documentation. "
            "Follow these rules strictly:\n"
            "1. Only extract claims that are technical promises.\n"
            "2. Every claim MUST have a 'quote' which is a substring present VERBATIM in the text.\n"
            "3. Do not paraphrase the quote.\n"
            "4. If no claims are found, return an empty list."
        )

        user_prompt = f"Extract claims from the following '{section_name}' section:\n\n{text}"

        print(f"[*] Calling LLM ({self.model}) for claim extraction...")
        
        # We use beta.chat.completions.parse for seamless Pydantic integration
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=ClaimList,
            )
            
            extracted_data = response.choices[0].message.parsed
        except Exception as e:
            print(f"[!] API or Parsing Error: {e}")
            return []

        # --- STEP 3: Hallucination Verification ---
        verified_claims = []
        for claim in extracted_data.claims:
            # Substring matching to ensure the LLM didn't "hallucinate" or paraphrase the evidence
            if claim.quote in text:
                verified_claims.append(claim)
            else:
                print(f"[!] HALLUCINATION DETECTED: Discarding claim. Quote not found verbatim: '{claim.quote}'")
                
        return verified_claims

if __name__ == "__main__":
    # Ensure OPENAI_API_KEY is set in .env before running this
    if not os.getenv("OPENAI_API_KEY"):
        print("[!] Warning: OPENAI_API_KEY not found in .env. Test will fail.")
    
    # Sample data as requested
    sample_text = "LangChain is designed for production-ready applications. It supports 1000+ concurrent users with low latency."
    section_name = "Introduction"
    
    agent = ClaimExtractionAgent()
    
    print("--- Testing Claim Extraction Agent (The Lawyer) ---")
    results = agent.extract_claims(sample_text, section_name)
    
    if results:
        print(f"\n[+] Successfully extracted {len(results)} verified claims.")
        # Print valid JSON output
        output_data = [claim.model_dump() for claim in results]
        print(json.dumps(output_data, indent=2))
    else:
        print("[!] No verified claims extracted.")
