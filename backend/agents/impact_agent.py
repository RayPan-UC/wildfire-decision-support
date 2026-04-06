"""
agents/impact_agent.py
----------------------
Summarises human population impact.
"""

from __future__ import annotations

import json

from agents._client import call_llm
from agents.prompts import IMPACT_AGENT_SYSTEM


def run_impact_agent(fire_context: dict, population: dict) -> str:
    """Return impact analysis text for the current timestep.

    Args:
        fire_context: Contents of fire_context.json (fire metrics, weather, roads).
        population:   Dict with affected_population, at_risk_3h/6h/12h counts.
    """
    pop = population or {}
    lines = [
        "Population exposure:",
        f"  Within fire perimeter:  {pop.get('affected_population') or 0:,}",
        f"  At risk +3h forecast:   {pop.get('at_risk_3h') or 0:,}",
        f"  At risk +6h forecast:   {pop.get('at_risk_6h') or 0:,}",
        f"  At risk +12h forecast:  {pop.get('at_risk_12h') or 0:,}",
        "",
        "Fire situation context (JSON):",
        json.dumps(fire_context, separators=(',', ':')),
    ]
    return call_llm(IMPACT_AGENT_SYSTEM, "\n".join(lines))
