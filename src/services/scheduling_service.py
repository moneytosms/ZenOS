"""Adaptive timetable and study schedule generation service"""

from datetime import datetime, date, timedelta, time
from typing import List, Dict, Optional, Tuple
from src.database.models import Course, Task, Timetable


def generate_study_schedule(
    courses: List[Course],
    tasks: List[Task],
    available_hours: Dict[int, Tuple[time, time]],  # day_of_week: (start_time, end_time)
    study_sessions_per_day: int = 2,
    session_duration_minutes: int = 120
) -> List[Dict]:
    """
    Generate adaptive study schedule based on courses and tasks
    
    Args:
        courses: List of Course objects
        tasks: List of Task objects
        available_hours: Dict mapping day of week (0-6) to available time slots
        study_sessions_per_day: Number of study blocks per day
        session_duration_minutes: Duration of each study session
        
    Returns:
        List of timetable entries (dictionaries)
    """
    schedule = []
    
    # Sort tasks by priority and due date
    sorted_tasks = sorted(
        tasks,
        key=lambda t: (
            0 if t.priority == 'urgent' else
            1 if t.priority == 'high' else
            2 if t.priority == 'medium' else 3,
            t.due_date or datetime.max
        )
    )
    
    # Calculate total study time needed
    today = date.today()
    tasks_by_course = {}
    for task in sorted_tasks:
        if task.course_id not in tasks_by_course:
            tasks_by_course[task.course_id] = []
        tasks_by_course[task.course_id].append(task)
    
    # Generate study blocks for upcoming week
    current_date = today
    for day_offset in range(7):
        current_date = today + timedelta(days=day_offset)
        day_of_week = current_date.weekday()
        
        if day_of_week not in available_hours:
            continue
        
        start_time, end_time = available_hours[day_of_week]
        
        # Generate study sessions for this day
        for session_num in range(study_sessions_per_day):
            # Calculate session time
            session_start = datetime.combine(current_date, start_time)
            session_start += timedelta(
                minutes=session_num * (session_duration_minutes + 30)  # 30 min break between sessions
            )
            
            if session_start.time() >= end_time:
                break
            
            session_end = session_start + timedelta(minutes=session_duration_minutes)
            
            # Assign task/course to session
            task = None
            course = None
            if sorted_tasks:
                task = sorted_tasks[0]
                course = next((c for c in courses if c.id == task.course_id), None)
            
            schedule.append({
                'title': f"Study: {course.name if course else 'General'}" if task else "Study Session",
                'type': 'study',
                'day_of_week': day_of_week,
                'date': current_date,
                'start_time': session_start.time(),
                'end_time': session_end.time(),
                'topic': task.title if task else None,
                'course_id': course.id if course else None,
                'task_id': task.id if task else None,
            })
            
            if task:
                sorted_tasks.pop(0)
    
    return schedule


def recalculate_schedule_after_miss(
    original_schedule: List[Dict],
    missed_date: date,
    available_hours: Dict[int, Tuple[time, time]]
) -> List[Dict]:
    """
    Recalculate schedule after missing a study session
    
    Args:
        original_schedule: Original schedule entries
        missed_date: Date of missed session
        available_hours: Available time slots
        
    Returns:
        Updated schedule with redistributed sessions
    """
    # Filter out missed session
    updated_schedule = [
        entry for entry in original_schedule
        if entry.get('date') != missed_date
    ]
    
    # Find the missed session's task/course
    missed_entry = next(
        (entry for entry in original_schedule if entry.get('date') == missed_date),
        None
    )
    
    if not missed_entry:
        return updated_schedule
    
    # Redistribute to next available slot
    today = date.today()
    for day_offset in range(1, 14):  # Look ahead 2 weeks
        check_date = today + timedelta(days=day_offset)
        day_of_week = check_date.weekday()
        
        if day_of_week not in available_hours:
            continue
        
        # Check if slot is available
        start_time, end_time = available_hours[day_of_week]
        slot_busy = any(
            entry.get('date') == check_date and
            entry.get('start_time') == start_time
            for entry in updated_schedule
        )
        
        if not slot_busy:
            # Add redistributed session
            updated_schedule.append({
                **missed_entry,
                'date': check_date,
                'day_of_week': day_of_week,
                'start_time': start_time,
            })
            break
    
    return updated_schedule

