"""Metric display component"""

import streamlit as st
from src.components.ui.card import metric_card


def display_metric(value: str, label: str, delta: str = "", delta_color: str = "normal"):
    """
    Display a metric with optional delta
    
    Args:
        value: Main value to display
        label: Label for the metric
        delta: Delta/change value (optional)
        delta_color: Color for delta (normal, inverse, off)
    """
    # Use Streamlit's built-in metric with custom styling
    st.metric(label=label, value=value, delta=delta if delta else None)

