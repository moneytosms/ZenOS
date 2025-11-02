"""Attendance Tracker Component"""

import streamlit as st
from datetime import date, datetime, timedelta
from src.database.database import get_db_session
from src.database.models import Attendance, Course, Grade, Timetable
from src.services.grade_calculator import calculate_current_grade, predict_grade_needed
from src.utils.helpers import calculate_percentage
from src.utils.course_helpers import calculate_total_classes_for_course
from src.components.ui.progress_bar import progress_bar
from src.components.ui.card import card


def render_attendance():
    """Render attendance tracker"""
    st.title("✅ Attendance & Grade Tracker")
    
    db = get_db_session()
    user_id = st.session_state.user_id
    
    try:
        courses = db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()
        
        if not courses:
            st.warning("📚 **No courses found!**")
            st.info("""
            **To track attendance:**
            1. Go to **📋 Syllabus Upload** page
            2. Upload your syllabus or add courses manually
            3. Then come back here to track attendance
            """)
            return
        
        tabs = st.tabs(["📊 Attendance", "📈 Grades"])
        
        with tabs[0]:
            st.markdown("### Course Attendance")
            
            # Format course options with code if available
            course_options = [f"{c.name} ({c.code})" if c.code else c.name for c in courses]
            selected_course_display = st.selectbox(
                "Select Course",
                course_options,
                help="Choose a course to track attendance"
            )
            # Extract course name from display string
            selected_course_name = selected_course_display.split(" (")[0] if " (" in selected_course_display else selected_course_display
            course = next((c for c in courses if c.name == selected_course_name), None)
            
            if course:
                # Calculate expected hours based on timetable entries (preferred) or fallback to class-count
                skipped_classes = course.skipped_classes or 0
                threshold = course.attendance_threshold or 75.0

                total_expected_hours = 0.0
                total_expected_occurrences = 0

                # Try to compute expected hours from timetable entries for this course
                timetable_entries = db.query(Timetable).filter(
                    Timetable.course_id == course.id,
                    Timetable.user_id == user_id
                ).all()

                def count_weekday_occurrences(start_d, end_d, weekday):
                    if not start_d or not end_d:
                        return 0
                    # Count dates in [start_d, end_d] with given weekday
                    cur = start_d
                    count = 0
                    while cur <= end_d:
                        if cur.weekday() == weekday:
                            count += 1
                        cur = cur + timedelta(days=1)
                    return count

                if timetable_entries and course.start_date and course.end_date:
                    for entry in timetable_entries:
                        # Duration in hours
                        try:
                            start_dt = datetime.combine(date.min, entry.start_time)
                            end_dt = datetime.combine(date.min, entry.end_time)
                            duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
                            if duration_hours <= 0:
                                continue
                        except Exception:
                            # If times are malformed, skip this entry
                            continue

                        occurrences = count_weekday_occurrences(course.start_date, course.end_date, entry.day_of_week)
                        total_expected_hours += occurrences * duration_hours
                        total_expected_occurrences += occurrences

                    # Fallback: if we couldn't compute any occurrences, treat as 0
                else:
                    # Fallback to class-count method: one-hour classes Monday-Friday
                    total_occurrences = calculate_total_classes_for_course(course)
                    total_expected_occurrences = total_occurrences
                    total_expected_hours = float(total_occurrences) * 1.0

                # Compute skipped hours based on average class duration
                if total_expected_occurrences > 0:
                    avg_duration = total_expected_hours / total_expected_occurrences
                    skipped_hours = skipped_classes * avg_duration
                else:
                    skipped_hours = 0.0

                attended_hours = max(total_expected_hours - skipped_hours, 0.0)

                # Calculate attendance percentage based on hours
                attendance_percentage = calculate_percentage(attended_hours, total_expected_hours) if total_expected_hours > 0 else 0
                
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Attendance %", f"{attendance_percentage:.1f}%")
                with col2:
                    # Show attended as hours (if we have hours) or classes
                    if total_expected_hours > 0:
                        st.metric("Attended (hrs)", f"{attended_hours:.1f}")
                    else:
                        st.metric("Attended", int(attended_hours))
                with col3:
                    # Show skipped as count and hours when available
                    if total_expected_hours > 0:
                        st.metric("Skipped (hrs)", f"{skipped_hours:.1f} ({skipped_classes} skips)")
                    else:
                        st.metric("Skipped", skipped_classes)
                with col4:
                    if total_expected_hours > 0:
                        st.metric("Total Hours", f"{total_expected_hours:.1f}")
                    else:
                        st.metric("Total Classes", total_expected_occurrences)
                
                # Progress bar
                color = "success" if attendance_percentage >= threshold else "warning" if attendance_percentage >= threshold - 10 else "error"
                progress_bar(
                    attendance_percentage,
                    max_value=100,
                    color=color,
                    label=f"Target: {threshold}%"
                )
                
                # Skip counter with +/- buttons
                st.markdown("### 📊 Skip Counter")
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**Current Skips: {skipped_classes}**")
                    if total_expected_occurrences > 0:
                        # Maximum safe skips in terms of occurrences (classes)
                        max_skips = int(max(0, total_expected_occurrences - int((threshold / 100.0) * total_expected_occurrences)))
                        st.caption(f"Maximum safe skips: {max_skips} (to maintain {threshold}%)")
                
                with col2:
                    if st.button("➕ Add Skip", key="add_skip"):
                        course.skipped_classes = (course.skipped_classes or 0) + 1
                        db.commit()
                        st.success("Skip added!")
                        st.rerun()
                
                with col3:
                    if st.button("➖ Remove Skip", key="remove_skip"):
                        if course.skipped_classes and course.skipped_classes > 0:
                            course.skipped_classes = course.skipped_classes - 1
                            db.commit()
                            st.success("Skip removed!")
                            st.rerun()
                
                # Alert
                if attendance_percentage < threshold:
                    remaining = threshold - attendance_percentage
                    # classes needed estimated from hours
                    if total_expected_hours > 0 and total_expected_occurrences > 0:
                        hours_needed = (remaining / 100.0) * total_expected_hours
                        classes_needed = int((hours_needed / (total_expected_hours / total_expected_occurrences)) + 0.999)
                    else:
                        classes_needed = int((remaining / 100.0) * total_expected_occurrences) if total_expected_occurrences > 0 else 0

                    st.warning(f"⚠️ Below threshold! You need to attend {classes_needed} more classes to reach {threshold}%")
                    st.info(f"Currently skipped: {skipped_classes} classes. Reduce skips to improve attendance.")
                else:
                    safe_margin = attendance_percentage - threshold
                    if total_expected_occurrences > 0:
                        max_additional_skips = int((safe_margin / 100.0) * total_expected_occurrences)
                    else:
                        max_additional_skips = 0
                    st.success(f"✅ Safe! You can skip {max_additional_skips} more classes safely (while staying above {threshold}%).")
                
                # Get attendance records for display
                attendance_records = db.query(Attendance).filter(
                    Attendance.course_id == course.id,
                    Attendance.user_id == user_id
                ).order_by(Attendance.date.desc()).limit(10).all()
                
                if attendance_records:
                    st.markdown("### Recent Attendance Records")
                    for record in attendance_records:
                        status = "✅ Present" if record.present else "❌ Absent"
                        card(
                            f"{record.date.strftime('%Y-%m-%d')} - {status}",
                            record.notes or "No notes"
                        )
                
                # Add new record
                with st.expander("➕ Mark Attendance"):
                    record_date = st.date_input("Date", value=date.today())
                    present = st.checkbox("Present", value=True)
                    notes = st.text_area("Notes (optional)")
                    
                    if st.button("Save"):
                        # Check if record exists
                        existing = db.query(Attendance).filter(
                            Attendance.course_id == course.id,
                            Attendance.date == record_date
                        ).first()
                        
                        if existing:
                            existing.present = present
                            existing.notes = notes
                        else:
                            attendance = Attendance(
                                user_id=user_id,
                                course_id=course.id,
                                date=record_date,
                                present=present,
                                notes=notes
                            )
                            db.add(attendance)
                        db.commit()
                        st.success("Attendance recorded!")
                        st.rerun()
        
        with tabs[1]:
            st.markdown("### Grade Tracker")
            
            # Format course options with code if available
            course_options_grade = [f"{c.name} ({c.code})" if c.code else c.name for c in courses]
            selected_course_display_grade = st.selectbox(
                "Select Course for Grades",
                course_options_grade,
                key="grade_course",
                help="Choose a course to track grades"
            )
            # Extract course name from display string
            selected_course_name_grade = selected_course_display_grade.split(" (")[0] if " (" in selected_course_display_grade else selected_course_display_grade
            course = next((c for c in courses if c.name == selected_course_name_grade), None)
            
            if course:
                grades = db.query(Grade).filter(
                    Grade.course_id == course.id,
                    Grade.user_id == user_id
                ).order_by(Grade.exam_date.desc()).all()
                
                if grades:
                    # Calculate current grade
                    grade_dicts = [
                        {'grade': g.grade, 'max_grade': g.max_grade, 'weight': g.weight}
                        for g in grades
                    ]
                    current_grade = calculate_current_grade(grade_dicts)
                    
                    st.metric("Current Grade", f"{current_grade:.1f}%")
                    
                    # Grade prediction
                    st.markdown("### Grade Prediction")
                    target_grade = st.number_input("Target Grade (%)", min_value=0.0, max_value=100.0, value=85.0)
                    completed_weight = st.slider("Completed Weight", 0.0, 1.0, 0.6)
                    remaining_weight = 1.0 - completed_weight
                    
                    if remaining_weight > 0:
                        needed = predict_grade_needed(
                            current_grade,
                            target_grade,
                            completed_weight,
                            remaining_weight
                        )
                        st.info(f"📊 You need **{needed:.1f}%** in remaining assignments to achieve {target_grade}%")
                    
                    # Grade list
                    st.markdown("### Grade History")
                    for grade in grades:
                        percentage = (grade.grade / grade.max_grade * 100) if grade.max_grade > 0 else 0
                        card(
                            f"{grade.assignment_name or 'Assignment'} - {percentage:.1f}%",
                            f"""
                            Score: {grade.grade}/{grade.max_grade}<br>
                            Weight: {grade.weight}<br>
                            Date: {grade.exam_date.strftime('%Y-%m-%d') if grade.exam_date else 'N/A'}
                            """
                        )
                else:
                    st.info("No grades recorded yet.")
                
                # Add new grade
                with st.expander("➕ Add Grade"):
                    assignment_name = st.text_input("Assignment/Exam Name")
                    grade_value = st.number_input("Grade", min_value=0.0)
                    max_grade = st.number_input("Max Grade", min_value=1.0, value=100.0)
                    weight = st.number_input("Weight", min_value=0.0, max_value=1.0, value=0.1)
                    exam_date = st.date_input("Date")
                    
                    if st.button("Add Grade"):
                        grade = Grade(
                            user_id=user_id,
                            course_id=course.id,
                            assignment_name=assignment_name,
                            grade=grade_value,
                            max_grade=max_grade,
                            weight=weight,
                            exam_date=exam_date
                        )
                        db.add(grade)
                        db.commit()
                        st.success("Grade added!")
                        st.rerun()
    
    finally:
        db.close()

