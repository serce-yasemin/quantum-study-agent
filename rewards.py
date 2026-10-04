"""
Points, levels, badges and the daily streak - plain code, no model calls.

Points are earned in the app (lesson finished, warm-up right, correct
answers). This module turns them into something to aim for:

- a level name that grows with the points, and a badge for every level reached
- a daily streak: days in a row with at least one earned point
- a streak bonus every 7 days in a row (7 days +10, 14 days +20, ...)

Everything lives in the learner profile, so it follows the learner.
"""

from datetime import date, timedelta

# (points needed, level name, badge)
LEVELS = [
    (0, "Curious", "🌱"),
    (15, "Qubit Rookie", "🔹"),
    (40, "Superposer", "🌗"),
    (80, "Phase Finder", "🧭"),
    (140, "Gate Runner", "🚪"),
    (220, "Entangler", "🔗"),
    (320, "Quantum Navigator", "🚀"),
]
STREAK_STEP = 7            # a bonus every 7 days in a row ...
STREAK_BONUS_PER_STEP = 10  # ... worth 10 points per completed week


def level(points: int) -> dict:
    """The level these points reach, and how far the next one is."""
    index = max(i for i, (need, _, _) in enumerate(LEVELS) if points >= need)
    need, name, badge = LEVELS[index]
    nxt = LEVELS[index + 1] if index + 1 < len(LEVELS) else None
    return {"index": index, "name": name, "badge": badge, "from": need,
            "next_name": nxt[1] if nxt else None,
            "next_at": nxt[0] if nxt else None,
            "progress": ((points - need) / (nxt[0] - need)) if nxt else 1.0}


def streak(profile: dict, today: date) -> int:
    """Days in a row with activity, counting back from today (or from
    yesterday, so the streak is not shown as lost before the day is over)."""
    days = set(profile.get("days", []))
    day = today if today.isoformat() in days else today - timedelta(days=1)
    count = 0
    while day.isoformat() in days:
        count += 1
        day -= timedelta(days=1)
    return count


def streak_bonus(days_in_a_row: int) -> int:
    """7 days -> 10, 14 days -> 20, 21 days -> 30 ... otherwise 0."""
    if days_in_a_row and days_in_a_row % STREAK_STEP == 0:
        return STREAK_BONUS_PER_STEP * (days_in_a_row // STREAK_STEP)
    return 0


def add_points(profile: dict, points: int, today: date) -> list[str]:
    """Add earned points, mark today as an active day, and hand out whatever
    that unlocks. Returns short messages for the learner (may be empty)."""
    messages = []
    before = level(profile.get("points", 0))["index"]
    profile["points"] = profile.get("points", 0) + points

    days = profile.setdefault("days", [])
    if today.isoformat() not in days:           # first points of the day
        days.append(today.isoformat())
        run = streak(profile, today)
        bonus = streak_bonus(run)
        if bonus:
            profile["points"] += bonus
            profile.setdefault("streak_bonuses", []).append(
                {"date": today.isoformat(), "days": run, "points": bonus})
            messages.append(f"🔥 {run} days in a row! Streak bonus +{bonus} points")
        elif run > 1:
            messages.append(f"🔥 {run} days in a row")

    after = level(profile["points"])
    if after["index"] > before:
        messages.append(f"{after['badge']} New level: {after['name']}!")
    return messages


def badges(profile: dict) -> list[dict]:
    """Every level badge, marked earned or not, plus the streak badges."""
    reached = level(profile.get("points", 0))["index"]
    out = [{"badge": badge, "name": name, "earned": i <= reached,
            "how": f"{need} points"} for i, (need, name, badge) in enumerate(LEVELS)]
    for bonus in profile.get("streak_bonuses", []):
        out.append({"badge": "🔥", "name": f"{bonus['days']}-day streak",
                    "earned": True, "how": bonus["date"]})
    return out
