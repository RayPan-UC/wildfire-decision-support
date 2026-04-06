"""
agents/summary_agent.py
-----------------------
Synthesises three specialist reports into an executive briefing.
"""

from __future__ import annotations

from agents._client import call_llm
from agents.prompts import SUMMARY_AGENT_SYSTEM


def run_summary_agent(
    risk_analysis: str,
    impact_analysis: str,
    evacuation_analysis: str,
) -> str:
    """Return consolidated executive summary for the current timestep."""
    user_msg = (
        "RISK ANALYSIS:\n"
        f"{risk_analysis}\n\n"
        "IMPACT ANALYSIS:\n"
        f"{impact_analysis}\n\n"
        "EVACUATION ANALYSIS:\n"
        f"{evacuation_analysis}"
    )
    return call_llm(SUMMARY_AGENT_SYSTEM, user_msg)
