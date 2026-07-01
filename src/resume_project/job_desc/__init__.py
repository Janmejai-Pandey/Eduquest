"""
__init__.py
Auto-discovers and loads ALL *_data.py files in this folder.
No manual imports needed — just drop a new file and it's picked up.
"""

import os
import importlib.util

# ── Auto-discover all *_data.py files in this folder ─────────────────────────
_current_dir = os.path.dirname(os.path.abspath(__file__))
BRANCH_PROFILES = {}

# Map from filename (without _data.py) → display branch name
BRANCH_NAME_MAP = {
    "cse":       "CSE",
    "it":        "IT",
    "mnc":       "MNC",
    "ai":        "AI",
    "ml":        "ML",
    "robotics":  "Robotics",
    "ece":       "ECE",
    "engineer":  "Engineering (legacy)",  # backward compat
}

for _fname in sorted(os.listdir(_current_dir)):
    if not _fname.endswith("_data.py"):
        continue

    _branch_key = _fname.replace("_data.py", "").lower()
    _display_name = BRANCH_NAME_MAP.get(_branch_key, _branch_key.upper())

    _full_path = os.path.join(_current_dir, _fname)
    _spec = importlib.util.spec_from_file_location(f"_jd_{_branch_key}", _full_path)
    _mod  = importlib.util.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_mod)
        _profiles = getattr(_mod, "job_skill_profiles", None)
        if _profiles and isinstance(_profiles, dict):
            BRANCH_PROFILES[_display_name] = _profiles
    except Exception as e:
        print(f"[job_desc] ⚠  Failed to load {_fname}: {e}")


# ── Flat combined dict of all roles across all branches ──────────────────────
combined_job_profiles = {}
for _branch, _profiles in BRANCH_PROFILES.items():
    for _role, _details in _profiles.items():
        # Prefer newer branches over legacy 'Engineering' if role duplicates
        if _role not in combined_job_profiles or _branch != "Engineering (legacy)":
            combined_job_profiles[_role] = _details


# ── Public helper functions ──────────────────────────────────────────────────
def get_roles_by_branch(branch: str) -> list:
    return list(BRANCH_PROFILES.get(branch, {}).keys())


def get_all_branches() -> list:
    return list(BRANCH_PROFILES.keys())


# ── Debug info on import (comment out later if noisy) ────────────────────────
if __name__ != "__main__":
    _total_roles = sum(len(p) for p in BRANCH_PROFILES.values())
    print(f"[job_desc] ✅ Loaded {len(BRANCH_PROFILES)} branches, {_total_roles} total roles")