"""
agents/summary_agent.py
-----------------------
Synthesises three specialist reports into a structured executive briefing.
"""

from __future__ import annotations

import json
import re

from agents._client import call_llm
from agents.prompts import SUMMARY_AGENT_SYSTEM


def run_summary_agent(
    risk_analysis: str,
    impact_analysis: str,
    evacuation_analysis: str,
) -> dict:
    """Return structured dict: {risk_level, key_points, briefing}."""
    user_msg = (
        "RISK ANALYSIS:\n"
        f"{risk_analysis}\n\n"
        "IMPACT ANALYSIS:\n"
        f"{impact_analysis}\n\n"
        "EVACUATION ANALYSIS:\n"
        f"{evacuation_analysis}"
    )
    text = call_llm(SUMMARY_AGENT_SYSTEM, user_msg)

    # Extract JSON from the response (handles accidental markdown fences)
    try:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return {
                "risk_level":  str(data.get("risk_level", "Unknown")),
                "key_points":  list(data.get("key_points", [])),
                "briefing":    str(data.get("briefing", text)),
            }
    except Exception:
        pass

    # Fallback: return plain text as briefing
    return {"risk_level": "Unknown", "key_points": [], "briefing": text}
