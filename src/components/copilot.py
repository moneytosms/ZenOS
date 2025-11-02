"""Copilot — course-aware study chatbot

This component provides a Copilot-style assistant that knows your courses,
their parsed syllabus data, pending tasks and recent grades, and offers
ready-made prompts (exam roadmap, weekly plan, next steps) plus a free-form chat.
"""

import streamlit as st
from datetime import date
from typing import List
from src.database.database import get_db_session
from src.database.models import Course, Syllabus, Task, Grade


def _safe_rerun():
    """Try to rerun Streamlit safely across different Streamlit versions.

    Streamlit exposed `st.experimental_rerun()` historically; in some
    newer/alternate runtimes that symbol may be missing. We attempt the
    standard call, then try to raise the runtime RerunException, and
    finally fall back to toggling a session flag and calling `st.stop()`.
    """
    try:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        # Fall through to other strategies
        pass

    try:
        # Try the internal RerunException (may not exist in all versions)
        from streamlit.runtime.script_runner import RerunException

        raise RerunException()
    except Exception:
        # Last resort: toggle a session flag and stop execution so the UI updates
        st.session_state["_copilot_rerun_flag"] = not st.session_state.get("_copilot_rerun_flag", False)
        try:
            st.stop()
        except Exception:
            # If st.stop is unavailable for some reason, just return
            return


def build_course_context(db, user_id: int) -> str:
    """Build a textual summary of all courses for sending as context to the assistant."""
    courses = db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()
    lines: List[str] = []
    for c in courses:
        syllabus = db.query(Syllabus).filter(Syllabus.user_id == user_id).order_by(Syllabus.uploaded_at.desc()).first()
        parsed = {}
        if syllabus and syllabus.parsed_data:
            parsed = next((cd for cd in syllabus.parsed_data.get('courses', []) if cd.get('name') == c.name), {})

        # Collect pending tasks and recent grades
        tasks = db.query(Task).filter(Task.user_id == user_id, Task.course_id == c.id).order_by(Task.due_date).limit(10).all()
        grades = db.query(Grade).filter(Grade.user_id == user_id, Grade.course_id == c.id).order_by(Grade.exam_date.desc()).limit(5).all()

        topics = parsed.get('topics', []) if isinstance(parsed.get('topics', []), list) else []
        objectives = parsed.get('objectives', []) if isinstance(parsed.get('objectives', []), list) else []

        lines.append(f"Course: {c.name} ({c.code or 'N/A'})")
        lines.append(f"Instructor: {c.instructor or 'N/A'}")
        lines.append(f"Credits: {c.credits or 0}")
        lines.append(f"Attendance required: {bool(c.attendance_required)}; threshold: {c.attendance_threshold or 75.0}%")
        lines.append(f"Start/End: {c.start_date or 'N/A'} to {c.end_date or 'N/A'}; skipped_classes: {c.skipped_classes or 0}")
        if topics:
            lines.append(f"Topics ({len(topics)}): {', '.join(topics[:20])}{'...' if len(topics) > 20 else ''}")
        if objectives:
            lines.append(f"Objectives ({len(objectives)}): {', '.join(objectives[:10])}{'...' if len(objectives) > 10 else ''}")

        if tasks:
            task_summaries = []
            for t in tasks:
                due = t.due_date.date().isoformat() if getattr(t, 'due_date', None) else 'N/A'
                task_summaries.append(f"{t.title} (due: {due})")
            lines.append(f"Pending tasks: {len(tasks)} - {', '.join(task_summaries[:5])}{'...' if len(task_summaries) > 5 else ''}")

        if grades:
            grade_summaries = []
            for g in grades:
                pct = (g.grade / g.max_grade * 100) if g.max_grade else 0
                grade_summaries.append(f"{g.assignment_name or 'Exam'}: {pct:.1f}%")
            lines.append(f"Recent grades: {', '.join(grade_summaries)}")

        lines.append("---")

    if not lines:
        return "No courses found for this user."

    header = (
        "You are a helpful study copilot. Below is the full context of the user's courses."
        " Use this information to give targeted study plans, roadmaps for exams, and next-step recommendations."
    )
    return header + "\n\n" + "\n".join(lines)


def render_copilot():
    """Render the Copilot chatbot UI."""
    st.title("🚀 Copilot — Course-aware Study Assistant")

    db = get_db_session()
    user_id = st.session_state.user_id
    gemini = st.session_state.get('gemini_service')

    try:
        if not gemini or not gemini.is_configured():
            st.warning("Please configure your Gemini API key in Settings before using Copilot.")
            return

        if user_id is None:
            st.error("No user session found. Please reload the app or sign in.")
            return

        # Ensure chat state
        if 'copilot_chat' not in st.session_state:
            st.session_state.copilot_chat = [
                {"role": "assistant", "text": "Hi — I'm your Copilot. I know about all your courses and can help plan study, create exam roadmaps, and suggest next steps. Pick a ready prompt or ask me anything."}
            ]

        # Build and show course context (collapsible) — be defensive in case DB access fails
        with st.expander("📚 Show course context sent to Copilot (click to view)"):
            try:
                context_text = build_course_context(db, user_id)
            except Exception as e:
                context_text = f"(Error building course context: {e})"
            st.text_area("Course Context", value=context_text, height=300, disabled=True)

        # UI: left column for templates, right column for chat
        left, right = st.columns([1, 2])

        with left:
            st.markdown("### Quick Prompts")

            # Exam roadmap template
            st.markdown("**Exam roadmap**")
            exam_course = st.selectbox("Course for exam", options=[c.name for c in db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()], key="exam_course_select")
            exam_date = st.date_input("Exam date", value=date.today(), key="exam_date_input")
            exam_topics = st.text_area("Topics (comma-separated, optional)", key="exam_topics_input")
            if st.button("Generate exam roadmap"):
                user_msg = f"I have an exam for {exam_course} on {exam_date.isoformat()}. The topics to cover are: {exam_topics or 'use course topics'}. Based on the course context below, give a prioritized study roadmap (day-by-day) for the days leading up to the exam, including what to cover each day and suggested study durations. Also list must-know concepts and practice suggestions." 
                st.session_state.copilot_chat.append({"role": "user", "text": user_msg})
                with st.spinner("Thinking..."):
                    try:
                        reply = gemini._generate_content(context_text + "\n\nUser request:\n" + user_msg)
                    except Exception as e:
                        reply = f"Error calling assistant: {str(e)}"
                    st.session_state.copilot_chat.append({"role": "assistant", "text": reply})
                    _safe_rerun()

            st.markdown("---")

            # Weekly plan template
            st.markdown("**Weekly plan**")
            wp_course = st.selectbox("Course for weekly plan", options=[c.name for c in db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()], key="wp_course_select")
            wp_hours = st.number_input("Hours per week", min_value=1, max_value=100, value=6, key="wp_hours_input")
            if st.button("Generate weekly plan"):
                user_msg = f"Create a weekly study plan for {wp_course} totaling {wp_hours} hours per week. Break down by day and suggest specific topics/activities, practice and review. Use course context below to prioritize topics." 
                st.session_state.copilot_chat.append({"role": "user", "text": user_msg})
                with st.spinner("Thinking..."):
                    try:
                        reply = gemini._generate_content(context_text + "\n\nUser request:\n" + user_msg)
                    except Exception as e:
                        reply = f"Error calling assistant: {str(e)}"
                    st.session_state.copilot_chat.append({"role": "assistant", "text": reply})
                    _safe_rerun()

            st.markdown("---")

            # Next steps / review prompt
            st.markdown("**What to review next**")
            ns_course = st.selectbox("Course (next review)", options=[c.name for c in db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()], key="ns_course_select")
            if st.button("Suggest next steps"):
                user_msg = f"Given my progress in {ns_course} (see context), suggest 3-5 concrete next steps to improve understanding and prepare for upcoming assessments. Include short practice activities and estimated time for each." 
                st.session_state.copilot_chat.append({"role": "user", "text": user_msg})
                with st.spinner("Thinking..."):
                    try:
                        reply = gemini._generate_content(context_text + "\n\nUser request:\n" + user_msg)
                    except Exception as e:
                        reply = f"Error calling assistant: {str(e)}"
                    st.session_state.copilot_chat.append({"role": "assistant", "text": reply})
                    _safe_rerun()

            st.markdown("---")
            if st.button("Clear chat"):
                st.session_state.copilot_chat = [{"role": "assistant", "text": "Hi — I'm your Copilot. I know about all your courses and can help plan study, create exam roadmaps, and suggest next steps. Pick a ready prompt or ask me anything."}]
                _safe_rerun()

        with right:
            st.markdown("### Chat")
            chat_box = st.container()
            with chat_box:
                for msg in st.session_state.copilot_chat:
                    # Assistant replies may contain HTML/Markdown — render as HTML when safe so
                    # the assistant's formatting shows correctly (images, lists, tables).
                    if msg['role'] == 'assistant':
                        try:
                            st.markdown(f"**Copilot:**\n{msg['text']}", unsafe_allow_html=True)
                        except Exception:
                            # Fallback: show as plain preformatted text
                            st.code(f"Copilot:\n{msg['text']}")
                    else:
                        # User messages should be shown plainly and safely (no HTML rendering)
                        st.markdown(f"**You:**")
                        st.code(msg['text'])

                # Input area
                user_input = st.text_area("Your message", key="copilot_input", height=120)
                if st.button("Send"):
                    if user_input and user_input.strip():
                        st.session_state.copilot_chat.append({"role": "user", "text": user_input})
                        with st.spinner("Thinking..."):
                            try:
                                reply = gemini._generate_content(context_text + "\n\nUser request:\n" + user_input)
                            except Exception as e:
                                reply = f"Error calling assistant: {str(e)}"
                            st.session_state.copilot_chat.append({"role": "assistant", "text": reply})
                            _safe_rerun()

    finally:
        db.close()
