"""Syllabus upload and parsing component with course management"""

import streamlit as st
from src.services.pdf_service import extract_text_from_pdf
from src.services.gemini_service import GeminiService
from src.database.database import get_db_session
from src.database.models import Syllabus, Course, Task, Timetable
from datetime import datetime, date, time
from src.components.ui.card import card
from src.utils.course_helpers import create_default_timetable_entries


def render_syllabus_upload():
    """Render syllabus upload interface with course management"""
    st.title("📋 Syllabus Upload & Course Management")
    
    # Get services
    gemini_service: GeminiService = st.session_state.gemini_service
    db = get_db_session()
    user_id = st.session_state.user_id
    
    # Initialize session state for PDF text
    if 'extracted_syllabus_text' not in st.session_state:
        st.session_state.extracted_syllabus_text = ""
    
    try:
        # Get existing courses
        existing_courses = db.query(Course).filter(Course.user_id == user_id).all()
        
        # Show existing courses section
        if existing_courses:
            st.markdown("### 📚 Your Courses")
            
            for course in existing_courses:
                # Get course metadata from syllabus if available
                syllabus = db.query(Syllabus).filter(
                    Syllabus.user_id == user_id
                ).order_by(Syllabus.uploaded_at.desc()).first()
                
                course_metadata = {}
                if syllabus and syllabus.parsed_data:
                    course_in_data = next(
                        (c for c in syllabus.parsed_data.get('courses', []) if c.get('name') == course.name),
                        {}
                    )
                    course_metadata = {
                        'topics': course_in_data.get('topics', []),
                        'objectives': course_in_data.get('objectives', []),
                        'outcomes': course_in_data.get('outcomes', []),
                        'textbooks': course_in_data.get('textbooks', [])
                    }
                
                course_title = f"{course.name} ({course.code})" if course.code else course.name
                with st.expander(course_title, expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"""
                        **Basic Information:**
                        - **Instructor:** {course.instructor or 'Not specified'}
                        - **Credits:** {course.credits}
                        - **Attendance Required:** {'Yes' if course.attendance_required else 'No'}
                        - **Attendance Threshold:** {course.attendance_threshold}%
                        """)
                        
                        # Show course metadata if available
                        if course_metadata.get('topics'):
                            st.markdown("---")
                            st.markdown(f"**📚 Syllabus Topics ({len(course_metadata['topics'])}):**")
                            with st.container():
                                for i, topic in enumerate(course_metadata['topics'][:10], 1):
                                    st.markdown(f"- {topic}")
                                if len(course_metadata['topics']) > 10:
                                    with st.expander(f"View all {len(course_metadata['topics'])} topics"):
                                        for i, topic in enumerate(course_metadata['topics'], 1):
                                            st.markdown(f"{i}. {topic}")
                        
                        if course_metadata.get('objectives'):
                            st.markdown("---")
                            st.markdown(f"**🎯 Course Objectives ({len(course_metadata['objectives'])}):**")
                            for i, obj in enumerate(course_metadata['objectives'], 1):
                                st.markdown(f"{i}. {obj}")
                        
                        if course_metadata.get('outcomes'):
                            st.markdown("---")
                            st.markdown(f"**✅ Course Outcomes ({len(course_metadata['outcomes'])}):**")
                            for i, outcome in enumerate(course_metadata['outcomes'], 1):
                                st.markdown(f"{i}. {outcome}")
                        
                        if course_metadata.get('textbooks'):
                            st.markdown("---")
                            st.markdown(f"**📖 Textbooks & References ({len(course_metadata['textbooks'])}):**")
                            for i, book in enumerate(course_metadata['textbooks'], 1):
                                st.markdown(f"{i}. {book}")
                    
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_{course.id}", type="primary", use_container_width=True):
                            st.session_state[f"editing_course_{course.id}"] = True
                            st.rerun()
                        
                        if st.button("🗑️ Delete", key=f"delete_{course.id}", type="secondary", use_container_width=True):
                            # Delete related records first
                            db.query(Task).filter(Task.course_id == course.id).delete()
                            db.query(Timetable).filter(Timetable.course_id == course.id).delete()
                            db.query(Course).filter(Course.id == course.id).delete()
                            db.commit()
                            st.success(f"Course '{course.name}' deleted!")
                            st.rerun()
                
                # Edit course form
                if st.session_state.get(f"editing_course_{course.id}", False):
                    st.markdown("---")
                    with st.form(f"edit_form_{course.id}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_name = st.text_input("Course Name", value=course.name, key=f"edit_name_{course.id}")
                            edit_code = st.text_input("Course Code", value=course.code or "", key=f"edit_code_{course.id}")
                            edit_instructor = st.text_input("Instructor", value=course.instructor or "", key=f"edit_instructor_{course.id}")
                        
                        with col2:
                            edit_credits = st.number_input("Credits", value=course.credits or 0, min_value=0, key=f"edit_credits_{course.id}")
                            edit_start_date = st.date_input("Start Date", value=course.start_date or date(2025, 8, 1), key=f"edit_start_{course.id}")
                            edit_end_date = st.date_input("End Date", value=course.end_date or date(2025, 11, 14), key=f"edit_end_{course.id}")
                        
                        edit_attendance_required = st.checkbox("Attendance Required", value=course.attendance_required, key=f"edit_attendance_req_{course.id}")
                        edit_attendance_threshold = st.slider("Attendance Threshold (%)", 0, 100, int(course.attendance_threshold or 75), key=f"edit_threshold_{course.id}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save Changes", type="primary"):
                                course.name = edit_name
                                course.code = edit_code or None
                                course.instructor = edit_instructor or None
                                course.credits = edit_credits
                                course.start_date = edit_start_date
                                course.end_date = edit_end_date
                                course.attendance_required = edit_attendance_required
                                course.attendance_threshold = float(edit_attendance_threshold)
                                db.commit()
                                st.session_state[f"editing_course_{course.id}"] = False
                                st.success("Course updated!")
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[f"editing_course_{course.id}"] = False
                                st.rerun()
        
        st.markdown("---")
        
        # Upload section
        st.markdown("### 📤 Upload Syllabus")
        
        tab1, tab2 = st.tabs(["📄 Upload PDF", "📝 Paste Text"])
        
        with tab1:
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type=['pdf'],
                help="Upload your course syllabus as a PDF",
                key="pdf_uploader"
            )
            
            if uploaded_file:
                # Extract text immediately when file is uploaded
                with st.spinner("Extracting text from PDF..."):
                    try:
                        extracted_text = extract_text_from_pdf(uploaded_file)
                        st.session_state.extracted_syllabus_text = extracted_text
                        st.success(f"✅ PDF extracted successfully! ({len(extracted_text)} characters)")
                        
                        # Show preview
                        with st.expander("Preview Extracted Text"):
                            st.text_area(
                                "Extracted Text",
                                extracted_text[:2000] + "..." if len(extracted_text) > 2000 else extracted_text,
                                height=200,
                                disabled=True,
                                key="preview_pdf"
                            )
                    except Exception as e:
                        st.error(f"❌ Error extracting PDF: {str(e)}")
                        st.session_state.extracted_syllabus_text = ""
        
        with tab2:
            manual_text = st.text_area(
                "Paste your syllabus text here",
                value=st.session_state.extracted_syllabus_text if not uploaded_file else "",
                height=300,
                help="Copy and paste the content of your syllabus",
                key="manual_text_input"
            )
            
            if manual_text:
                st.session_state.extracted_syllabus_text = manual_text
        
        # Parse button - only show if we have text
        if st.session_state.extracted_syllabus_text:
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.info("💡 Ready to parse! Click the button below to extract courses from your syllabus.")
            
            with col2:
                if st.button("🚀 Parse Syllabus", type="primary", use_container_width=True):
                    if not gemini_service.is_configured():
                        st.error("❌ Please configure your Gemini API key first in Settings.")
                        return
                    
                    with st.spinner("🤖 Analyzing syllabus with AI..."):
                        try:
                            # Parse with Gemini
                            parsed_data = gemini_service.parse_syllabus(st.session_state.extracted_syllabus_text)
                            
                            if parsed_data and parsed_data.get('courses'):
                                # Save syllabus
                                syllabus = Syllabus(
                                    user_id=user_id,
                                    title="Uploaded Syllabus",
                                    content=st.session_state.extracted_syllabus_text[:50000],  # Limit size
                                    parsed_data=parsed_data
                                )
                                db.add(syllabus)
                                db.commit()
                                
                                # Create courses
                                created_courses = []
                                for course_data in parsed_data.get('courses', []):
                                    course_name = course_data.get('name', 'Unknown Course')
                                    
                                    # Check if course already exists
                                    existing = db.query(Course).filter(
                                        Course.user_id == user_id,
                                        Course.name == course_name
                                    ).first()
                                    
                                    # Store additional course metadata in parsed_data
                                    course_metadata = {
                                        'topics': course_data.get('topics', []),
                                        'objectives': course_data.get('objectives', []),
                                        'outcomes': course_data.get('outcomes', []),
                                        'textbooks': course_data.get('textbooks', [])
                                    }
                                    
                                    if existing:
                                        # Update existing course - only update if AI provided values, keep existing if blank
                                        if course_data.get('code'):
                                            existing.code = course_data.get('code')
                                        if course_data.get('instructor'):
                                            existing.instructor = course_data.get('instructor')
                                        if course_data.get('credits'):
                                            existing.credits = course_data.get('credits', 0) or 0
                                        existing.attendance_required = course_data.get('attendance_required', existing.attendance_required if 'attendance_required' not in course_data else True)
                                        existing.attendance_threshold = course_data.get('attendance_threshold', existing.attendance_threshold if 'attendance_threshold' not in course_data else 75.0)
                                        
                                        # Update parsed_data with metadata
                                        if not existing.parsed_data:
                                            existing.parsed_data = {}
                                        existing.parsed_data.update(course_metadata)
                                        
                                        db.commit()
                                        db.refresh(existing)
                                        created_courses.append(existing)
                                    else:
                                        # Create new course - allow blank values, use defaults
                                        course = Course(
                                            user_id=user_id,
                                            name=course_name,
                                            code=course_data.get('code') or '',  # Allow blank
                                            instructor=course_data.get('instructor') or '',  # Allow blank
                                            credits=course_data.get('credits') or 0 if course_data.get('credits') else 0,  # Default to 0 if not provided
                                            attendance_required=course_data.get('attendance_required', True),
                                            attendance_threshold=course_data.get('attendance_threshold', 75.0),
                                            start_date=date(2025, 8, 1),  # Default start date
                                            end_date=date(2025, 11, 14),  # Default end date
                                            skipped_classes=0
                                        )
                                        db.add(course)
                                        db.commit()
                                        db.refresh(course)
                                        
                                        # Create default Monday-Friday timetable entries
                                        create_default_timetable_entries(course, user_id)
                                        
                                        created_courses.append(course)
                                    
                                    # Create tasks for assignments
                                    for assignment in course_data.get('assignments', []):
                                        due_date = None
                                        if assignment.get('due_date'):
                                            try:
                                                due_date = datetime.strptime(assignment['due_date'], "%Y-%m-%d")
                                            except:
                                                try:
                                                    # Try alternative format
                                                    due_date = datetime.strptime(assignment['due_date'], "%Y/%m/%d")
                                                except:
                                                    pass
                                        
                                        # Check if task already exists
                                        existing_task = db.query(Task).filter(
                                            Task.user_id == user_id,
                                            Task.course_id == course.id if 'course' in locals() else existing.id,
                                            Task.title == assignment.get('title', 'Assignment')
                                        ).first()
                                        
                                        if not existing_task:
                                            task = Task(
                                                user_id=user_id,
                                                course_id=course.id if 'course' in locals() else existing.id,
                                                title=assignment.get('title', 'Assignment'),
                                                due_date=due_date,
                                                priority='high' if due_date and due_date.date() < datetime.now().date() else 'medium'
                                            )
                                            db.add(task)
                                    
                                    # Create tasks for exams
                                    for exam in course_data.get('exams', []):
                                        exam_date = None
                                        if exam.get('date'):
                                            try:
                                                exam_date = datetime.strptime(exam['date'], "%Y-%m-%d")
                                            except:
                                                try:
                                                    exam_date = datetime.strptime(exam['date'], "%Y/%m/%d")
                                                except:
                                                    pass
                                        
                                        existing_task = db.query(Task).filter(
                                            Task.user_id == user_id,
                                            Task.course_id == course.id if 'course' in locals() else existing.id,
                                            Task.title == exam.get('title', 'Exam')
                                        ).first()
                                        
                                        if not existing_task:
                                            task = Task(
                                                user_id=user_id,
                                                course_id=course.id if 'course' in locals() else existing.id,
                                                title=exam.get('title', 'Exam'),
                                                due_date=exam_date,
                                                priority='urgent' if exam_date and exam_date.date() < datetime.now().date() else 'high'
                                            )
                                            db.add(task)
                                
                                db.commit()
                                
                                st.success(f"✅ Successfully parsed syllabus!")
                                st.balloons()
                                
                                # Show created courses with full details
                                st.markdown("### 📋 Extracted Courses")
                                for c in created_courses:
                                    # Get course metadata from parsed data
                                    course_meta = next(
                                        (cd for cd in parsed_data.get('courses', []) if cd.get('name') == c.name),
                                        {}
                                    )
                                    topics = course_meta.get('topics', [])
                                    objectives = course_meta.get('objectives', [])
                                    
                                    details_html = f"""
                                    - <strong>Instructor:</strong> {c.instructor or 'Not specified'}<br>
                                    - <strong>Credits:</strong> {c.credits}<br>
                                    - <strong>Attendance Threshold:</strong> {c.attendance_threshold}%
                                    """
                                    
                                    if topics:
                                        details_html += f"<br>- <strong>Topics:</strong> {len(topics)} topics extracted"
                                    if objectives:
                                        details_html += f"<br>- <strong>Objectives:</strong> {len(objectives)} objectives"
                                    
                                    card(
                                        f"{c.name} ({c.code})" if c.code else c.name,
                                        details_html
                                    )
                                    
                                    # Show topics in expander
                                    if topics:
                                        with st.expander(f"📚 View Topics for {c.name}"):
                                            for i, topic in enumerate(topics[:20], 1):  # Show first 20
                                                st.markdown(f"{i}. {topic}")
                                            if len(topics) > 20:
                                                st.info(f"... and {len(topics) - 20} more topics")
                                
                                st.success("💡 Your courses have been saved! They're now available throughout the app.")
                                st.info("""
                                **Next Steps:**
                                - Go to **📅 Timetable** to schedule your classes
                                - Use **📖 Study Session** to start studying
                                - Track **✅ Attendance** for each course
                                - Create **🎴 Flashcards** organized by course
                                """)
                                
                                # Clear extracted text
                                st.session_state.extracted_syllabus_text = ""
                                st.rerun()
                            else:
                                st.warning("⚠️ Could not extract course information from the syllabus. The AI might not have found clear course structures. You can manually add courses below.")
                                if parsed_data:
                                    st.json(parsed_data)
                                
                        except Exception as e:
                            st.error(f"❌ Error parsing syllabus: {str(e)}")
                            st.exception(e)
        
        # Manual course addition
        st.markdown("---")
        st.markdown("### ➕ Add Course Manually")
        
        with st.expander("Add New Course"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_course_name = st.text_input("Course Name *", key="new_course_name")
                new_course_code = st.text_input("Course Code", key="new_course_code")
                new_instructor = st.text_input("Instructor", key="new_instructor")
            
            with col2:
                new_credits = st.number_input("Credits", min_value=0, max_value=10, value=3, key="new_credits")
                attendance_required = st.checkbox("Attendance Required", value=True, key="attendance_req")
                attendance_threshold = st.slider("Attendance Threshold (%)", 0, 100, 75, key="attendance_thresh")
            
            if st.button("➕ Add Course", type="primary"):
                if new_course_name:
                    # Check if course already exists
                    existing = db.query(Course).filter(
                        Course.user_id == user_id,
                        Course.name == new_course_name
                    ).first()
                    
                    if existing:
                        st.warning(f"Course '{new_course_name}' already exists!")
                    else:
                        course = Course(
                            user_id=user_id,
                            name=new_course_name,
                            code=new_course_code or None,
                            instructor=new_instructor or None,
                            credits=new_credits,
                            attendance_required=attendance_required,
                            attendance_threshold=float(attendance_threshold),
                            start_date=date(2025, 8, 1),
                            end_date=date(2025, 11, 14),
                            skipped_classes=0
                        )
                        db.add(course)
                        db.commit()
                        db.refresh(course)
                        
                        # Create default Monday-Friday timetable entries
                        create_default_timetable_entries(course, user_id)
                        
                        st.success(f"✅ Course '{new_course_name}' added successfully!")
                        st.rerun()
                else:
                    st.error("Please enter a course name.")
    
    finally:
        db.close()
