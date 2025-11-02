"""Grade calculation and prediction service"""

from typing import List, Dict, Optional
from src.utils.helpers import calculate_percentage


def calculate_current_grade(grades: List[Dict]) -> float:
    """
    Calculate current weighted grade
    
    Args:
        grades: List of grade dictionaries with 'grade', 'max_grade', 'weight' keys
        
    Returns:
        Weighted average percentage
    """
    if not grades:
        return 0.0
    
    total_weighted_score = 0.0
    total_weight = 0.0
    
    for grade_entry in grades:
        grade = grade_entry.get('grade', 0)
        max_grade = grade_entry.get('max_grade', 100)
        weight = grade_entry.get('weight', 1.0)
        
        if max_grade > 0:
            percentage = (grade / max_grade) * 100
            total_weighted_score += percentage * weight
            total_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    return round(total_weighted_score / total_weight, 2)


def predict_grade_needed(
    current_grade: float,
    target_grade: float,
    completed_weight: float,
    remaining_weight: float
) -> float:
    """
    Predict what grade is needed in remaining assignments to achieve target
    
    Args:
        current_grade: Current weighted grade percentage
        target_grade: Desired final grade percentage
        completed_weight: Total weight of completed assignments (0-1)
        remaining_weight: Total weight of remaining assignments (0-1)
        
    Returns:
        Required percentage on remaining assignments
    """
    if remaining_weight == 0:
        return current_grade  # No remaining assignments
    
    # Weighted grade formula: target = (current * completed_weight) + (needed * remaining_weight)
    # Solving for needed:
    needed = (target_grade - (current_grade * completed_weight)) / remaining_weight
    
    # Clamp to reasonable values
    needed = max(0.0, min(100.0, needed))
    
    return round(needed, 2)


def calculate_grade_breakdown(grades: List[Dict]) -> Dict:
    """
    Calculate detailed grade breakdown
    
    Returns:
        Dictionary with total points, max points, percentage, weighted average
    """
    total_points = 0.0
    max_points = 0.0
    total_weighted = 0.0
    total_weight = 0.0
    
    for grade_entry in grades:
        grade = grade_entry.get('grade', 0)
        max_grade = grade_entry.get('max_grade', 100)
        weight = grade_entry.get('weight', 1.0)
        
        total_points += grade
        max_points += max_grade
        total_weighted += (grade / max_grade * 100) * weight if max_grade > 0 else 0
        total_weight += weight
    
    weighted_avg = total_weighted / total_weight if total_weight > 0 else 0
    
    return {
        'total_points': round(total_points, 2),
        'max_points': round(max_points, 2),
        'percentage': calculate_percentage(total_points, max_points),
        'weighted_average': round(weighted_avg, 2),
        'completed_count': len(grades)
    }

