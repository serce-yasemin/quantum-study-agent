"""
Quantum Study Agent - web app (Streamlit)
Nebius x NVIDIA Global AI Hackathon 2026 - Personal AI track

Run locally:   streamlit run streamlit_app.py

Two tabs:
- Explore: an exact, interactive picture of one-qubit states (Bloch sphere +
  density-matrix heat map). No AI involved - every number is computed.
- Study: the AI tutor loop (lesson -> questions -> grading -> review pages),
  backed by NVIDIA Nemotron on Nebius Token Factory.

The learner profile lives in this browser session and can be downloaded as
JSON - your learning data stays under your control.
"""

import json
import os
from pathlib import Path

import numpy as np
import streamlit as st

st.set_page_config(page_title="Quantum Study Agent", page_icon="⚛️", layout="wide")

# Secrets from Streamlit Cloud -> environment, before the LLM client is created.
try:
    for key in ("NEBIUS_API_KEY",):
        if key in st.secrets and not os.environ.get(key):
            os.environ[key] = st.secrets[key]
    ACCESS_CODE = st.secrets.get("ACCESS_CODE")
except Exception:            # no secrets file when running locally
    ACCESS_CODE = None

import profile_store  # noqa: E402  (after env setup)
import quantum_viz as qv  # noqa: E402
import tutor  # noqa: E402

MATERIALS_DIR = Path(__file__).parent / "materials"
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


def load_material() -> str:
    if ss.get("material_choice") == "Paste my own text":
        return ss.get("own_text", "").strip()
    return (MATERIALS_DIR / "density_matrix.txt").read_text(encoding="utf-8")


def call(fn, *args):
    """Run an LLM step with a spinner; show a friendly error instead of a trace."""
    try:
        with st.spinner("Nemotron is thinking…"):
            return fn(*args)
    except Exception as exc:
        st.error(f"The model call failed: {exc}")
        st.stop()


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
        ss.concept = st.text_input("Concept", "density_matrix")
        ss.material_choice = st.radio("Study material",
                                      ["Built-in primer: density matrices",
                                       "Paste my own text"], horizontal=True)
        if ss.material_choice == "Paste my own text":
            ss.own_text = st.text_area("Paste a paragraph from a paper or lecture notes",
                                       height=180)
        if st.button("Start session", type="primary"):
            material = load_material()
            if len(material) < 200:
                st.warning("Please paste at least 200 characters of material "
                           "(no API call was made).")
                st.stop()
            ss.material = material
            c = concept_record()
            ss.level = profile_store.MAX_LEVEL if c["status"] == "mastered" else c["level"] + 1
            ss.asked = []
            start_level()
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
                    ss.end_reason = f"'{ss.concept}' mastered! Next review: {c['next_review']}."
                elif action == "level":
                    ss.level += 1
                    start_level()
                else:
                    next_question()
                st.rerun()

        elif ss.stage == "done":
            st.subheader("Session finished")
            st.info(ss.end_reason)
            st.write("Your progress is in the 🗂️ **My progress** tab - download it "
                     "to keep it.")
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
    if concepts:
        for name, rec in concepts.items():
            total = len(rec["history"])
            right = sum(h["correct"] for h in rec["history"])
            cols = st.columns(4)
            cols[0].metric("Concept", name)
            cols[1].metric("Level passed", f"{rec['level']}/3")
            cols[2].metric("Answers correct", f"{right}/{total}")
            cols[3].metric("Next review", rec["next_review"] or "—")
            weak = [h["weak_point"] for h in rec["history"] if h["weak_point"]]
            if weak:
                st.caption("Gaps found so far: " + "; ".join(dict.fromkeys(weak)))
    else:
        st.caption("No sessions yet.")

    st.download_button("Download my profile (JSON)",
                       json.dumps(ss.profile, indent=2, ensure_ascii=False),
                       file_name="learner_profile.json", mime="application/json")
    uploaded = st.file_uploader("Continue from a saved profile", type="json")
    if uploaded is not None and st.button("Load this profile"):
        ss.profile = json.load(uploaded)
        st.success("Profile loaded.")
