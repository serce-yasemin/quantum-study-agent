"""
Learner accounts and a learner profile that survives between visits.

Each learner signs in with e-mail + password (Supabase Auth) and their whole
profile is stored as one JSON row in the `learner_profiles` table. A database
rule (row level security) lets every learner read and write ONLY their own
row, so the same account works from any device.

If Supabase is not configured (e.g. running locally without secrets), the
web app falls back to the in-browser profile with download/upload.
"""

import json
import os
from datetime import datetime, timezone

TABLE = "learner_profiles"


def configured() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))


def new_client():
    from supabase import create_client  # imported lazily: optional dependency
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def sign_up(client, email: str, password: str):
    """Create an account. Returns the user, or raises with a readable message."""
    res = client.auth.sign_up({"email": email, "password": password})
    if res.user is None:
        raise RuntimeError("Sign-up failed.")
    if res.session is None:
        raise RuntimeError("Account created - please confirm the e-mail we sent you, "
                           "then sign in.")
    return res.user


def sign_in(client, email: str, password: str):
    res = client.auth.sign_in_with_password({"email": email, "password": password})
    return res.user


def load_profile(client, user_id: str) -> dict | None:
    rows = (client.table(TABLE).select("profile").eq("user_id", user_id)
            .execute().data)
    return rows[0]["profile"] if rows else None


def save_profile(client, user_id: str, profile: dict) -> None:
    client.table(TABLE).upsert({
        "user_id": user_id,
        "profile": profile,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()


def fingerprint(profile: dict) -> str:
    """Cheap change detector: we only write when the profile really changed."""
    return json.dumps(profile, sort_keys=True, ensure_ascii=False)
