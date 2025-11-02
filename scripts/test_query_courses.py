"""Quick test: query courses for user_id=1 using the app's DB session."""
from src.database.database import get_db_session
from src.database.models import Course


def main():
    db = get_db_session()
    try:
        courses = db.query(Course).filter(Course.user_id == 1).all()
        print(f"Found {len(courses)} courses for user_id=1")
        for c in courses:
            print(c.id, c.name, c.start_date, c.end_date)
    finally:
        db.close()

if __name__ == '__main__':
    main()
