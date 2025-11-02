"""Wellness Layer Component"""

import streamlit as st
from datetime import date, datetime, timedelta
from src.database.database import get_db_session
from src.database.models import WellnessLog, FocusSession, StudySession
from src.components.ui.card import card
from src.utils.helpers import format_duration


def render_wellness():
    """Render wellness interface"""
    st.title("🧘 Wellness & Balance")
    st.markdown("Track your wellbeing, focus streaks, and take time for reflection.")
    
    db = get_db_session()
    user_id = st.session_state.user_id
    
    try:
        # Calculate focus streak
        study_sessions = db.query(StudySession).filter(
            StudySession.user_id == user_id
        ).order_by(StudySession.completed_at.desc()).all()
        
        # Calculate streak
        streak = 0
        current_date = date.today()
        for i in range(30):  # Check last 30 days
            check_date = current_date - timedelta(days=i)
            has_session = any(
                s.completed_at and s.completed_at.date() == check_date
                for s in study_sessions
            )
            if has_session:
                if i == 0 or (i > 0 and any(
                    s.completed_at and s.completed_at.date() == current_date - timedelta(days=i-1)
                    for s in study_sessions
                )):
                    streak += 1
                else:
                    break
            else:
                if i == 0:
                    break
        
        tabs = st.tabs(["📊 Overview", "📝 Reflection Log", "⏸️ Recovery"])
        
        with tabs[0]:
            # Metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("🔥 Focus Streak", f"{streak} days")
            
            with col2:
                total_study_time = sum(s.duration_minutes for s in study_sessions if s.duration_minutes)
                st.metric("⏱️ Total Study Time", format_duration(total_study_time))
            
            with col3:
                today_sessions = [
                    s for s in study_sessions
                    if s.completed_at and s.completed_at.date() == date.today()
                ]
                st.metric("📚 Sessions Today", len(today_sessions))
            
            # Streak visualization
            st.markdown("### 🔥 Focus Streak")
            if streak > 0:
                st.success(f"🔥 Great job! You've studied for {streak} days in a row!")
                if streak >= 7:
                    st.balloons()
                    st.info("🌟 Week-long streak! Amazing dedication!")
                elif streak >= 3:
                    st.info("💪 Building momentum! Keep it up!")
            else:
                st.info("Start a study session today to begin your streak!")
            
            # Overwork detection
            today_minutes = sum(
                s.duration_minutes for s in today_sessions
                if s.duration_minutes
            )
            
            if today_minutes > 480:  # 8 hours
                st.warning("⚠️ You've studied for over 8 hours today. Consider taking a break!")
            elif today_minutes > 360:  # 6 hours
                st.info("💡 You've had a productive day! Remember to rest.")
            
            # Weekly summary
            st.markdown("### 📅 Weekly Summary")
            week_start = date.today() - timedelta(days=date.today().weekday())
            week_sessions = [
                s for s in study_sessions
                if s.completed_at and s.completed_at.date() >= week_start
            ]
            
            weekly_time = sum(s.duration_minutes for s in week_sessions if s.duration_minutes)
            card(
                "This Week",
                f"""
                <ul>
                    <li><strong>Sessions:</strong> {len(week_sessions)}</li>
                    <li><strong>Study Time:</strong> {format_duration(weekly_time)}</li>
                    <li><strong>Average per Day:</strong> {format_duration(weekly_time / 7 if weekly_time > 0 else 0)}</li>
                </ul>
                """
            )
        
        with tabs[1]:
            st.markdown("### Daily Reflection")
            
            # Get today's log
            today_log = db.query(WellnessLog).filter(
                WellnessLog.user_id == user_id,
                WellnessLog.date == date.today()
            ).first()
            
            mood_rating = st.slider(
                "How are you feeling today?",
                1, 5,
                value=today_log.mood_rating if today_log else 3
            )
            
            energy_level = st.slider(
                "Energy Level",
                1, 5,
                value=today_log.energy_level if today_log else 3
            )
            
            reflection = st.text_area(
                "Today's Reflection",
                value=today_log.reflection if today_log else "",
                placeholder="How did today go? What did you learn?",
                height=150
            )
            
            gratitude = st.text_area(
                "Gratitude",
                value=today_log.gratitude if today_log else "",
                placeholder="What are you grateful for today?",
                height=100
            )
            
            if st.button("💾 Save Reflection"):
                if today_log:
                    today_log.mood_rating = mood_rating
                    today_log.energy_level = energy_level
                    today_log.reflection = reflection
                    today_log.gratitude = gratitude
                else:
                    log = WellnessLog(
                        user_id=user_id,
                        date=date.today(),
                        mood_rating=mood_rating,
                        energy_level=energy_level,
                        reflection=reflection,
                        gratitude=gratitude
                    )
                    db.add(log)
                db.commit()
                st.success("Reflection saved!")
            
            # Past reflections
            st.markdown("### Past Reflections")
            past_logs = db.query(WellnessLog).filter(
                WellnessLog.user_id == user_id
            ).order_by(WellnessLog.date.desc()).limit(7).all()
            
            for log in past_logs:
                mood_emoji = "😊" if log.mood_rating >= 4 else "😐" if log.mood_rating >= 3 else "😔"
                card(
                    f"{log.date.strftime('%Y-%m-%d')} {mood_emoji}",
                    f"""
                    <strong>Mood:</strong> {log.mood_rating}/5 | <strong>Energy:</strong> {log.energy_level}/5<br>
                    <strong>Reflection:</strong> {log.reflection or 'No reflection'}<br>
                    <strong>Gratitude:</strong> {log.gratitude or 'None'}
                    """
                )
        
        with tabs[2]:
            st.markdown("### Recovery & Balance")
            
            # Recovery suggestions
            if today_minutes > 480:
                st.warning("""
                ### ⚠️ Time for a Break
                
                You've put in a lot of work today. Consider:
                - Taking a walk
                - Practicing mindfulness
                - Getting some sleep
                - Doing something you enjoy
                """)
            elif today_minutes == 0:
                st.info("""
                ### 💡 Rest Day
                
                It's okay to take breaks! Rest is important for learning.
                """)
            else:
                st.success("""
                ### ✅ Well Balanced
                
                You're maintaining a healthy study-work balance!
                """)
            
            # Balance tips
            card(
                "🧘 Wellness Tips",
                """
                <ul>
                    <li>Take regular breaks during study sessions</li>
                    <li>Get 7-9 hours of sleep</li>
                    <li>Stay hydrated and eat well</li>
                    <li>Practice mindfulness or meditation</li>
                    <li>Exercise regularly</li>
                    <li>Stay connected with friends and family</li>
                </ul>
                """
            )
    
    finally:
        db.close()

