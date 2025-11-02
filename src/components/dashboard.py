"""Unified Academic Dashboard"""

import streamlit as st
from datetime import datetime, date
from src.database.database import get_db_session
from src.database.models import Course, Task, Attendance, Grade, StudySession
from src.services.grade_calculator import calculate_current_grade
from src.utils.helpers import calculate_percentage, format_duration
from src.components.ui.card import card, metric_card


def render_dashboard():
    """Render unified dashboard"""
    st.title("🏠 Academic Dashboard")
    
    db = get_db_session()
    user_id = st.session_state.user_id
    
    try:
        # Get data
        courses = db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()
        
        # Show message if no courses
        if not courses:
            st.warning("📚 **No courses found!**")
            st.info("""
            **To get started:**
            1. Go to **📋 Syllabus Upload** page
            2. Upload your syllabus PDF or paste text
            3. Click "Parse Syllabus" to extract courses
            4. Or manually add courses using the "Add Course Manually" section
            """)
            return
        tasks = db.query(Task).filter(Task.user_id == user_id).all()
        attendance_records = db.query(Attendance).filter(Attendance.user_id == user_id).all()
        grades = db.query(Grade).filter(Grade.user_id == user_id).all()
        study_sessions = db.query(StudySession).filter(StudySession.user_id == user_id).all()
        
        # Calculate metrics
        total_courses = len(courses)
        pending_tasks = len([t for t in tasks if t.status == 'pending'])
        overdue_tasks = len([t for t in tasks if t.status == 'overdue' or (t.due_date and t.due_date.date() < date.today() and t.status != 'completed')])
        
        # Calculate attendance percentages
        course_attendance = {}
        for course in courses:
            course_attendance_records = [a for a in attendance_records if a.course_id == course.id]
            if course_attendance_records:
                present_count = sum(1 for a in course_attendance_records if a.present)
                total_count = len(course_attendance_records)
                course_attendance[course.id] = calculate_percentage(present_count, total_count)
        
        avg_attendance = sum(course_attendance.values()) / len(course_attendance) if course_attendance else 0
        
        # Calculate study time
        total_study_minutes = sum(s.duration_minutes for s in study_sessions if s.duration_minutes)
        
        # Calculate average grade
        if grades:
            grade_dicts = [
                {'grade': g.grade, 'max_grade': g.max_grade, 'weight': g.weight}
                for g in grades
            ]
            avg_grade = calculate_current_grade(grade_dicts)
        else:
            avg_grade = 0
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            metric_card(str(total_courses), "Total Courses")
        
        with col2:
            metric_card(f"{avg_attendance:.1f}%", "Avg Attendance", 
                       trend="On track" if avg_attendance >= 75 else "Below threshold",
                       trend_direction="up" if avg_attendance >= 75 else "down")
        
        with col3:
            metric_card(f"{avg_grade:.1f}%", "Average Grade")
        
        with col4:
            metric_card(format_duration(total_study_minutes), "Study Time")
        
        st.markdown("---")
        
        # Quick stats
        col1, col2 = st.columns(2)
        
        
        
        # Simple todo list (no deadlines or course overview)
        st.markdown("### ✅ Todo List")

        # Add new todo
        with st.form("add_todo_form", clear_on_submit=True):
            new_todo = st.text_input("Add new todo")
            submitted = st.form_submit_button("Add")
            if submitted and new_todo and new_todo.strip():
                todo = Task(
                    user_id=user_id,
                    course_id=None,
                    title=new_todo.strip(),
                    description=None,
                    due_date=None,
                    priority='low',
                    status='pending'
                )
                db.add(todo)
                db.commit()
                db.refresh(todo)
                st.success("Todo added")
                st.rerun()

        # List todos
        todo_items = db.query(Task).filter(Task.user_id == user_id).order_by(Task.id.desc()).all()

        if not todo_items:
            st.info("No todos yet — add one above.")
        else:
            for t in todo_items:
                cols = st.columns([8, 1, 1])
                checked = (t.status == 'completed')
                with cols[0]:
                    new_checked = st.checkbox(t.title, value=checked, key=f"todo_chk_{t.id}")
                    if new_checked and not checked:
                        t.status = 'completed'
                        db.add(t)
                        db.commit()
                        st.success("Marked complete")
                        st.rerun()
                    if not new_checked and checked:
                        t.status = 'pending'
                        db.add(t)
                        db.commit()
                        st.success("Marked pending")
                        st.rerun()
                with cols[1]:
                    if st.button("Delete", key=f"del_{t.id}"):
                        db.delete(t)
                        db.commit()
                        st.success("Deleted")
                        st.rerun()
        
        # Course attendance overview
        if course_attendance:
            st.markdown("### 📊 Course Attendance")
            for course in courses:
                if course.id in course_attendance:
                    att_percentage = course_attendance[course.id]
                    threshold = course.attendance_threshold or 75.0
                    color = "success" if att_percentage >= threshold else "warning" if att_percentage >= threshold - 10 else "error"
                    
                    from src.components.ui.progress_bar import progress_bar
                    progress_bar(
                        att_percentage,
                        max_value=100,
                        color=color,
                        label=f"{course.name} ({att_percentage:.1f}%)"
                    )
    
    finally:
        db.close()

