from __future__ import annotations

from typing import Any

from backend.database import get_profile_dict


async def calculate_bio_age(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Calculate biological age with 4 sub-system breakdown."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import calculate_bio_age as calc

    return calc(profile or {})


async def project_risk(user_id: str, db: Any, years: int = 15, **kwargs: Any) -> dict:
    """Project disease risks over N years based on the current profile."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import project_risk as proj

    return {"projections": proj(profile or {}, years)}


async def simulate_habit_change(user_id: str, db: Any, changes: dict | None = None, **kwargs: Any) -> dict:
    """Simulate the effect of a habit change on bio age and risk projections."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import simulate_habit_change as sim

    return sim(profile or {}, changes or {})


async def mental_wellness_score(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Calculate mental wellness score."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import mental_wellness_score as mws

    return mws(profile or {})


async def nutrition_targets(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Get blood-work-aware daily nutrition targets."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import nutrition_targets as nt

    return nt(profile or {})


async def score_meal(user_id: str, db: Any, meal: dict | None = None, **kwargs: Any) -> dict:
    """Score a meal against blood-work-aware nutrition targets."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import score_meal as sm

    return sm(profile or {}, meal or {})


async def workout_targets(user_id: str, db: Any, **kwargs: Any) -> dict:
    """Get profile-aware workout recommendations."""

    _ = kwargs
    profile = await get_profile_dict(user_id, db)
    from backend.formulas import workout_targets as wt

    return wt(profile or {})
