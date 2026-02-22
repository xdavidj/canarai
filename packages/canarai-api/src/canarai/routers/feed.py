"""Feed endpoints - intelligence feed and trend data placeholders."""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/v1/feed", tags=["feed"])


@router.get("/agents")
async def get_agent_feed() -> dict:
    """Hosted intelligence feed of known AI agent behaviors.

    Returns curated data about known agent families, their capabilities,
    and observed prompt injection susceptibility.
    """
    return {
        "version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agents": [
            {
                "family": "openai",
                "variants": ["GPTBot", "ChatGPT-User", "OAI-SearchBot"],
                "category": "llm_crawler",
                "known_behaviors": {
                    "respects_robots_txt": True,
                    "executes_javascript": False,
                    "follows_meta_directives": True,
                },
                "risk_level": "high",
            },
            {
                "family": "anthropic",
                "variants": ["ClaudeBot", "Claude-Web"],
                "category": "llm_crawler",
                "known_behaviors": {
                    "respects_robots_txt": True,
                    "executes_javascript": False,
                    "follows_meta_directives": True,
                },
                "risk_level": "medium",
            },
            {
                "family": "google",
                "variants": ["Google-Extended", "Googlebot"],
                "category": "search_crawler",
                "known_behaviors": {
                    "respects_robots_txt": True,
                    "executes_javascript": True,
                    "follows_meta_directives": True,
                },
                "risk_level": "medium",
            },
            {
                "family": "perplexity",
                "variants": ["PerplexityBot"],
                "category": "ai_search",
                "known_behaviors": {
                    "respects_robots_txt": False,
                    "executes_javascript": False,
                    "follows_meta_directives": False,
                },
                "risk_level": "high",
            },
        ],
    }


@router.get("/trends")
async def get_trends() -> dict:
    """Trend data for AI agent activity across all monitored sites.

    Returns aggregated, anonymized trend data.
    """
    return {
        "version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": "last_30_days",
        "trends": {
            "total_agent_visits": 0,
            "unique_agent_families": 0,
            "average_resilience_score": 0.0,
            "critical_failure_rate": 0.0,
            "most_common_agent": None,
            "most_vulnerable_test": None,
        },
        "note": "Trend data will be populated as monitoring data accumulates.",
    }
