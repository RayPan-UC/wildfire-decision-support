"""
agents/risk_agent.py
--------------------
Analyses fire behaviour data and produces a risk analysis report.
"""

from __future__ import annotations

import json

from agents._client import call_llm
from agents.prompts import RISK_AGENT_SYSTEM


def run_risk_agent(fire_context: dict) -> str:
    """Return risk analysis text for the current timestep.

    Args:
        fire_context: Contents of fire_context.json — includes fire metrics,
            weather_t1, fwi_t1, and wind_forecast.
    """
    user_msg = (
        "Fire situation context (JSON):\n"
        f"{json.dumps(fire_context, separators=(',', ':'))}"
    )
    return call_llm(RISK_AGENT_SYSTEM, user_msg)
