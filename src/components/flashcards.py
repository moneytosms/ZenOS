"""Flashcards Component with Spaced Repetition"""

import streamlit as st
from datetime import date
from src.database.database import get_db_session
from src.database.models import Flashcard, Course
from src.services.spaced_repetition import (
    calculate_next_review,
    initialize_card,
    get_cards_due_today
)
from src.services.gemini_service import GeminiService
from src.components.ui.card import card


def render_flashcards():
    """Render flashcards interface"""
    st.title("🎴 Flashcards")
    st.markdown("Review flashcards using spaced repetition for optimal learning.")
    
    db = get_db_session()
    user_id = st.session_state.user_id
    gemini_service: GeminiService = st.session_state.gemini_service
    
    try:
        courses = db.query(Course).filter(Course.user_id == user_id).order_by(Course.name).all()
        
        # Show message if no courses (but still allow creating general flashcards)
        if not courses:
            st.info("💡 **No courses yet.** You can still create flashcards! Add courses in the **📋 Syllabus Upload** page to organize flashcards by course.")
        
        tabs = st.tabs(["🔄 Review", "➕ Create", "📚 All Cards"])
        
        with tabs[0]:
            # Get cards due for review
            all_cards = db.query(Flashcard).filter(Flashcard.user_id == user_id).all()
            cards_due = get_cards_due_today(all_cards)
            
            if not cards_due:
                st.success("🎉 No cards due for review! Great job staying on top of your studies.")
                
                # Show next review date
                upcoming_cards = [c for c in all_cards if c.next_review_date > date.today()]
                if upcoming_cards:
                    next_review = min(c.next_review_date for c in upcoming_cards)
                    st.info(f"Next review scheduled for: {next_review.strftime('%Y-%m-%d')}")
            else:
                st.markdown(f"### {len(cards_due)} cards due today")
                
                if 'current_card_index' not in st.session_state:
                    st.session_state.current_card_index = 0
                if 'card_flipped' not in st.session_state:
                    st.session_state.card_flipped = False
                
                if st.session_state.current_card_index < len(cards_due):
                    current_card = cards_due[st.session_state.current_card_index]
                    
                    if not st.session_state.card_flipped:
                        # Show front
                        card("Front", f"<h2 style='text-align: center;'>{current_card.front}</h2>")
                        if st.button("🔍 Show Answer", type="primary"):
                            st.session_state.card_flipped = True
                            st.rerun()
                    else:
                        # Show back
                        card("Back", f"<h2 style='text-align: center;'>{current_card.back}</h2>")
                        
                        st.markdown("### How well did you know this?")
                        col1, col2, col3, col4, col5 = st.columns(5)
                        
                        quality = None
                        with col1:
                            if st.button("❌", key="q0"):
                                quality = 0
                        with col2:
                            if st.button("🟡", key="q1"):
                                quality = 1
                        with col3:
                            if st.button("🟠", key="q2"):
                                quality = 2
                        with col4:
                            if st.button("🟢", key="q3"):
                                quality = 3
                        with col5:
                            if st.button("✅", key="q4"):
                                quality = 4
                        
                        if quality is not None:
                            # Update card using SM-2
                            new_ef, new_interval, new_reps, next_date = calculate_next_review(
                                quality,
                                current_card.easiness_factor,
                                current_card.interval_days,
                                current_card.repetitions
                            )
                            
                            current_card.easiness_factor = new_ef
                            current_card.interval_days = new_interval
                            current_card.repetitions = new_reps
                            current_card.next_review_date = next_date
                            current_card.last_reviewed = date.today()
                            
                            db.commit()
                            
                            st.session_state.current_card_index += 1
                            st.session_state.card_flipped = False
                            st.rerun()
                else:
                    st.balloons()
                    st.success("All cards reviewed for today!")
                    st.session_state.current_card_index = 0
                    if st.button("🔄 Review Again"):
                        st.rerun()
        
        with tabs[1]:
            st.markdown("### Create New Flashcard")
            
            col1, col2 = st.columns(2)
            with col1:
                # Format course options
                course_options = ["None"] + [f"{c.name} ({c.code})" if c.code else c.name for c in courses]
                selected_course_display = st.selectbox(
                    "Course",
                    course_options,
                    help="Organize this flashcard under a course (optional)"
                )
                
                # Extract course from selection
                selected_course_name = None
                if selected_course_display != "None":
                    selected_course_name = selected_course_display.split(" (")[0] if " (" in selected_course_display else selected_course_display
            
            front = st.text_area("Front (Question/Prompt)")
            back = st.text_area("Back (Answer/Explanation)")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Card"):
                    if front and back:
                        course_id = None
                        if selected_course_name:
                            course = next((c for c in courses if c.name == selected_course_name), None)
                            if course:
                                course_id = course.id
                        
                        ef, interval, reps, next_date = initialize_card()
                        
                        flashcard = Flashcard(
                            user_id=user_id,
                            course_id=course_id,
                            front=front,
                            back=back,
                            easiness_factor=ef,
                            interval_days=interval,
                            repetitions=reps,
                            next_review_date=next_date
                        )
                        db.add(flashcard)
                        db.commit()
                        st.success("Card created!")
                    else:
                        st.warning("Please fill in both front and back.")
            
            with col2:
                if st.button("🤖 Generate from Text"):
                    text_input = st.text_area("Enter text to generate cards from", key="gen_text")
                    if text_input:
                        with st.spinner("Generating flashcards..."):
                            cards = gemini_service.create_flashcards_from_text(text_input, num_cards=5)
                            if cards:
                                st.success(f"Generated {len(cards)} cards!")
                                for i, card_data in enumerate(cards, 1):
                                    with st.expander(f"Card {i}"):
                                        st.markdown(f"**Front:** {card_data.get('front', '')}")
                                        st.markdown(f"**Back:** {card_data.get('back', '')}")
                                        if st.button(f"Save Card {i}", key=f"save_{i}"):
                                            course_id = None
                                            if selected_course != "None":
                                                course = next((c for c in courses if c.name == selected_course), None)
                                                if course:
                                                    course_id = course.id
                                            
                                            ef, interval, reps, next_date = initialize_card()
                                            flashcard = Flashcard(
                                                user_id=user_id,
                                                course_id=course_id,
                                                front=card_data.get('front', ''),
                                                back=card_data.get('back', ''),
                                                easiness_factor=ef,
                                                interval_days=interval,
                                                repetitions=reps,
                                                next_review_date=next_date
                                            )
                                            db.add(flashcard)
                                            db.commit()
                                            st.success(f"Card {i} saved!")
        
        with tabs[2]:
            st.markdown("### All Flashcards")
            
            # Format course options for filter
            filter_course_options = ["All"] + [f"{c.name} ({c.code})" if c.code else c.name for c in courses]
            filter_course_display = st.selectbox(
                "Filter by Course",
                filter_course_options,
                key="filter_course",
                help="Filter flashcards by course"
            )
            
            query = db.query(Flashcard).filter(Flashcard.user_id == user_id)
            if filter_course_display != "All":
                filter_course_name = filter_course_display.split(" (")[0] if " (" in filter_course_display else filter_course_display
                course = next((c for c in courses if c.name == filter_course_name), None)
                if course:
                    query = query.filter(Flashcard.course_id == course.id)
            
            all_cards = query.all()
            
            st.metric("Total Cards", len(all_cards))
            due_today = len(get_cards_due_today(all_cards))
            st.metric("Due Today", due_today)
            
            for card_obj in all_cards:
                course_name = card_obj.course.name if card_obj.course else "General"
                card(
                    f"{course_name} - Card #{card_obj.id}",
                    f"""
                    <strong>Front:</strong> {card_obj.front[:100]}...<br>
                    <strong>Back:</strong> {card_obj.back[:100]}...<br>
                    <small>Next Review: {card_obj.next_review_date.strftime('%Y-%m-%d')}</small><br>
                    <small>Repetitions: {card_obj.repetitions} | Interval: {card_obj.interval_days} days</small>
                    """
                )
    
    finally:
        db.close()

