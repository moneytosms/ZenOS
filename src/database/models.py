"""SQLAlchemy database models for ZenOS"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Date, Time
)
from datetime import date as date_type
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User profile and settings"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    settings = Column(JSON, default=dict)  # Store theme, preferences, etc.

    # Relationships
    courses = relationship("Course", back_populates="user")
    study_sessions = relationship("StudySession", back_populates="user")
    flashcards = relationship("Flashcard", back_populates="user")
    attendance_records = relationship("Attendance", back_populates="user")
    grades = relationship("Grade", back_populates="user")
    focus_sessions = relationship("FocusSession", back_populates="user")
    wellness_logs = relationship("WellnessLog", back_populates="user")
    research_conversations = relationship("ResearchConversation", back_populates="user")


class Syllabus(Base):
    """Syllabus content and metadata"""
    __tablename__ = "syllabus"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255))
    content = Column(Text)  # Full text content
    file_path = Column(String(500))  # Path to uploaded PDF if any
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    parsed_data = Column(JSON)  # Structured data extracted by Gemini


class Course(Base):
    """Course information"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50))
    instructor = Column(String(255))
    credits = Column(Integer, default=0)
    attendance_required = Column(Boolean, default=True)
    attendance_threshold = Column(Float, default=75.0)  # Minimum % required
    start_date = Column(Date)  # Default: Aug 1, 2025 (set in application code)
    end_date = Column(Date)  # Default: Nov 14, 2025 (set in application code)
    skipped_classes = Column(Integer, default=0)  # Number of classes skipped
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="courses")
    timetable_entries = relationship("Timetable", back_populates="course")
    tasks = relationship("Task", back_populates="course")
    attendance_records = relationship("Attendance", back_populates="course")
    grades = relationship("Grade", back_populates="course")
    flashcards = relationship("Flashcard", back_populates="course")
    study_sessions = relationship("StudySession", back_populates="course")


class Timetable(Base):
    """Class schedules and study blocks"""
    __tablename__ = "timetable"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(String(50))  # 'class', 'study', 'break', 'meal', etc.
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    location = Column(String(255))
    topic = Column(String(500))  # What to study/learn
    is_recurring = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="timetable_entries")


class Task(Base):
    """Assignments, deadlines, and tasks"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    status = Column(String(20), default="pending")  # pending, in_progress, completed, overdue
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    course = relationship("Course", back_populates="tasks")


class StudySession(Base):
    """Study session history with confidence ratings"""
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    topic = Column(String(500))
    duration_minutes = Column(Integer, default=25)  # Pomodoro duration
    confidence_rating = Column(Integer)  # 1-5 scale
    notes = Column(Text)
    completed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="study_sessions")
    course = relationship("Course", back_populates="study_sessions")


class Flashcard(Base):
    """Flashcard content + SM-2 metadata"""
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    # SM-2 algorithm fields
    easiness_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    next_review_date = Column(Date, default=datetime.utcnow)
    last_reviewed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="flashcards")
    course = relationship("Course", back_populates="flashcards")


class Attendance(Base):
    """Attendance records per course"""
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    date = Column(Date, nullable=False)
    present = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="attendance_records")
    course = relationship("Course", back_populates="attendance_records")


class Grade(Base):
    """Grade entries per course/assignment"""
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    assignment_name = Column(String(255))
    grade = Column(Float, nullable=False)  # Score or percentage
    max_grade = Column(Float, default=100.0)
    weight = Column(Float, default=1.0)  # Weight in final grade calculation
    exam_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="grades")
    course = relationship("Course", back_populates="grades")


class FocusSession(Base):
    """Pomodoro/focus tracking"""
    __tablename__ = "focus_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer)
    session_type = Column(String(50), default="pomodoro")  # pomodoro, custom, break
    topic = Column(String(500))
    distractions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="focus_sessions")


class WellnessLog(Base):
    """Reflection and wellness entries"""
    __tablename__ = "wellness_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=datetime.utcnow)
    mood_rating = Column(Integer)  # 1-5 scale
    energy_level = Column(Integer)  # 1-5 scale
    reflection = Column(Text)
    gratitude = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="wellness_logs")


class ResearchConversation(Base):
    """Research coach chat history"""
    __tablename__ = "research_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255))
    messages = Column(JSON)  # Store conversation history as JSON
    outline = Column(Text)  # Generated outline
    draft = Column(Text)  # Generated draft
    exported_formats = Column(JSON, default=list)  # List of exported formats
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="research_conversations")

