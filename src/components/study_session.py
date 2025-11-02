"""Study Session Component with Pomodoro"""

import streamlit as st
import time as time_module
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from src.database.database import get_db_session
from src.database.models import StudySession, Course, Flashcard
from src.services.gemini_service import GeminiService
from src.components.ui.timer import timer_display
from src.components.ui.card import card
from src.utils.constants import POMODORO_WORK_MINUTES, POMODORO_SHORT_BREAK_MINUTES
from src.utils.course_helpers import get_course_background


def render_study_session():
    """Render study session interface"""
    st.title("📖 Study Session")
    
    db = get_db_session()
    user_id = st.session_state.user_id
    gemini_service: GeminiService = st.session_state.gemini_service
    
    try:
        courses = db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()
        
        if not courses:
            st.warning("📚 **No courses found!**")
            st.info("""
            **To start studying:**
            1. Go to **📋 Syllabus Upload** page
            2. Upload your syllabus or add courses manually
            3. Then come back here to start study sessions
            """)
            return
        
        # Session setup
        col1, col2 = st.columns(2)
        
        with col1:
            # Format course options with code if available
            course_options = [f"{c.name} ({c.code})" if c.code else c.name for c in courses]
            selected_course_display = st.selectbox(
                "Select Course",
                course_options,
                help="Choose a course for this study session"
            )
            # Extract course name from display string
            selected_course_name = selected_course_display.split(" (")[0] if " (" in selected_course_display else selected_course_display
            course = next((c for c in courses if c.name == selected_course_name), None)
        
        with col2:
            topic = st.text_input("Topic/Chapter to Study")
        
        # Session controls
        if 'session_active' not in st.session_state:
            st.session_state.session_active = False
        if 'session_start_time' not in st.session_state:
            st.session_state.session_start_time = None
        if 'session_paused_time' not in st.session_state:
            st.session_state.session_paused_time = None
        if 'session_total_paused_seconds' not in st.session_state:
            st.session_state.session_total_paused_seconds = 0
        if 'session_minutes' not in st.session_state:
            st.session_state.session_minutes = POMODORO_WORK_MINUTES
        if 'session_seconds' not in st.session_state:
            st.session_state.session_seconds = 0
        if 'session_type' not in st.session_state:
            st.session_state.session_type = "work"
        
        # Timer display
        timer_display(
            st.session_state.session_minutes,
            st.session_state.session_seconds,
            "Work" if st.session_state.session_type == "work" else "Break"
        )
        
        # Controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if not st.session_state.session_active:
                if st.button("▶️ Start Session", type="primary"):
                    st.session_state.session_active = True
                    st.session_state.session_start_time = datetime.now()
                    st.session_state.session_paused_time = None
                    st.session_state.session_total_paused_seconds = 0
                    st.session_state.session_minutes = POMODORO_WORK_MINUTES
                    st.session_state.session_seconds = 0
                    st.session_state.session_type = "work"
                    st.rerun()
        
        with col2:
            if st.session_state.session_active:
                if st.button("⏸️ Pause"):
                    # Calculate current remaining time before pausing
                    if st.session_state.session_start_time:
                        current_time = datetime.now()
                        total_elapsed = (current_time - st.session_state.session_start_time).total_seconds()
                        actual_elapsed = total_elapsed - st.session_state.session_total_paused_seconds
                        
                        # Use appropriate duration based on session type
                        session_duration_minutes = POMODORO_SHORT_BREAK_MINUTES if st.session_state.session_type == "break" else POMODORO_WORK_MINUTES
                        total_seconds_remaining = (session_duration_minutes * 60) - int(actual_elapsed)
                        
                        if total_seconds_remaining > 0:
                            st.session_state.session_minutes = total_seconds_remaining // 60
                            st.session_state.session_seconds = total_seconds_remaining % 60
                    
                    # Record when we paused
                    st.session_state.session_paused_time = datetime.now()
                    st.session_state.session_active = False
                    st.rerun()
            elif st.session_state.session_start_time is not None and st.session_state.session_paused_time:
                # Session is paused, show resume button
                if st.button("▶️ Resume", type="primary"):
                    # Calculate how long we were paused
                    if st.session_state.session_paused_time:
                        paused_duration = (datetime.now() - st.session_state.session_paused_time).total_seconds()
                        st.session_state.session_total_paused_seconds += paused_duration
                        st.session_state.session_paused_time = None
                    st.session_state.session_active = True
                    st.rerun()
        
        with col3:
            if st.button("🛑 End Session"):
                if st.session_state.session_start_time:
                    # Calculate actual duration excluding paused time
                    total_duration = (datetime.now() - st.session_state.session_start_time).total_seconds()
                    actual_duration = total_duration - st.session_state.session_total_paused_seconds
                    if st.session_state.session_paused_time:
                        # If currently paused, add the current pause duration
                        actual_duration -= (datetime.now() - st.session_state.session_paused_time).total_seconds()
                    
                    duration_minutes = max(0, int(actual_duration / 60))
                    session = StudySession(
                        user_id=user_id,
                        course_id=course.id if course else None,
                        topic=topic or "General Study",
                        duration_minutes=duration_minutes
                    )
                    db.add(session)
                    db.commit()
                
                st.session_state.session_active = False
                st.session_state.session_start_time = None
                st.session_state.session_paused_time = None
                st.session_state.session_total_paused_seconds = 0
                st.success("Session saved!")
                st.rerun()
        
        # Auto-refresh timer (only when active, not paused)
        if st.session_state.session_active and st.session_state.session_start_time:
            # Calculate elapsed time excluding pauses
            current_time = datetime.now()
            total_elapsed = (current_time - st.session_state.session_start_time).total_seconds()
            actual_elapsed = total_elapsed - st.session_state.session_total_paused_seconds
            
            # Use appropriate duration based on session type
            session_duration_minutes = POMODORO_SHORT_BREAK_MINUTES if st.session_state.session_type == "break" else POMODORO_WORK_MINUTES
            
            # Convert to minutes and seconds remaining
            total_seconds_remaining = (session_duration_minutes * 60) - int(actual_elapsed)
            
            if total_seconds_remaining > 0:
                st.session_state.session_minutes = total_seconds_remaining // 60
                st.session_state.session_seconds = total_seconds_remaining % 60
            else:
                # Time's up
                st.session_state.session_minutes = 0
                st.session_state.session_seconds = 0
                
                # Switch to break or end
                if st.session_state.session_type == "work":
                    st.session_state.session_type = "break"
                    st.session_state.session_minutes = POMODORO_SHORT_BREAK_MINUTES
                    st.session_state.session_seconds = 0
                    # Reset timer start for break
                    st.session_state.session_start_time = datetime.now()
                    st.session_state.session_total_paused_seconds = 0
                    st.balloons()
                else:
                    st.session_state.session_active = False
                    st.success("Break complete! Ready for next session.")
            
            time_module.sleep(1)
            st.rerun()
        
        # Topic brief
        if topic and gemini_service.is_configured():
            st.markdown("---")
            st.markdown("### 📝 Topic Brief")
            
            # Get course background if course is selected
            course_bg = None
            if course:
                course_bg = get_course_background(course, user_id)
            
            if st.button("Generate Brief"):
                with st.spinner("Generating topic brief..."):
                    brief = gemini_service.generate_topic_brief(
                        topic,
                        course_context=course.name if course else None,
                        course_background=course_bg
                    )
                    card("Study Brief", brief)
            
            # Quiz questions
            if st.button("📝 Generate Quiz Questions"):
                with st.spinner("Generating quiz questions..."):
                    questions = gemini_service.generate_quiz_questions(
                        topic,
                        course_background=course_bg
                    )
                    if questions:
                        for i, q in enumerate(questions, 1):
                            card(f"Question {i}", f"""
                            <p><strong>{q.get('question', '')}</strong></p>
                            <ul>
                                {''.join(f'<li>{opt}</li>' for opt in q.get('options', []))}
                            </ul>
                            <p><em>Correct Answer: {q.get('options', [])[q.get('correct', 0)] if q.get('options') else 'N/A'}</em></p>
                            <p><small>{q.get('explanation', '')}</small></p>
                            """)
        
        # Session history
        st.markdown("---")
        st.markdown("### 📊 Recent Sessions")
        recent_sessions = db.query(StudySession).options(
            joinedload(StudySession.course)
        ).filter(
            StudySession.user_id == user_id
        ).order_by(StudySession.completed_at.desc()).limit(5).all()
        
        if recent_sessions:
            for session in recent_sessions:
                course_name = session.course.name if session.course else "General"
                card(
                    f"{session.topic} - {course_name}",
                    f"""
                    Duration: {session.duration_minutes} minutes<br>
                    Completed: {session.completed_at.strftime('%Y-%m-%d %H:%M') if session.completed_at else 'N/A'}
                    """
                )
        else:
            st.info("No study sessions yet. Start your first session!")
    
    finally:
        db.close()

