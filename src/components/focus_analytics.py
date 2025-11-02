"""Focus Analytics Component"""

import streamlit as st
from datetime import datetime, date, timedelta
from collections import defaultdict
from src.database.database import get_db_session
from src.database.models import FocusSession, StudySession
from src.utils.helpers import format_duration
from src.components.ui.card import card
import pandas as pd


def render_focus_analytics():
    """Render focus analytics dashboard"""
    st.title("📊 Focus Analytics")
    st.markdown("Track your focus patterns, best hours, and productivity metrics.")
    
    db = get_db_session()
    user_id = st.session_state.user_id
    
    try:
        # Get all sessions
        study_sessions = db.query(StudySession).filter(
            StudySession.user_id == user_id
        ).order_by(StudySession.completed_at.desc()).all()
        
        focus_sessions = db.query(FocusSession).filter(
            FocusSession.user_id == user_id
        ).order_by(FocusSession.start_time.desc()).all()
        
        if not study_sessions and not focus_sessions:
            st.info("Start some study sessions to see your analytics!")
            return
        
        # Overall metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_study_time = sum(s.duration_minutes for s in study_sessions if s.duration_minutes)
        
        with col1:
            st.metric("Total Sessions", len(study_sessions))
        with col2:
            st.metric("Total Study Time", format_duration(total_study_time))
        with col3:
            avg_session = total_study_time / len(study_sessions) if study_sessions else 0
            st.metric("Avg Session Length", format_duration(int(avg_session)))
        with col4:
            days_active = len(set(
                s.completed_at.date() for s in study_sessions
                if s.completed_at
            ))
            st.metric("Days Active", days_active)
        
        tabs = st.tabs(["⏰ Best Hours", "📈 Trends", "📅 Calendar View", "🎯 Insights"])
        
        with tabs[0]:
            st.markdown("### Peak Focus Hours")
            
            # Analyze by hour
            hour_distribution = defaultdict(int)
            for session in study_sessions:
                if session.completed_at:
                    hour = session.completed_at.hour
                    hour_distribution[hour] += session.duration_minutes or 0
            
            if hour_distribution:
                # Create chart data
                hours = list(range(24))
                minutes = [hour_distribution.get(h, 0) for h in hours]
                
                df = pd.DataFrame({
                    'Hour': [f"{h:02d}:00" for h in hours],
                    'Minutes': minutes
                })
                
                # Find best hours
                best_hours = sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
                
                st.markdown("#### Top 3 Focus Hours")
                for i, (hour, minutes) in enumerate(best_hours, 1):
                    card(f"#{i} {hour:02d}:00", f"{format_duration(minutes)} studied at this hour")
                
                # Simple bar chart
                st.bar_chart(df.set_index('Hour'))
            else:
                st.info("Not enough data to analyze focus hours.")
        
        with tabs[1]:
            st.markdown("### Study Trends")
            
            # Last 7 days
            last_7_days = []
            for i in range(7):
                day = date.today() - timedelta(days=i)
                day_sessions = [
                    s for s in study_sessions
                    if s.completed_at and s.completed_at.date() == day
                ]
                day_minutes = sum(s.duration_minutes for s in day_sessions if s.duration_minutes)
                last_7_days.append({
                    'Date': day.strftime('%Y-%m-%d'),
                    'Minutes': day_minutes
                })
            
            df_week = pd.DataFrame(reversed(last_7_days))
            st.line_chart(df_week.set_index('Date'))
            
            # Weekly comparison
            st.markdown("### Weekly Comparison")
            this_week = date.today() - timedelta(days=date.today().weekday())
            last_week = this_week - timedelta(days=7)
            
            this_week_sessions = [
                s for s in study_sessions
                if s.completed_at and s.completed_at.date() >= this_week
            ]
            last_week_sessions = [
                s for s in study_sessions
                if s.completed_at and last_week <= s.completed_at.date() < this_week
            ]
            
            this_week_time = sum(s.duration_minutes for s in this_week_sessions if s.duration_minutes)
            last_week_time = sum(s.duration_minutes for s in last_week_sessions if s.duration_minutes)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("This Week", format_duration(this_week_time))
            with col2:
                delta = this_week_time - last_week_time
                st.metric("Last Week", format_duration(last_week_time), delta=f"{delta:+d} min")
        
        with tabs[2]:
            st.markdown("### Study Calendar")
            
            # Last 30 days heatmap data
            heatmap_data = {}
            for i in range(30):
                day = date.today() - timedelta(days=i)
                day_sessions = [
                    s for s in study_sessions
                    if s.completed_at and s.completed_at.date() == day
                ]
                day_minutes = sum(s.duration_minutes for s in day_sessions if s.duration_minutes)
                heatmap_data[day.strftime('%Y-%m-%d')] = day_minutes
            
            # Display as cards
            st.markdown("#### Last 30 Days")
            for day_str, minutes in sorted(heatmap_data.items(), reverse=True)[:14]:
                intensity = "High" if minutes > 120 else "Medium" if minutes > 60 else "Low" if minutes > 0 else "None"
                color_class = "success" if minutes > 120 else "warning" if minutes > 60 else "info" if minutes > 0 else ""
                card(f"{day_str} - {intensity}", f"{format_duration(minutes)}")
        
        with tabs[3]:
            st.markdown("### Insights & Recommendations")
            
            # Consistency analysis
            recent_sessions = [s for s in study_sessions if s.completed_at][:14]
            if len(recent_sessions) >= 7:
                st.success("✅ You've been consistent with your studies!")
            else:
                st.info("💡 Try to study more consistently for better results.")
            
            # Best day of week
            day_distribution = defaultdict(int)
            for session in study_sessions:
                if session.completed_at:
                    day_name = session.completed_at.strftime('%A')
                    day_distribution[day_name] += session.duration_minutes or 0
            
            if day_distribution:
                best_day = max(day_distribution.items(), key=lambda x: x[1])
                card(
                    "Best Study Day",
                    f"{best_day[0]}: {format_duration(best_day[1])}"
                )
            
            # Recommendations
            if total_study_time < 300:  # Less than 5 hours total
                card(
                    "💡 Recommendation",
                    "Consider increasing your study time gradually. Start with 25-minute Pomodoro sessions!"
                )
            elif avg_session < 25:
                card(
                    "💡 Recommendation",
                    "Try extending your study sessions to 45-60 minutes for deeper learning."
                )
            else:
                card(
                    "💡 Recommendation",
                    "You're doing great! Keep up the excellent work and maintain your study routine."
                )
    
    finally:
        db.close()

