"""
agents/evacuation_agent.py
--------------------------
Analyses road network status and recommends evacuation priorities.
"""

from __future__ import annotations

import json

from agents._client import call_llm
from agents.prompts import EVACUATION_AGENT_SYSTEM


def run_evacuation_agent(fire_context: dict) -> str:
    """Return evacuation analysis text for the current timestep.

    Args:
        fire_context: Contents of fire_context.json — includes road_summary
            (list of major roads with worst_status, cut_at, cut_location)
            plus wind_forecast for the next 12 hours.
    """
    user_msg = (
        "Fire situation context (JSON):\n"
        f"{json.dumps(fire_context, separators=(',', ':'))}"
    )
    return call_llm(EVACUATION_AGENT_SYSTEM, user_msg)
