"""SM-2 Spaced Repetition Algorithm Implementation"""

from datetime import date, timedelta
from typing import Tuple
from src.utils.constants import SM2_MIN_EASINESS, SM2_DEFAULT_EASINESS


def calculate_next_review(
    quality: int,
    easiness_factor: float,
    interval_days: int,
    repetitions: int
) -> Tuple[float, int, int, date]:
    """
    Calculate next review parameters using SM-2 algorithm
    
    Args:
        quality: User's response quality (0-5 scale, where 5 is perfect)
        easiness_factor: Current easiness factor
        interval_days: Current interval in days
        repetitions: Current repetition count
        
    Returns:
        Tuple of (new_easiness_factor, new_interval_days, new_repetitions, next_review_date)
    """
    # Update easiness factor
    easiness_factor = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    
    # Ensure minimum easiness
    if easiness_factor < SM2_MIN_EASINESS:
        easiness_factor = SM2_MIN_EASINESS
    
    # Update interval based on quality
    if quality < 3:  # Incorrect or difficult
        # Reset to beginning
        interval_days = 1
        repetitions = 0
    else:
        # Correct response
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            interval_days = int(interval_days * easiness_factor)
        
        repetitions += 1
    
    # Calculate next review date
    next_review_date = date.today() + timedelta(days=interval_days)
    
    return easiness_factor, interval_days, repetitions, next_review_date


def initialize_card() -> Tuple[float, int, int, date]:
    """Initialize a new flashcard with default SM-2 values"""
    easiness_factor = SM2_DEFAULT_EASINESS
    interval_days = 1
    repetitions = 0
    next_review_date = date.today()
    
    return easiness_factor, interval_days, repetitions, next_review_date


def get_cards_due_today(cards: list) -> list:
    """Filter cards that are due for review today"""
    today = date.today()
    return [card for card in cards if card.next_review_date <= today]

