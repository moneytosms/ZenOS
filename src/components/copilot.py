"""Copilot — course-aware study chatbot

This component provides a Copilot-style assistant that knows your courses,
their parsed syllabus data, pending tasks and recent grades, and offers
ready-made prompts (exam roadmap, weekly plan, next steps) plus a free-form chat.
"""

import streamlit as st
from datetime import date
from typing import List
import time

# Database models and helpers
try:
    # Preferred import (works when package paths are set up normally)
    from src.database.database import get_db_session
except Exception:
    # Fallback: import the SessionLocal factory and create a small shim.
    from src.database.database import SessionLocal as _SessionLocal

    def get_db_session():
        """Fallback get_db_session when direct import fails (robust for different run contexts)."""
        return _SessionLocal()

from src.database.models import Course, Syllabus, Task, Grade

# Small cached wrapper for building course context to avoid repeated DB work
@st.cache_data(ttl=600)
def _cached_course_context(user_id: int, syllabus_version: float) -> str:
    db = get_db_session()
    try:
        return build_course_context(db, user_id)
    finally:
        try:
            db.close()
        except Exception:
            pass


def _start_background_generation(prompt: str, context_text: str, gemini):
    """Start a background thread that generates the assistant reply and writes
    the partial/full text into session_state so the main thread can poll it.
    This is a simple fallback when true SDK streaming isn't available.
    """
    import threading

    def _worker():
        try:
            # Build a combined prompt with context to give the assistant course info
            full_prompt = (context_text + "\n\n" + prompt) if context_text else prompt
            # Use gemini's synchronous generator
            reply = gemini._generate_content(full_prompt) if hasattr(gemini, '_generate_content') else gemini._generate_content(prompt)
            st.session_state['_copilot_background_partial'] = reply
            st.session_state['_copilot_background_done'] = True
            st.session_state['_copilot_background_error'] = ""
        except Exception as e:
            st.session_state['_copilot_background_error'] = str(e)
            st.session_state['_copilot_background_done'] = True

    # Initialize state
    st.session_state['_copilot_background_partial'] = ""
    st.session_state['_copilot_background_done'] = False
    st.session_state['_copilot_background_error'] = ""

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def _await_background_and_get_result(placeholder=None, timeout: float = 30.0, poll_interval: float = 0.12):
    """Poll the session_state keys set by the background worker and return
    (reply_text, from_cache_bool, duration_seconds, error_str).
    If a placeholder is provided, update it with any partial text to simulate streaming.
    """
    start = time.time()
    while True:
        if st.session_state.get('_copilot_background_done'):
            err = st.session_state.get('_copilot_background_error', '')
            reply = st.session_state.get('_copilot_background_partial', '')
            dur = time.time() - start
            return reply, False, dur, err

        if time.time() - start > timeout:
            return "", False, 0.0, "timeout"

        # Update placeholder with any partial text to simulate streaming
        if placeholder:
            try:
                partial = st.session_state.get('_copilot_background_partial', '')
                if partial:
                    placeholder.markdown(partial)
            except Exception:
                pass
        time.sleep(poll_interval)


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

        # Build and show course context (collapsible) — use a small cached helper
        try:
            # compute a lightweight syllabus version (latest uploaded_at) to include in cache key
            latest = db.query(Syllabus).filter(Syllabus.user_id == user_id).order_by(Syllabus.uploaded_at.desc()).first()
            syllabus_version = latest.uploaded_at.timestamp() if latest and getattr(latest, 'uploaded_at', None) else 0.0
        except Exception:
            syllabus_version = 0.0

        # Use cached context builder to avoid repeated expensive DB traversals
        try:
            context_text = _cached_course_context(user_id, syllabus_version)
        except Exception:
            # Fallback to building inline if cache helper fails
            try:
                context_text = build_course_context(db, user_id)
            except Exception as e:
                context_text = f"(Error building course context: {e})"

        with st.expander("📚 Show course context sent to Copilot (click to view)"):
            st.text_area("Course Context", value=context_text, height=200, disabled=True)

        # Ensure a generation flag is present so we can explicitly clear it after replies
        if '_copilot_generating' not in st.session_state:
            st.session_state['_copilot_generating'] = False

        # Chat-first layout: chat area occupies full width and supports streaming replies.
        st.markdown("### Chat")
        # We'll render the chat into this placeholder so we can re-render on demand
        chat_holder = st.empty()

        def _bubble_html(text: str, role: str) -> str:
            """Return simple HTML for a chat bubble aligned by role ('assistant'|'user')."""
            # Basic styling — keep inline to avoid external CSS dependence
            safe_text = text.replace("\n", "<br/>")
            if role == 'assistant':
                return (
                    f"<div style='margin:8px 0; text-align:left;'><div "
                    f"style='display:inline-block; background:#0b1220; color:#e6eef8; padding:12px; "
                    f"border-radius:10px; max-width:72%; line-height:1.4;'>{safe_text}</div></div>"
                )
            else:
                return (
                    f"<div style='margin:8px 0; text-align:right;'><div "
                    f"style='display:inline-block; background:#2b2f36; color:#f8fafc; padding:12px; "
                    f"border-radius:10px; max-width:72%; line-height:1.4;'>{safe_text}</div></div>"
                )


        def _render_messages(holder):
            """Render all messages into the given placeholder/container as stacked bubbles."""
            with holder.container():
                for msg in st.session_state.copilot_chat:
                    try:
                        html = _bubble_html(msg['text'], msg.get('role', 'assistant'))
                        st.markdown(html, unsafe_allow_html=True)
                    except Exception:
                        # Fallback: show plain text
                        if msg.get('role') == 'assistant':
                            st.markdown(f"**Copilot:**\n{msg['text']}")
                        else:
                            st.markdown(f"**You:**\n{msg['text']}")

        # Initial render of message history
        _render_messages(chat_holder)

        # A central streaming placeholder placed directly under the chat area.
        # This ensures any streamed assistant content appears beneath the messages
        # (not over in the send column). We'll reuse `stream_placeholder` for
        # all streaming operations below.
        stream_placeholder = st.empty()

        st.markdown("---")
        if st.button("Clear chat"):
            st.session_state.copilot_chat = [{"role": "assistant", "text": "Hi — I'm your Copilot. I know about all your courses and can help plan study, create exam roadmaps, and suggest next steps. Pick a ready prompt or ask me anything."}]
            _safe_rerun()

        # Re-use the chat_holder to render the full chat; the input area sits below
        # the messages and the send button is placed to the right of the input for
        # a conventional chat feel.
        _render_messages(chat_holder)

        input_col, send_col = st.columns([8, 1])
        # If a previous send requested the input be cleared, set the session value
        # before the widget is instantiated (Streamlit forbids modifying a widget
        # key after the widget has been created in the same run).
        if st.session_state.get('_copilot_input_clear'):
            try:
                st.session_state['copilot_input'] = ""
            except Exception:
                pass
            st.session_state['_copilot_input_clear'] = False

        with input_col:
            user_input = st.text_area("Your message", key="copilot_input", height=120)
        with send_col:
            if st.button("Send"):
                if user_input and user_input.strip():
                    st.session_state.copilot_chat.append({"role": "user", "text": user_input})
                    # re-render so the user's message appears immediately
                    _render_messages(chat_holder)
                    # Use the centralized stream placeholder so streamed text
                    # appears below the chat history.
                    st.session_state['_copilot_generating'] = True
                    with st.spinner("Thinking"):
                        try:
                            if hasattr(gemini, 'stream_generate_content'):
                                partial = ""
                                for chunk in gemini.stream_generate_content(user_input):
                                    partial += chunk
                                    try:
                                        stream_placeholder.markdown(_bubble_html(partial, 'assistant'), unsafe_allow_html=True)
                                    except Exception:
                                        pass
                                reply = partial
                            else:
                                _start_background_generation(user_input, context_text, gemini)
                                reply, cached, dur, err = _await_background_and_get_result(placeholder=stream_placeholder)
                                if err:
                                    reply = f"Error calling assistant: {err}"
                        except Exception as e:
                            reply = f"Error calling assistant: {e}"
                        finally:
                            st.session_state['_copilot_generating'] = False

                    st.session_state.copilot_chat.append({"role": "assistant", "text": reply})
                    # request input clear for the next run (set before widget instantiation)
                    st.session_state['_copilot_input_clear'] = True
                    _safe_rerun()
            # "More options" toggle placed below the Send button so templates are
            # available after composing a message. We use a session flag to
            # preserve the expanded/collapsed state across reruns.
            if '_copilot_show_more_options' not in st.session_state:
                st.session_state['_copilot_show_more_options'] = False

            if st.button("More options " + ("▲" if st.session_state['_copilot_show_more_options'] else "▼")):
                st.session_state['_copilot_show_more_options'] = not st.session_state['_copilot_show_more_options']

            if st.session_state['_copilot_show_more_options']:
                # Render the options in the send column below the buttons. This
                # keeps them visually below Send and ensures the UI persists.
                with st.container():
                    st.markdown("Customize templates below; use these templates to craft messages you can send to Copilot.")
                    # Exam roadmap details
                    st.subheader("Exam roadmap")
                    exam_course = st.selectbox("Course for exam", options=[c.name for c in db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()], key="exam_course_select")
                    exam_date = st.date_input("Exam date", value=date.today(), key="exam_date_input")
                    exam_topics = st.text_input("Topics (comma-separated, optional)", key="exam_topics_input")
                    if st.button("Send exam roadmap"):
                        user_msg = f"I have an exam for {exam_course} on {exam_date.isoformat()}. The topics to cover are: {exam_topics or 'use course topics'}. Based on the course context below, give a prioritized study roadmap (day-by-day) for the days leading up to the exam, including what to cover each day and suggested study durations. Also list must-know concepts and practice suggestions."
                        st.session_state.copilot_chat.append({"role": "user", "text": user_msg})
                        # re-render so the user's message appears immediately
                        _render_messages(chat_holder)
                        # Stream into the centralized placeholder under the chat
                        st.session_state['_copilot_generating'] = True
                        with st.spinner("Thinking"):
                            try:
                                if hasattr(gemini, 'stream_generate_content'):
                                    partial = ""
                                    for chunk in gemini.stream_generate_content(user_msg):
                                        try:
                                            partial += chunk
                                        except Exception:
                                            partial = (partial or "") + str(chunk)
                                        try:
                                            stream_placeholder.markdown(_bubble_html(partial, 'assistant'), unsafe_allow_html=True)
                                        except Exception:
                                            pass
                                    reply = partial
                                else:
                                    # Fallback to background generation
                                    _start_background_generation(user_msg, context_text, gemini)
                                    reply, cached, dur, err = _await_background_and_get_result(placeholder=stream_placeholder)
                                    if err:
                                        reply = f"Error calling assistant: {err}"
                            except Exception as e:
                                reply = f"Error calling assistant: {e}"
                            finally:
                                st.session_state['_copilot_generating'] = False

                        st.session_state.copilot_chat.append({"role": "assistant", "text": reply})
                        _safe_rerun()

                    st.markdown("---")

                    # Weekly plan details
                    st.subheader("Weekly plan")
                    wp_course = st.selectbox("Course for weekly plan", options=[c.name for c in db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()], key="wp_course_select")
                    wp_hours = st.number_input("Hours per week", min_value=1, max_value=100, value=6, key="wp_hours_input")
                    if st.button("Send weekly plan"):
                        user_msg = f"Create a weekly study plan for {wp_course} totaling {wp_hours} hours per week. Break down by day and suggest specific topics/activities, practice and review. Use course context below to prioritize topics."
                        st.session_state.copilot_chat.append({"role": "user", "text": user_msg})
                        _render_messages(chat_holder)
                        st.session_state['_copilot_generating'] = True
                        with st.spinner("Thinking"):
                            try:
                                if hasattr(gemini, 'stream_generate_content'):
                                    partial = ""
                                    for chunk in gemini.stream_generate_content(user_msg):
                                        partial += chunk
                                        try:
                                            stream_placeholder.markdown(_bubble_html(partial, 'assistant'), unsafe_allow_html=True)
                                        except Exception:
                                            pass
                                    reply = partial
                                else:
                                    _start_background_generation(user_msg, context_text, gemini)
                                    reply, cached, dur, err = _await_background_and_get_result(placeholder=stream_placeholder)
                                    if err:
                                        reply = f"Error calling assistant: {err}"
                            except Exception as e:
                                reply = f"Error calling assistant: {e}"
                            finally:
                                st.session_state['_copilot_generating'] = False
                            st.session_state.copilot_chat.append({"role": "assistant", "text": reply})
                            _safe_rerun()

                    st.markdown("---")

                    # Next steps details
                    st.subheader("What to review next")
                    ns_course = st.selectbox("Course (next review)", options=[c.name for c in db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()], key="ns_course_select")
                    if st.button("Send next steps"):
                        user_msg = f"Given my progress in {ns_course} (see context), suggest 3-5 concrete next steps to improve understanding and prepare for upcoming assessments. Include short practice activities and estimated time for each."
                        st.session_state.copilot_chat.append({"role": "user", "text": user_msg})
                        _render_messages(chat_holder)
                        st.session_state['_copilot_generating'] = True
                        with st.spinner("Thinking"):
                            try:
                                if hasattr(gemini, 'stream_generate_content'):
                                    partial = ""
                                    for chunk in gemini.stream_generate_content(user_msg):
                                        partial += chunk
                                        try:
                                            stream_placeholder.markdown(_bubble_html(partial, 'assistant'), unsafe_allow_html=True)
                                        except Exception:
                                            pass
                                    reply = partial
                                else:
                                    _start_background_generation(user_msg, context_text, gemini)
                                    reply, cached, dur, err = _await_background_and_get_result(placeholder=stream_placeholder)
                                    if err:
                                        reply = f"Error calling assistant: {err}"
                            except Exception as e:
                                reply = f"Error calling assistant: {e}"
                            finally:
                                st.session_state['_copilot_generating'] = False
                        st.session_state.copilot_chat.append({"role": "assistant", "text": reply})
                        _safe_rerun()

            # Small instrumentation output so you can see if calls are cached and timing
            if '_last_call_duration' in st.session_state:
                dur = st.session_state.get('_last_call_duration', 0.0)
                cached = st.session_state.get('_last_call_from_cache', False)
                st.caption(f"Last assistant call: {dur:.2f}s {'(from cache)' if cached else ''}")

    finally:
        db.close()
