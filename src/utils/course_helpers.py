"""Helper functions for course management"""

from src.database.database import get_db_session
from src.database.models import Course, Syllabus, Timetable
from typing import List, Optional, Dict, Any
from datetime import date, time, timedelta


def get_user_courses(user_id: int) -> List[Course]:
    """Get all courses for a user"""
    db = get_db_session()
    try:
        courses = db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()
        return courses
    finally:
        db.close()


def get_course_by_id(user_id: int, course_id: int) -> Optional[Course]:
    """Get a specific course by ID"""
    db = get_db_session()
    try:
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.user_id == user_id
        ).first()
        return course
    finally:
        db.close()


def get_course_by_name(user_id: int, course_name: str) -> Optional[Course]:
    """Get a specific course by name"""
    db = get_db_session()
    try:
        course = db.query(Course).filter(
            Course.name == course_name,
            Course.user_id == user_id
        ).first()
        return course
    finally:
        db.close()


def format_course_display_name(course: Course) -> str:
    """Format course name for display"""
    if course.code:
        return f"{course.name} ({course.code})"
    return course.name


def get_course_background(course: Course, user_id: int) -> Dict[str, Any]:
    """
    Get comprehensive course background information from syllabus
    
    Returns:
        Dictionary with course metadata: topics, objectives, outcomes, textbooks, etc.
    """
    db = get_db_session()
    try:
        # Find syllabus with course data
        syllabus = db.query(Syllabus).filter(
            Syllabus.user_id == user_id
        ).order_by(Syllabus.uploaded_at.desc()).first()
        
        if syllabus and syllabus.parsed_data:
            # Find this course in the parsed data
            course_in_data = next(
                (c for c in syllabus.parsed_data.get('courses', []) if c.get('name') == course.name),
                {}
            )
            
            return {
                'name': course.name,
                'code': course.code or '',
                'instructor': course.instructor or '',
                'credits': course.credits or 0,
                'topics': course_in_data.get('topics', []),
                'objectives': course_in_data.get('objectives', []),
                'outcomes': course_in_data.get('outcomes', []),
                'textbooks': course_in_data.get('textbooks', [])
            }
        
        # Fallback to basic course info if no syllabus data
        return {
            'name': course.name,
            'code': course.code or '',
            'instructor': course.instructor or '',
            'credits': course.credits or 0,
            'topics': [],
            'objectives': [],
            'outcomes': [],
            'textbooks': []
        }
    finally:
        db.close()


def create_default_timetable_entries(course: Course, user_id: int, default_time: time = time(9, 0)) -> None:
    """
    Create default Monday-Friday timetable entries for a course
    
    Args:
        course: Course object
        user_id: User ID
        default_time: Default class start time (default: 9:00 AM)
    """
    db = get_db_session()
    try:
        # Check if timetable entries already exist
        existing_entries = db.query(Timetable).filter(
            Timetable.course_id == course.id,
            Timetable.user_id == user_id
        ).first()
        
        if existing_entries:
            return  # Don't create if entries already exist
        
        # Monday-Friday (0-4)
        for day_of_week in range(5):  # 0=Monday, 4=Friday
            # Default: 1-hour class
            start_time = default_time
            end_time = time(default_time.hour + 1, default_time.minute)
            
            timetable_entry = Timetable(
                user_id=user_id,
                course_id=course.id,
                title=f"{course.name} Class",
                type="class",
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                is_recurring=True
            )
            db.add(timetable_entry)
        
        db.commit()
    finally:
        db.close()


def calculate_total_classes_for_course(course: Course) -> int:
    """
    Calculate total number of classes for a course based on start/end dates
    Assumes Monday-Friday classes
    
    Args:
        course: Course object with start_date and end_date
        
    Returns:
        Total number of classes
    """
    if not course.start_date or not course.end_date:
        return 0
    
    current_date = course.start_date
    class_count = 0
    
    while current_date <= course.end_date:
        # Monday = 0, Friday = 4
        if current_date.weekday() < 5:  # Monday to Friday
            class_count += 1
        current_date += timedelta(days=1)
    
    return class_count
