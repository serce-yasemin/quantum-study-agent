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
APP_URL = os.environ.get("APP_URL", "https://quantum-study-agent.streamlit.app")


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


def sign_out(client) -> None:
    """End the session on the server too, so this client stops refreshing its
    token in the background. Never blocks signing out in the app."""
    try:
        client.auth.sign_out()
    except Exception:
        pass


def send_password_reset(client, email: str) -> None:
    """E-mail a reset link. The link opens the app with ?token_hash=...&type=recovery
    (set in the Supabase "Reset password" e-mail template), so the app can read it."""
    client.auth.reset_password_for_email(email, {"redirect_to": APP_URL})


def verify_link(client, token_hash: str, link_type: str):
    """Check a token from an e-mail link. On success the client is signed in
    as that user. Returns the user. Each token works only once."""
    res = client.auth.verify_otp({"token_hash": token_hash, "type": link_type})
    if res.user is None:
        raise RuntimeError("This link is invalid or has expired.")
    return res.user


def set_password(client, email: str, new_password: str):
    """Change the password of the user the client is signed in as, then sign
    in again with it and return the user.

    Why sign in again: supabase-py handles the "USER_UPDATED" event that
    update_user fires by putting the public key back into the request headers.
    Database requests made afterwards are then anonymous, so row level
    security hides the learner's own profile (seen live: GET returned no row,
    the insert was refused with 401). A fresh sign-in fires "SIGNED_IN",
    which puts the learner's token back.
    """
    client.auth.update_user({"password": new_password})
    return sign_in(client, email, new_password)


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
