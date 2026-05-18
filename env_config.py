"""
Environment configuration.

Single source of truth for all environment URLs.
Selected via --env CLI option or ENV environment variable.

Usage:
    pytest --env uat
    ENV=uat pytest
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class EnvConfig:
    """Holds UI and API base URLs for one environment."""
    ui:  str
    api: str


# ── Environment URL map ────────────────────────────────────────────
# Add new environments here only. Nothing else needs changing.
ENV_MAP: Dict[str, EnvConfig] = {
    "dev": EnvConfig(
        ui  = "https://miox-dev.ikp1001rnp.cloud.uk.hsbc",
        api = "https://miox-backend-dev.ikp1001rnp.cloud.uk.hsbc",
    ),
    "sit": EnvConfig(
        ui  = "https://miox-sit.ikp1001rnp.cloud.uk.hsbc",
        api = "https://miox-backend-sit.ikp1001rnp.cloud.uk.hsbc",
    ),
    "uat": EnvConfig(
        ui  = "https://miox-uat.ikp1001rnp.cloud.uk.hsbc",
        api = "https://miox-backend-uat.ikp1001rnp.cloud.uk.hsbc",
    ),
    "prod": EnvConfig(
        ui  = "https://miox.ikp1001rnp.cloud.uk.hsbc",
        api = "https://miox-backend.ikp1001rnp.cloud.uk.hsbc",
    ),
}


def get_env_config(env: str) -> EnvConfig:
    """Return EnvConfig for the given environment key (case-insensitive)."""
    key = env.lower()
    if key not in ENV_MAP:
        valid = ", ".join(ENV_MAP.keys())
        raise ValueError(
            f"Unknown ENV '{env}'. Valid values: {valid}. "
            f"Pass via --env <value> or set ENV=<value>."
        )
    return ENV_MAP[key]
