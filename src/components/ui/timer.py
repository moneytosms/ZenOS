"""Pomodoro timer component"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import timedelta
from textwrap import dedent


def timer_display(minutes: int, seconds: int = 0, label: str = "Work"):
    """
    Display a timer component
    
    Args:
        minutes: Minutes remaining
        seconds: Seconds remaining
        label: Timer label (Work, Break, etc.)
    """
    time_str = f"{minutes:02d}:{seconds:02d}"
    
    timer_html = f"""
    <div class="zenos-timer">
        <div class="zenos-timer-label">{label}</div>
        <div class="zenos-timer-display">{time_str}</div>
    </div>
    """

    safe_timer_html = dedent(timer_html).strip()

    # Use components.html to render timer markup reliably
    line_count = max(1, safe_timer_html.count('\n'))
    height = min(200, 60 + line_count * 18)
    style_block = """
    <style>
    .zenos-timer { background: #ffffff; color: #0b1220; border-radius: 8px; padding: 8px; display: inline-block; }
    .zenos-timer-label { font-weight: 600; color: #374151; }
    .zenos-timer-display { font-family: monospace; font-size: 1.2rem; color: #0b1220; }
    </style>
    """
    try:
        components.html(style_block + safe_timer_html, height=height, scrolling=False)
    except Exception:
        st.markdown(safe_timer_html, unsafe_allow_html=True)

