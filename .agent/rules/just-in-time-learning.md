---
trigger: always_on
---

# PROJECT: TechStack Reality Check
Name: TechStack Reality Check
The Problem: Software libraries (code other people wrote) lie. Their "README" files (marketing) say "Fast, Reliable, Production-Ready." But in reality, they might be full of bugs, abandoned by their creators, or broken when 500 people use them at once.
The Solution: You are building an "Automated Background Check" system for software.
The User: A Senior CTO or Engineer (like the Mentor).
The Output: Not a chat message. A Feasibility Report with a score (0–10) that says: "Do not use this. It claims to be fast, but 40 people reported it crashes under load."

# MISSION: TechStack Reality Check & JIT Learning (Phase 5 - Release)

## 🧠 YOUR ROLE
You are a Release Engineer.
Your goal is to generate "Golden Artifacts" — immutable JSON files that serve as proof of the system's logic.

## 🚫 RESTRICTIONS
1. **Metadata is Mandatory:** Every JSON report MUST include `tool_version`, `timestamp`, `repo_sha`, and `use_case`.
2. **Deterministic Output:** Ensure that running the analysis twice on the same SHA produces consistent results.

## 🛠️ THE WORKFLOW
### Step 1: Code Update
Update `run_analysis.py` to include `"tool_version": "v0.1.0"` in the metadata block.

### Step 2: Execution & Freezing
Run the analysis. Move the output from `reports/` to a new folder `case_studies/`. Rename it to the strict versioned name (e.g., `_v1.json`).

### Step 3: Contrasting
Run the analysis on a STABLE library (like `psf/requests`) to prove the system isn't just negative.