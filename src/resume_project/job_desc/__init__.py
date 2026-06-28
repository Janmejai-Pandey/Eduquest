"""
__init__.py
Auto-loads all branch-wise job profiles and exposes a combined dict.

Usage:
    from resume_project.job_desc import combined_job_profiles
    profile = combined_job_profiles["Software Developer"]
"""

from .cse_data import job_skill_profiles as cse_profiles
from .it_data import job_skill_profiles as it_profiles
from .mnc_data import job_skill_profiles as mnc_profiles
from .ai_data import job_skill_profiles as ai_profiles
from .ml_data import job_skill_profiles as ml_profiles
from .robotics_data import job_skill_profiles as robotics_profiles
from .ece_data import job_skill_profiles as ece_profiles

# Try to load the original engineer_data too (for backward compat)
try:
    from .engineer_data import job_skill_profiles as engineer_profiles
except ImportError:
    engineer_profiles = {}


# Combine all profiles into one dict, tagged by branch
BRANCH_PROFILES = {
    "CSE": cse_profiles,
    "IT": it_profiles,
    "MNC": mnc_profiles,
    "AI": ai_profiles,
    "ML": ml_profiles,
    "Robotics": robotics_profiles,
    "ECE": ece_profiles,
}

# Flat combined dict (all roles in one place)
combined_job_profiles = {}
for branch, profiles in BRANCH_PROFILES.items():
    for role, details in profiles.items():
        combined_job_profiles[role] = details

# Also expose engineer_profiles for backward compat with old ranking.py
if engineer_profiles:
    for role, details in engineer_profiles.items():
        if role not in combined_job_profiles:
            combined_job_profiles[role] = details


def get_roles_by_branch(branch: str) -> list:
    """Get list of role names for a given branch."""
    return list(BRANCH_PROFILES.get(branch, {}).keys())


def get_all_branches() -> list:
    """Get list of all available branches."""
    return list(BRANCH_PROFILES.keys())