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

import numpy as np
import streamlit as st

st.set_page_config(page_title="Quantum Study Agent", page_icon="⚛️", layout="wide")

# Secrets from Streamlit Cloud -> environment, before the LLM client is created.
try:
    for key in ("NEBIUS_API_KEY", "TAVILY_API_KEY"):
        if key in st.secrets and not os.environ.get(key):
            os.environ[key] = st.secrets[key]
    ACCESS_CODE = st.secrets.get("ACCESS_CODE")
except Exception:            # no secrets file when running locally
    ACCESS_CODE = None

import curriculum  # noqa: E402  (after env setup)
import homework  # noqa: E402
import profile_store  # noqa: E402
import quantum_viz as qv  # noqa: E402
import tutor  # noqa: E402

MAX_QUESTIONS = 5
MAX_WRONG_PER_LEVEL = 2
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

# Match the figures to the viewer's light/dark theme.
try:
    qv.set_theme(st.context.theme.type == "dark")
except Exception:
    qv.set_theme(False)
ss.setdefault("profile", {"learner": {"goal": "", "interests": []},
                          "concepts": {}, "assignments": []})
ss.setdefault("stage", "start")


# ---------------------------------------------------------------- header
st.title("⚛️ Quantum Study Agent")
st.caption("A personal, stateful study agent for quantum computing · "
           "NVIDIA Nemotron on Nebius Token Factory")

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
    """Start a session of up to MAX_QUESTIONS on one concept."""
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
    ss.lesson = call(tutor.micro_lesson, material, ss.concept, ss.level, ss.objective)
    ss.wrong_this_level = 0
    ss.stage = "lesson"


def next_question() -> None:
    if len(ss.asked) >= MAX_QUESTIONS:
        ss.stage = "done"
        ss.end_reason = f"That's {MAX_QUESTIONS} questions - enough for today."
        return
    c = concept_record()
    weak = [h["weak_point"] for h in c["history"] if h["weak_point"]]
    ss.question = call(tutor.generate_question, ss.material, ss.concept, ss.level,
                       weak, ss.asked, ss.objective)
    ss.asked.append(ss.question["question"])
    ss.show_hint = False
    ss.stage = "question"


with tab_study:
    if ss.stage == "start":
        st.subheader("Start a short session")
        st.write("One idea at a time: a short lesson, then questions that climb "
                 "**recall → apply → transfer**. Pass a level with "
                 f"**{NEED} correct answers in a row**. Max {MAX_QUESTIONS} questions "
                 "per session - come back tomorrow for the rest.")
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

    else:
        c = concept_record()
        st.progress(min(len(ss.asked), MAX_QUESTIONS) / MAX_QUESTIONS,
                    text=f"Question {len(ss.asked)}/{MAX_QUESTIONS} · Level {ss.level}/3 "
                         f"({tutor.DIFFICULTY_NAMES.get(ss.level, '')}) · "
                         f"streak {c['streak']}/{NEED}")

        if ss.stage == "lesson":
            st.subheader(f"Lesson · {tutor.DIFFICULTY_NAMES[ss.level]}")
            st.success(f"**Goal:** {ss.objective}")
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
                if not result["correct"]:
                    ss.wrong_this_level += 1
                    ss.session_weak = result.get("weak_point") or ss.session_weak
                    ss.review = call(tutor.review_page, ss.material, ss.concept,
                                     result.get("weak_point") or "", ss.question, answer)
                ss.stage = "feedback"
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
                label, action = "Finish for today", "stop"
            elif ss.passed and ss.level >= profile_store.MAX_LEVEL:
                label, action = "Finish - concept mastered!", "mastered"
            elif len(ss.asked) >= MAX_QUESTIONS:
                label, action = "Finish for today", "limit"
            elif ss.passed:
                label, action = "Next level →", "level"
            else:
                label, action = "Next question →", "question"

            if st.button(label, type="primary"):
                if action == "stop":
                    ss.stage = "done"
                    ss.end_reason = (f"Let's stop here for today. Review is scheduled "
                                     f"for {c['next_review']}.")
                elif action == "limit":
                    ss.stage = "done"
                    ss.end_reason = (f"That's {MAX_QUESTIONS} questions - enough for "
                                     f"today. Next review: {c['next_review']}.")
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
                st.caption("Short sessions help memory stick, but it is your call.")
                col1, col2 = st.columns(2)
                if col1.button(f"Keep going: {MAX_QUESTIONS} more questions on "
                               f"{concept_title(nxt)}", width="stretch"):
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
    st.write("This is everything the agent remembers about you. The model itself "
             "forgets everything between calls - this file **is** its memory. "
             "It lives only in this browser session; download it to keep it, "
             "upload it next time to continue.")
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
