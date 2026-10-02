"""
Quantum Study Agent - web app (Streamlit)
Nebius x NVIDIA Global AI Hackathon 2026 - Personal AI track

Run locally:   streamlit run streamlit_app.py

Three tabs:
- Explore: an exact, interactive picture of one-qubit states (Bloch sphere +
  density-matrix heat map). No AI involved - every number is computed.
- Study: the AI tutor loop (lesson -> questions -> grading -> review pages),
  backed by NVIDIA Nemotron on Nebius Token Factory. A learning path starts
  from the basics (state vectors) and unlocks each step after the one before.
- My progress: the learner profile - download it, upload it next time.

The learner profile lives in this browser session and can be downloaded as
JSON - your learning data stays under your control.
"""

import json
import os
from datetime import date

import numpy as np
import streamlit as st

st.set_page_config(page_title="Quantum Study Agent", page_icon="⚛️", layout="wide")

# Secrets from Streamlit Cloud -> environment, before the LLM client is created.
try:
    for key in ("NEBIUS_API_KEY", "TAVILY_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"):
        if key in st.secrets and not os.environ.get(key):
            os.environ[key] = st.secrets[key]
    ACCESS_CODE = st.secrets.get("ACCESS_CODE")
except Exception:            # no secrets file when running locally
    ACCESS_CODE = None

import curriculum  # noqa: E402  (after env setup)
import homework  # noqa: E402
import profile_store  # noqa: E402
import store  # noqa: E402
import quantum_viz as qv  # noqa: E402
import tutor  # noqa: E402

MAX_WRONG_PER_LEVEL = 2   # after this many misses at a level: back to the lesson
NEED = profile_store.CORRECT_IN_A_ROW_TO_PASS


# ---------------------------------------------------------------- access gate
def access_gate() -> None:
    """Protect the shared API credits on the public demo."""
    if not ACCESS_CODE or st.session_state.get("unlocked"):
        return
    st.title("⚛️ Quantum Study Agent")
    code = st.text_input("Access code", type="password",
                         help="The code is in the hackathon submission text.")
    if code:
        if code == ACCESS_CODE:
            st.session_state.unlocked = True
            st.rerun()
        st.error("Wrong code.")
    st.stop()


access_gate()

ss = st.session_state
EMPTY_PROFILE = {"learner": {"goal": "", "interests": []}, "concepts": {}, "assignments": []}


# ---------------------------------------------------------------- accounts
def finish_login(client, user) -> None:
    """Load (or create) the learner's profile and open the app."""
    profile = store.load_profile(client, user.id)
    if profile is None:
        profile = json.loads(json.dumps(EMPTY_PROFILE))
        store.save_profile(client, user.id, profile)
    ss.db, ss.user_id, ss.user_email = client, user.id, user.email
    ss.profile, ss.saved = profile, store.fingerprint(profile)
    ss.stage = "start"


def read_email_link() -> None:
    """E-mail links open the app as ?token_hash=...&type=recovery|email.
    Check the token once, then remove it from the address bar."""
    params = st.query_params
    token, link_type = params.get("token_hash"), params.get("type")
    if not token or link_type not in ("recovery", "email", "signup"):
        return
    st.query_params.clear()          # a token works only once - never re-use it
    try:
        client = store.new_client()
        user = store.verify_link(client, token, link_type)
    except Exception as exc:
        ss.link_error = f"{exc} Please request a new link."
        return
    if link_type == "recovery":      # signed in, but must choose a new password first
        ss.reset_client, ss.reset_user = client, user
    else:                            # e-mail confirmed: sign straight in
        finish_login(client, user)


def new_password_form() -> None:
    st.title("⚛️ Quantum Study Agent")
    st.subheader("Choose a new password")
    with st.form("new_password"):
        first = st.text_input("New password", type="password",
                              help="At least 6 characters.")
        again = st.text_input("Repeat new password", type="password")
        if st.form_submit_button("Save new password", type="primary"):
            if len(first) < 6:
                st.error("The password needs at least 6 characters.")
            elif first != again:
                st.error("The two passwords are not the same.")
            else:
                try:
                    user = store.set_password(ss.reset_client, ss.reset_user.email, first)
                    finish_login(ss.reset_client, user)
                except Exception as exc:
                    st.error(str(exc))
                    st.stop()
                del ss.reset_client, ss.reset_user
                st.rerun()
    st.stop()


def account_gate() -> None:
    """Sign in so the learner profile follows the learner to any device."""
    if not store.configured() or ss.get("user_id"):
        return
    read_email_link()
    if ss.get("user_id"):
        return
    if ss.get("reset_user"):
        new_password_form()
    st.title("⚛️ Quantum Study Agent")
    st.write("Sign in to keep your progress - it is saved to your account, so you "
             "can continue on any device.")
    if ss.get("link_error"):
        st.error(ss.pop("link_error"))
    sign_in_tab, sign_up_tab, forgot_tab = st.tabs(
        ["Sign in", "Create account", "Forgot password?"])
    for tab, new in ((sign_in_tab, False), (sign_up_tab, True)):
        with tab, st.form(f"auth_{new}"):
            email = st.text_input("E-mail")
            password = st.text_input("Password", type="password",
                                     help="At least 6 characters." if new else None)
            if st.form_submit_button("Create account" if new else "Sign in",
                                     type="primary"):
                try:
                    client = store.new_client()
                    user = (store.sign_up if new else store.sign_in)(
                        client, email.strip(), password)
                    finish_login(client, user)
                except Exception as exc:
                    st.error(str(exc))
                    st.stop()
                st.rerun()
    with forgot_tab, st.form("forgot"):
        st.write("We will e-mail you a link to choose a new password.")
        email = st.text_input("E-mail", key="forgot_email")
        if st.form_submit_button("Send reset link", type="primary"):
            try:
                store.send_password_reset(store.new_client(), email.strip())
            except Exception as exc:
                st.error(str(exc))
                st.stop()
            # Same message whether or not the address has an account,
            # so the form cannot be used to find out who is signed up.
            st.success("If an account exists for this address, a reset link is "
                       "on its way.")
    st.stop()


def autosave() -> None:
    """Write the profile to the learner's account whenever it has changed."""
    if not ss.get("user_id"):
        return
    now = store.fingerprint(ss.profile)
    if now != ss.get("saved"):
        try:
            store.save_profile(ss.db, ss.user_id, ss.profile)
            ss.saved = now
        except Exception as exc:
            st.warning(f"Could not save your progress just now ({exc}). "
                       "It will be retried on your next click.")


account_gate()

# Match the figures to the viewer's light/dark theme.
try:
    qv.set_theme(st.context.theme.type == "dark")
except Exception:
    qv.set_theme(False)
ss.setdefault("profile", json.loads(json.dumps(EMPTY_PROFILE)))
ss.setdefault("stage", "start")
autosave()   # catches changes from a run that ended early with st.rerun()


# ---------------------------------------------------------------- header
st.title("⚛️ Quantum Study Agent")
st.caption("A personal, stateful study agent for quantum computing · "
           "NVIDIA Nemotron on Nebius Token Factory")
if ss.get("user_id"):
    left, right = st.columns([4, 1])
    left.caption(f"Signed in as {ss.user_email} · progress is saved automatically"
                 f" · ⭐ {ss.profile.get('points', 0)} points")
    if right.button("Sign out"):
        autosave()
        store.sign_out(ss.db)
        for key in list(ss.keys()):
            if key != "unlocked":
                del ss[key]
        st.rerun()

tab_explore, tab_study, tab_profile = st.tabs(["🔭 Explore", "📘 Study", "🗂️ My progress"])


# ================================================================ EXPLORE
def state_picker(label: str, key: str, default: str):
    names = list(qv.NAMED_STATES) + ["custom"]
    choice = st.selectbox(label, names, index=names.index(default), key=f"{key}_sel")
    if choice == "custom":
        theta = st.slider("θ (tilt from |0⟩, degrees)", 0, 180, 60, key=f"{key}_th")
        phi = st.slider("φ (relative phase, degrees)", 0, 359, 0, key=f"{key}_ph")
    else:
        theta, phi = qv.NAMED_STATES[choice]
    name = choice if choice != "custom" else f"θ={theta}°, φ={phi}°"
    return qv.density_from_state(qv.pure_state(theta, phi)), name


def show_numbers(rho: np.ndarray) -> None:
    r = qv.bloch_vector(rho)
    c = st.columns(5)
    c[0].metric("P(0) = ρ₀₀", f"{rho[0, 0].real:.3f}")
    c[1].metric("P(1) = ρ₁₁", f"{rho[1, 1].real:.3f}")
    c[2].metric("coherence |ρ₀₁|", f"{abs(rho[0, 1]):.3f}")
    phase = "—" if abs(rho[0, 1]) < 1e-9 else f"{np.degrees(-np.angle(rho[0, 1])) % 360:.1f}°"
    c[3].metric("relative phase φ", phase)
    c[4].metric("purity Tr(ρ²)", f"{qv.purity(rho):.3f}",
                help=f"Bloch vector length |r| = {np.linalg.norm(r):.3f}")


with tab_explore:
    mode = st.radio("What do you want to see?",
                    ["One pure state", "Mix two states"], horizontal=True)

    if mode == "One pure state":
        left, right = st.columns([1, 2])
        with left:
            rho, name = state_picker("State", "pure", "|+⟩")
            st.info("A **pure** state always sits **on the surface** of the sphere "
                    "(length 1, purity 1). Change φ and watch only the off-diagonal "
                    "entries rotate - the probabilities on the diagonal stay put.")
        with right:
            st.plotly_chart(qv.bloch_figure([{"rho": rho, "label": name,
                                             "color": qv.COLOR_A}]),
                            width="stretch")
        show_numbers(rho)
        st.plotly_chart(qv.matrix_figure(rho, f"ρ = |ψ⟩⟨ψ| for {name}"),
                        width="stretch")

    else:
        left, right = st.columns([1, 2])
        with left:
            rho_a, name_a = state_picker("State A", "a", "|0⟩")
            rho_b, name_b = state_picker("State B", "b", "|+⟩")
            p = st.slider("p = probability of A", 0.0, 1.0, 0.6, 0.05)
            rho = qv.mix(p, rho_a, rho_b)
            st.info(f"ρ = {p:.2f}·ρ(A) + {1 - p:.2f}·ρ(B). The mixture is the "
                    "**straight line between A and B** - so it lands **inside** "
                    "the sphere: shorter vector, smaller coherence, purity < 1.")
        with right:
            st.plotly_chart(qv.bloch_figure([
                {"rho": rho_a, "label": f"A {name_a}", "color": qv.COLOR_A},
                {"rho": rho_b, "label": f"B {name_b}", "color": qv.COLOR_B},
                {"rho": rho, "label": "mixture", "color": qv.COLOR_MIX},
            ], chord=True), width="stretch")
        show_numbers(rho)
        c1, c2, c3 = st.columns(3)
        c1.plotly_chart(qv.matrix_figure(rho_a, f"A: {name_a}", show_scale=False),
                        width="stretch")
        c2.plotly_chart(qv.matrix_figure(rho_b, f"B: {name_b}", show_scale=False),
                        width="stretch")
        c3.plotly_chart(qv.matrix_figure(rho, f"Mixture (p = {p:.2f})"),
                        width="stretch")


# ================================================================ STUDY
def concept_record():
    return profile_store.get_concept(ss.profile, ss.concept)


OWN = "✍️ My own material"
ICONS = {"locked": "🔒", "new": "⬜", "learning": "📘",
         "review_due": "🔁", "mastered": "✅"}
LABELS = {"locked": "locked", "new": "not started", "learning": "in progress",
          "review_due": "review due", "mastered": "mastered"}


def path_overview() -> None:
    """The learning path as a row of cards: basics first, each unlocks the next."""
    cols = st.columns(len(curriculum.PATH))
    for i, (col, step) in enumerate(zip(cols, curriculum.PATH)):
        state = curriculum.status(ss.profile, step["id"])
        rec = ss.profile["concepts"].get(step["id"])
        level = rec["level"] if rec else 0
        with col.container(border=True):
            st.markdown(f"**{i + 1}. {step['title']}**")
            st.caption(f"{ICONS[state]} {LABELS[state]} · level {level}/3")


def concept_title(concept: str) -> str:
    return curriculum.BY_ID[concept]["title"] if concept in curriculum.BY_ID else concept


def show_assignment(a: dict) -> None:
    """One homework card: what to do, the book section, the checked links."""
    with st.container(border=True):
        st.markdown(f"**{concept_title(a['concept'])}** · given {a['created']}"
                    + (f" · gap: *{a['weak_point']}*" if a.get("weak_point") else ""))
        st.write(a["task"])
        if a.get("book"):
            b = a["book"]
            st.markdown(f"📖 **{b['section']}**, pp. {b['pages']}  \n{b['book']}")
        for link in a.get("links", []):
            st.markdown(f"🔗 [{link['title']}]({link['url']}) "
                        f"· ✓ link checked {link['checked_on']}")
        if not a.get("links") and a.get("web_search", "ok") != "ok":
            st.caption(f"Web resources: {a['web_search']}.")
        st.caption("When you have done it, the agent will ask you two short "
                   "check questions about it.")


def call(fn, *args):
    """Run an LLM step with a spinner; show a friendly error instead of a trace."""
    try:
        with st.spinner("Nemotron is thinking…"):
            return fn(*args)
    except Exception as exc:
        st.error(f"The model call failed: {exc}")
        st.stop()


def begin_session(concept: str, material: str, keep_gaps: bool = False) -> None:
    """Start a session on one concept. It runs until the learner stops it."""
    ss.concept, ss.material = concept, material
    ss.homework = None
    if not keep_gaps:
        ss.session_weak = None
    c = concept_record()
    if concept in curriculum.BY_ID:
        c["prerequisites"] = curriculum.BY_ID[concept]["prerequisites"]
    ss.was_mastered = c["level"] >= profile_store.MAX_LEVEL
    ss.level = profile_store.MAX_LEVEL if c["status"] == "mastered" else c["level"] + 1
    ss.asked = []
    start_level()


def start_level() -> None:
    material = ss.material
    ss.objective = call(tutor.learning_objective, material, ss.concept, ss.level)
    ss.cards = call(tutor.lesson_cards, material, ss.concept, ss.level, ss.objective)
    # If the model's cards do not have the right shape, teach the old way:
    # one plain lesson text. The learner always gets a lesson.
    ss.lesson = (None if ss.cards else
                 call(tutor.micro_lesson, material, ss.concept, ss.level, ss.objective))
    ss.card, ss.simpler, ss.try_pick = 0, {}, None
    ss.wrong_this_level = 0
    ss.stage = "lesson"


def add_points(n: int, why: str) -> None:
    """Points: +1 lesson finished, +1 warm-up right, +1/+2/+3 for a correct
    answer at level 1/2/3. Saved in the learner profile."""
    ss.profile["points"] = ss.profile.get("points", 0) + n
    st.toast(f"⭐ +{n} · {why}")


CARD_NAMES = ["You already know", "The new idea", "Worked example", "Your turn"]


def lesson_figure(concept: str) -> None:
    """A small interactive picture for the concept, drawn by our own code
    (exact numbers - nothing here comes from the model)."""
    if concept == "state_vector":
        st.caption("Move the sliders: θ changes the probabilities, φ only turns "
                   "the arrow around the vertical axis.")
        theta = st.slider("θ (tilt from |0⟩, degrees)", 0, 180, 60, key="lf_th")
        phi = st.slider("φ (relative phase, degrees)", 0, 359, 0, key="lf_ph")
        rho = qv.density_from_state(qv.pure_state(theta, phi))
        a, b = np.cos(np.radians(theta) / 2), np.sin(np.radians(theta) / 2)
        st.code(f"|ψ⟩ = {a:.3f}|0⟩ + {b:.3f}·e^(i·{phi}°)|1⟩\n"
                f"P(0) = {a * a:.3f}    P(1) = {b * b:.3f}    sum = 1", language=None)
        st.plotly_chart(qv.bloch_figure([{"rho": rho, "label": "|ψ⟩",
                                         "color": qv.COLOR_A}]), width="stretch")
    elif concept in ("outer_product", "density_matrix"):
        st.caption("Pick a state: the matrix is |ψ⟩⟨ψ|. Diagonal = probabilities, "
                   "off-diagonal = coherence (it carries the phase).")
        names = list(qv.NAMED_STATES)
        name = st.selectbox("State", names, index=names.index("|+⟩"), key="lf_state")
        rho = qv.density_from_state(qv.pure_state(*qv.NAMED_STATES[name]))
        st.plotly_chart(qv.matrix_figure(rho, f"ρ = |ψ⟩⟨ψ| for {name}"), width="stretch")
        st.plotly_chart(qv.bloch_figure([{"rho": rho, "label": name,
                                         "color": qv.COLOR_A}]), width="stretch")
    elif concept == "mixed_state":
        st.caption("Slide p: the mixture moves along the straight line between "
                   "A and B, inside the sphere - purity drops below 1.")
        p = st.slider("p = probability of |0⟩ (the rest is |+⟩)", 0.0, 1.0, 0.5, 0.05,
                      key="lf_p")
        rho_a = qv.density_from_state(qv.pure_state(*qv.NAMED_STATES["|0⟩"]))
        rho_b = qv.density_from_state(qv.pure_state(*qv.NAMED_STATES["|+⟩"]))
        rho = qv.mix(p, rho_a, rho_b)
        st.metric("purity Tr(ρ²)", f"{qv.purity(rho):.3f}")
        st.plotly_chart(qv.bloch_figure([
            {"rho": rho_a, "label": "A |0⟩", "color": qv.COLOR_A},
            {"rho": rho_b, "label": "B |+⟩", "color": qv.COLOR_B},
            {"rho": rho, "label": "mixture", "color": qv.COLOR_MIX}], chord=True),
            width="stretch")


def simple_picture(concept: str, key: str) -> None:
    """A plain picture of the idea, drawn by our own code - shown when the
    learner says "I didn't get it". No model output in here."""
    if concept == "state_vector":
        theta = st.slider("Turn the arrow", 0, 180, 60, key=f"sp_{key}")
        st.plotly_chart(qv.arrow_figure(theta), width="stretch", key=f"spa_{key}")
        st.plotly_chart(qv.chance_bar(float(np.cos(np.radians(theta) / 2) ** 2)),
                        width="stretch", key=f"spb_{key}")
        st.caption("The arrow always has length 1. Its two shadows are a and b. "
                   "Square each shadow → the two chances. They always fill the bar.")
    elif concept in ("outer_product", "density_matrix"):
        theta = st.slider("Change the state", 0, 180, 90, key=f"sp_{key}")
        st.plotly_chart(qv.product_table_figure(theta), width="stretch",
                        key=f"spa_{key}")
        st.caption("A multiplication table: every entry of the column times every "
                   "entry of the row. The diagonal (a·a, b·b) holds the two chances.")
    elif concept == "mixed_state":
        p = st.slider("Share of |0⟩ in the mix", 0.0, 1.0, 0.5, 0.05, key=f"sp_{key}")
        rho_a = qv.density_from_state(qv.pure_state(*qv.NAMED_STATES["|0⟩"]))
        rho_b = qv.density_from_state(qv.pure_state(*qv.NAMED_STATES["|+⟩"]))
        st.plotly_chart(qv.bloch_figure([
            {"rho": rho_a, "label": "A |0⟩", "color": qv.COLOR_A},
            {"rho": rho_b, "label": "B |+⟩", "color": qv.COLOR_B},
            {"rho": qv.mix(p, rho_a, rho_b), "label": "mixture",
             "color": qv.COLOR_MIX}], chord=True), width="stretch", key=f"spa_{key}")
        st.caption("A mixture sits on the straight line between A and B - inside "
                   "the ball, not on its surface.")


def explain_again(text: str) -> None:
    """'I didn't get it' - show a real picture and say the card more simply."""
    i = ss.card
    if ss.simpler.get(i):
        with st.container(border=True):
            if ss.concept in curriculum.BY_ID and i != 1:   # card 2 has its figure
                simple_picture(ss.concept, f"{ss.level}_{i}")
            st.write(ss.simpler[i])
    elif st.button("🤔 I didn't get it - show me", key=f"simpler_{i}"):
        with st.spinner("Finding a simpler way…"):
            ss.simpler[i] = call(tutor.explain_differently, concept_title(ss.concept),
                                 ss.objective, text)
        st.rerun()


def lesson_cards_view() -> None:
    """The lesson as four small cards, one at a time."""
    cards, i = ss.cards, ss.card
    st.progress((i + 1) / 4, text=f"Card {i + 1} of 4 · {CARD_NAMES[i]}")
    if i == 0:
        st.markdown(f"#### 🧩 {CARD_NAMES[0]}")
        st.write(cards["bridge"])
        explain_again(cards["bridge"])
    elif i == 1:
        st.markdown(f"#### 💡 {CARD_NAMES[1]}")
        has_figure = ss.concept in curriculum.BY_ID
        left, right = st.columns([1, 1]) if has_figure else (st.container(), None)
        with left:
            st.code(cards["idea"], language=None, wrap_lines=True)
            explain_again(cards["idea"])
        if has_figure:
            with right:
                lesson_figure(ss.concept)
    elif i == 2:
        st.markdown(f"#### ✏️ {CARD_NAMES[2]}")
        for n, step in enumerate(cards["example"], 1):
            st.code(f"{n}. {step['step']}", language=None, wrap_lines=True)
            st.caption(f"↳ why: {step['why']}")
        explain_again("\n".join(f"{x['step']} ({x['why']})" for x in cards["example"]))
    else:
        t = cards["try_it"]
        st.markdown(f"#### 🎯 {CARD_NAMES[3]}")
        st.caption("A warm-up. It does not count for your level - just try.")
        if ss.try_pick is None:
            pick = st.radio(t["question"], t["options"], index=None, key=f"try_{ss.level}")
            if st.button("Check", type="primary", disabled=pick is None):
                ss.try_pick = t["options"].index(pick)
                if ss.try_pick == t["correct"]:
                    add_points(1, "warm-up right")
                st.rerun()
        else:
            st.markdown(f"**{t['question']}**")
            for n, option in enumerate(t["options"]):
                mark = ("✅" if n == t["correct"] else
                        "❌" if n == ss.try_pick else "▫️")
                st.write(f"{mark} {option}")
            if ss.try_pick == t["correct"]:
                st.success(f"Right! {t['explanation']}")
            else:
                st.warning(f"Not this time - and that is fine here. {t['explanation']}")

    back, forward = st.columns(2)
    if i > 0 and back.button("← Back", width="stretch"):
        ss.card -= 1
        st.rerun()
    if i < 3:
        if forward.button("Continue →", type="primary", width="stretch"):
            ss.card += 1
            st.rerun()
    elif ss.try_pick is not None:
        if forward.button("Start the questions →", type="primary", width="stretch"):
            add_points(1, "lesson finished")
            next_question()
            st.rerun()


def next_question() -> None:
    c = concept_record()
    weak = [h["weak_point"] for h in c["history"] if h["weak_point"]]
    weak += [g for a in ss.profile.get("assignments", []) if a["concept"] == ss.concept
             for chk in a.get("checks", []) for g in chk["gaps"] if g]
    ss.question = call(tutor.generate_question, ss.material, ss.concept, ss.level,
                       weak, ss.asked, ss.objective)
    ss.asked.append(ss.question["question"])
    ss.show_hint = False
    ss.stage = "question"


def welcome_back() -> None:
    """Session start: what is waiting for the learner before new material -
    homework to check and spaced-repetition reviews that are due."""
    due = [s["id"] for s in curriculum.PATH
           if curriculum.status(ss.profile, s["id"]) == "review_due"]
    todo = homework.open_assignments(ss.profile)
    if not due and not todo:
        return
    st.subheader("👋 Welcome back")
    for concept in due:
        st.info(f"🔁 **Review due:** {concept_title(concept)} - it is recommended "
                "below, so a quick round keeps it fresh.")
    for a in todo:
        with st.container(border=True):
            st.markdown(f"📚 **Homework #{a['id']}** · {concept_title(a['concept'])} "
                        f"· given {a['created']}")
            st.caption(a["task"])
            if a.get("checks"):
                st.caption(f"Checked {len(a['checks'])}x so far - not passed yet.")
            if a["check_questions"]:
                if st.button("I did it - check me", key=f"check_{a['id']}"):
                    ss.checking, ss.check_results, ss.check_extra = a["id"], None, None
                    ss.stage = "check"
                    st.rerun()
            elif st.button("Mark as done", key=f"done_{a['id']}"):
                a["status"], a["done_on"] = "done", str(date.today())
                st.rerun()
    st.divider()


def check_homework() -> None:
    """Two short questions that someone who did the homework can answer.

    2/2 right -> done. One wrong -> one extra question on that gap.
    Extra wrong, or both wrong -> a short review page on what is missing.
    """
    a = next(x for x in ss.profile["assignments"] if x["id"] == ss.checking)
    st.subheader(f"Homework check · #{a['id']} {concept_title(a['concept'])}")
    check = ss.get("check_results")
    if check is None:
        st.write("Answer in a line or two - no need to be formal.")
        answers = [st.text_area(q["question"], key=f"hw_{a['id']}_{i}", height=100)
                   for i, q in enumerate(a["check_questions"])]
        if st.button("Check my answers", type="primary",
                     disabled=not all(x.strip() for x in answers)):
            with st.spinner("Checking your answers…"):
                ss.check_results = call(homework.check, a, answers)
            ss.check_extra = None
            st.rerun()
        if st.button("Back"):
            ss.stage = "start"
            st.rerun()
        return

    def show(r: dict) -> None:
        st.markdown(f"**{r['question']}**  \nYour answer: {r['answer']}")
        if r["correct"]:
            st.success(f"✅ {r['feedback']}")
        else:
            st.error(f"Not yet - {r['feedback']}")
            with st.expander("Expected answer"):
                st.write(r["expected_answer"])

    def review_pages(pages: list[str]) -> None:
        st.markdown("#### 📖 What is missing")
        st.write("Read this, then have another look at the homework resources. "
                 "The gap will also come up in your next questions.")
        for page in pages:
            st.code(page, language=None, wrap_lines=True)

    for r in check["results"]:
        show(r)
    extra, extra_done = check["extra"], ss.get("check_extra")

    if a["status"] == "done" and not extra:
        st.balloons()
        st.success("Homework done! 🎉")
    elif check["reviews"]:                       # both wrong: teach, no extra question
        st.warning("Both answers need work, so here is a short review instead of "
                   "another question. The homework stays open - retry it later.")
        review_pages(check["reviews"])
    elif extra and extra_done is None:           # one wrong: one more question
        st.info("One miss. One more question on that idea - get it right and the "
                "homework counts as done.")
        answer = st.text_area(extra["question"], key=f"hw_{a['id']}_extra", height=100)
        if st.button("Check this answer", type="primary", disabled=not answer.strip()):
            with st.spinner("Checking…"):
                ss.check_extra = call(homework.check_extra, a, extra, answer.strip())
            st.rerun()
        return
    elif extra:
        st.divider()
        show(extra_done["result"])
        if a["status"] == "done":
            st.balloons()
            st.success("That was just a slip - homework done! 🎉")
        else:
            st.warning("This idea is not solid yet. The homework stays open - "
                       "retry it later.")
            review_pages([extra_done["review"]])
    if st.button("Back to start", type="primary"):
        ss.stage, ss.check_results, ss.check_extra = "start", None, None
        st.rerun()


with tab_study:
    if ss.stage == "start":
        welcome_back()
        st.subheader("Start a session")
        st.write("One idea at a time: a short lesson, then questions that climb "
                 "**recall → apply → transfer**. Pass a level with "
                 f"**{NEED} correct answers in a row**. Study as long as you like - "
                 "press *Finish for today* whenever you want to stop.")
        st.markdown("#### Your learning path")
        path_overview()
        rec_id, reason = curriculum.recommend(ss.profile)
        st.info(f"**Recommended now:** {curriculum.BY_ID[rec_id]['title']} - {reason}.")

        skip = st.toggle("Let me pick any step (skip ahead)",
                         help="Locked steps open when the step before them is "
                              "mastered. Turn this on if you already know the basics.")
        options = [s["id"] for s in curriculum.PATH
                   if skip or curriculum.is_unlocked(ss.profile, s["id"])] + [OWN]
        choice = st.selectbox(
            "What do you want to study?", options, index=options.index(rec_id),
            format_func=lambda c: c if c == OWN else curriculum.BY_ID[c]["title"])
        if choice == OWN:
            concept = st.text_input("Concept name", "my_topic")
            material = st.text_area("Paste a paragraph from a paper or lecture notes",
                                    height=180).strip()
        else:
            concept, material = choice, curriculum.material(choice)

        if st.button("Start session", type="primary"):
            if len(material) < 200:
                st.warning("Please paste at least 200 characters of material "
                           "(no API call was made).")
                st.stop()
            begin_session(concept, material)
            st.rerun()

    elif ss.stage == "check":
        check_homework()

    else:
        c = concept_record()
        st.progress(min(c["level"] * NEED + c["streak"], 3 * NEED) / (3 * NEED),
                    text=f"Question {len(ss.asked)} · Level {ss.level}/3 "
                         f"({tutor.DIFFICULTY_NAMES.get(ss.level, '')}) · "
                         f"streak {c['streak']}/{NEED}")

        if ss.stage == "lesson":
            st.subheader(f"Lesson · {tutor.DIFFICULTY_NAMES[ss.level]}")
            st.success(f"**Goal:** {ss.objective}")
            if ss.cards:
                lesson_cards_view()
            else:
                st.code(ss.lesson, language=None, wrap_lines=True)
                st.caption("Tip: open the 🔭 Explore tab to see any matrix from this "
                           "lesson on the Bloch sphere.")
                if st.button("I'm ready - ask me", type="primary"):
                    next_question()
                    st.rerun()

        elif ss.stage == "question":
            st.subheader("Question")
            st.markdown(ss.question["question"])
            if st.button("💡 Hint"):
                ss.show_hint = True
            if ss.show_hint:
                st.info(ss.question.get("hint") or "Look back at the lesson example.")
            answer = st.text_area("Your answer (plain text is fine, e.g. [[0.5, 0.5], [0.5, 0.5]])",
                                  height=140, key=f"ans_{len(ss.asked)}")
            if st.button("Submit answer", type="primary", disabled=not answer.strip()):
                result = call(tutor.grade_answer, ss.question, answer)
                passed = profile_store.record_attempt(c, ss.level, result["correct"],
                                                      result.get("weak_point"))
                ss.result, ss.passed, ss.last_answer = result, passed, answer
                ss.review = None
                if result["correct"]:
                    add_points(ss.level, f"correct at level {ss.level}")
                if not result["correct"]:
                    ss.wrong_this_level += 1
                    ss.session_weak = result.get("weak_point") or ss.session_weak
                    ss.review = call(tutor.review_page, ss.material, ss.concept,
                                     result.get("weak_point") or "", ss.question, answer)
                ss.stage = "feedback"
                st.rerun()
            if st.button("Finish for today", key="stop_in_question"):
                ss.asked.pop()                       # this one was not answered
                ss.stage = "done"
                ss.end_reason = (f"{len(ss.asked)} questions today. "
                                 f"Next review: {c['next_review'] or 'not set yet'}.")
                st.rerun()

        elif ss.stage == "feedback":
            st.subheader("Question")
            st.markdown(ss.question["question"])
            st.markdown(f"**Your answer:** {ss.last_answer}")
            if ss.result["correct"]:
                st.success(f"✅ Correct - {ss.result['feedback']}")
            else:
                st.error(f"Not yet - {ss.result['feedback']}")
                with st.expander("Model answer"):
                    st.code(ss.question["expected_answer"], language=None, wrap_lines=True)
                st.subheader("Review page")
                st.code(ss.review, language=None, wrap_lines=True)

            if ss.passed:
                st.balloons()
                st.success(f"Level {ss.level} passed ({NEED} correct in a row)!")

            if not ss.result["correct"] and ss.wrong_this_level >= MAX_WRONG_PER_LEVEL:
                st.info(f"{MAX_WRONG_PER_LEVEL} misses at this level - let's look at "
                        "the lesson once more, then try fresh questions.")
                label, action = "Back to the lesson →", "relearn"
            elif ss.passed and ss.level >= profile_store.MAX_LEVEL:
                label, action = "Finish - concept mastered!", "mastered"
            elif ss.passed:
                label, action = "Next level →", "level"
            else:
                label, action = "Next question →", "question"

            go, stop = st.columns([2, 1])
            if action != "mastered" and stop.button("Finish for today", width="stretch"):
                ss.stage = "done"
                ss.end_reason = (f"{len(ss.asked)} questions today. "
                                 f"Next review: {c['next_review'] or 'not set yet'}.")
                st.rerun()
            if go.button(label, type="primary", width="stretch"):
                if action == "relearn":
                    start_level()
                elif action == "mastered":
                    ss.stage = "done"
                    title = curriculum.BY_ID.get(ss.concept, {}).get("title", ss.concept)
                    ss.end_reason = f"'{title}' mastered! Next review: {c['next_review']}."
                    opened = ([] if ss.was_mastered else
                              curriculum.newly_unlocked(ss.profile, ss.concept))
                    if opened:
                        ss.end_reason += " 🔓 Unlocked: " + ", ".join(
                            curriculum.BY_ID[o]["title"] for o in opened) + "."
                elif action == "level":
                    ss.level += 1
                    start_level()
                else:
                    next_question()
                st.rerun()

        elif ss.stage == "done":
            st.subheader("Session finished")
            st.info(ss.end_reason)
            if ss.get("homework") is None:
                # The learner chooses: another short round now, or stop and get
                # homework. Homework is made only once they stop, so continuing
                # does not pile up assignments (or API calls).
                just_mastered = (not ss.was_mastered and
                                 concept_record()["level"] >= profile_store.MAX_LEVEL)
                if just_mastered and ss.concept in curriculum.BY_ID:
                    nxt, _ = curriculum.recommend(ss.profile)
                else:
                    nxt = ss.concept
                st.caption("Stop here and get homework, or carry on.")
                col1, col2 = st.columns(2)
                if col1.button(f"Keep going with {concept_title(nxt)}", width="stretch"):
                    material = (curriculum.material(nxt) if nxt in curriculum.BY_ID
                                else ss.material)
                    begin_session(nxt, material, keep_gaps=True)
                    st.rerun()
                if col2.button("Done for today - give me homework", type="primary",
                               width="stretch"):
                    try:
                        with st.spinner("Preparing your homework (checking every link)…"):
                            ss.homework = homework.create(ss.profile, ss.concept,
                                                          concept_title(ss.concept),
                                                          ss.material, ss.session_weak)
                        st.rerun()
                    except Exception as exc:
                        ss.homework = {}
                        st.warning(f"Could not prepare homework this time: {exc}")
            if ss.homework:
                st.subheader("📚 Your homework")
                show_assignment(ss.homework)
            if ss.get("homework") is not None:
                st.write("Your progress is in the 🗂️ **My progress** tab - download "
                         "it to keep it.")
                if st.button("Start a new session"):
                    ss.stage = "start"
                    st.rerun()


# ================================================================ PROFILE
with tab_profile:
    st.subheader("Your learner profile")
    st.metric("⭐ Points", ss.profile.get("points", 0),
              help="+1 for finishing a lesson, +1 for a right warm-up, "
                   "+1 / +2 / +3 for a correct answer at level 1 / 2 / 3.")
    where = ("It is saved to your account after every step, so you can continue "
             "on any device." if ss.get("user_id") else
             "It lives only in this browser session; download it to keep it, "
             "upload it next time to continue.")
    st.write("This is everything the agent remembers about you. The model itself "
             "forgets everything between calls - this profile **is** its memory. "
             + where)
    concepts = ss.profile["concepts"]
    order = [s["id"] for s in curriculum.PATH]
    if concepts:
        for name, rec in sorted(concepts.items(),
                                key=lambda kv: order.index(kv[0]) if kv[0] in order
                                else len(order)):
            total = len(rec["history"])
            right = sum(h["correct"] for h in rec["history"])
            cols = st.columns(4)
            title = curriculum.BY_ID[name]["title"] if name in curriculum.BY_ID else name
            cols[0].metric("Concept", title)
            cols[1].metric("Level passed", f"{rec['level']}/3")
            cols[2].metric("Answers correct", f"{right}/{total}")
            cols[3].metric("Next review", rec["next_review"] or "—")
            weak = [h["weak_point"] for h in rec["history"] if h["weak_point"]]
            if weak:
                st.caption("Gaps found so far: " + "; ".join(dict.fromkeys(weak)))
    else:
        st.caption("No sessions yet.")

    tasks = ss.profile.get("assignments", [])
    if tasks:
        st.subheader("Homework")
        for a in reversed(tasks):
            with st.expander(f"#{a['id']} · {concept_title(a['concept'])} · "
                             f"{a['created']} · {a['status']}"):
                show_assignment(a)

    st.download_button("Download my profile (JSON)",
                       json.dumps(ss.profile, indent=2, ensure_ascii=False),
                       file_name="learner_profile.json", mime="application/json")
    uploaded = st.file_uploader("Continue from a saved profile", type="json")
    if uploaded is not None and st.button("Load this profile"):
        ss.profile = json.load(uploaded)
        st.success("Profile loaded.")


autosave()
