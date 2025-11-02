"""ZenOS - Main Streamlit Application"""

import streamlit as st
from src.components.layout import setup_custom_layout, create_custom_sidebar
from src.database.database import init_db, get_db_session
from src.database.models import User
from src.services.gemini_service import GeminiService

# Initialize app
setup_custom_layout()

# Initialize database
init_db()

# Initialize session state
if 'gemini_service' not in st.session_state:
    st.session_state.gemini_service = GeminiService()

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if 'api_key_set' not in st.session_state:
    st.session_state.api_key_set = False


def get_or_create_user():
    """Get or create default user"""
    db = get_db_session()
    try:
        user = db.query(User).first()
        if not user:
            user = User(name="Student", email="student@example.com")
            db.add(user)
            db.commit()
            db.refresh(user)

        # If an API key was previously stored in the user's settings, load it
        try:
            api_key = None
            if hasattr(user, 'settings') and isinstance(user.settings, dict):
                api_key = user.settings.get('gemini_api_key')

            if api_key:
                # Ensure gemini_service exists in session and configure it
                if 'gemini_service' not in st.session_state:
                    st.session_state.gemini_service = GeminiService()
                try:
                    st.session_state.gemini_service.set_api_key(api_key)
                    st.session_state.api_key_set = True
                except Exception:
                    # If setting the API key fails, leave api_key_set as-is (False)
                    pass
        except Exception:
            # Defensive: if the DB user/settings are malformed, ignore and continue
            pass

        return user.id
    finally:
        db.close()


def main():
    """Main application"""
    # Sidebar navigation
    sidebar = create_custom_sidebar()
    
    # API Key input
    if not st.session_state.api_key_set:
        with sidebar:
            st.markdown("### 🔑 Setup")
            api_key = st.text_input(
                "Enter Gemini API Key",
                type="password",
                help="Get your API key from https://makersuite.google.com/app/apikey"
            )
            if api_key:
                try:
                    # Try to initialize the gemini service with the provided key
                    st.session_state.gemini_service.set_api_key(api_key)

                    # Persist the API key to the single user's settings so it survives restarts
                    db = get_db_session()
                    try:
                        user = db.query(User).filter(User.id == st.session_state.user_id).first()
                        if user:
                            settings = user.settings or {}
                            settings['gemini_api_key'] = api_key
                            user.settings = settings
                            db.add(user)
                            db.commit()
                    finally:
                        db.close()

                    st.session_state.api_key_set = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Invalid API key: {str(e)}")
    
    # Get user ID
    if st.session_state.user_id is None:
        st.session_state.user_id = get_or_create_user()
    
    # Navigation
    page = None
    if st.session_state.api_key_set:
        with sidebar:
            st.markdown("### Navigation")
            page = st.radio(
                "Choose a page",
                [
                    "🏠 Dashboard",
                    "🚀 Copilot",
                    "📖 Study Session",
                    "✅ Attendance",
                    "💬 Research Coach",
                    "🎴 Flashcards",
                    "🧘 Wellness",
                    "📊 Focus Analytics",
                    "📋 Syllabus Upload"
                ],
                label_visibility="collapsed"
            )
            
            st.markdown("---")
            st.markdown("### Settings")
            if st.button("🔑 Change API Key"):
                st.session_state.api_key_set = False
                st.rerun()
    
    # Route to appropriate page
    if not st.session_state.api_key_set:
        st.title("Welcome to ZenOS")
        st.markdown("""
        ### Get Started
        
        Please enter your Gemini API key in the sidebar to begin.
        
        **Getting a Gemini API Key:**
        1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Sign in with your Google account
        3. Create a new API key
        4. Paste it in the sidebar
        """)
        return
    
    # Page routing
    if not page:
        return
    
    if page == "🏠 Dashboard":
        from src.components.dashboard import render_dashboard
        render_dashboard()
    elif page == "🚀 Copilot":
        from src.components.copilot import render_copilot
        render_copilot()
    elif page == "📖 Study Session":
        from src.components.study_session import render_study_session
        render_study_session()
    elif page == "✅ Attendance":
        from src.components.attendance import render_attendance
        render_attendance()
    elif page == "💬 Research Coach":
        from src.components.research_coach import render_research_coach
        render_research_coach()
    elif page == "🎴 Flashcards":
        from src.components.flashcards import render_flashcards
        render_flashcards()
    elif page == "🧘 Wellness":
        from src.components.wellness import render_wellness
        render_wellness()
    elif page == "📊 Focus Analytics":
        from src.components.focus_analytics import render_focus_analytics
        render_focus_analytics()
    elif page == "📋 Syllabus Upload":
        from src.components.syllabus_upload import render_syllabus_upload
        render_syllabus_upload()


if __name__ == "__main__":
    main()

