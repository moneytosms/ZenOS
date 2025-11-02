"""Custom progress bar component"""

import streamlit as st
import streamlit.components.v1 as components
from textwrap import dedent


def progress_bar(value: float, max_value: float = 100.0, color: str = "primary", label: str = ""):
    """
    Display a custom styled progress bar
    
    Args:
        value: Current value
        max_value: Maximum value
        color: Color theme (primary, success, warning, error)
        label: Optional label above progress bar
    """
    percentage = min((value / max_value) * 100, 100.0) if max_value > 0 else 0
    
    color_class = {
        "primary": "",
        "success": "zenos-progress-success",
        "warning": "zenos-progress-warning",
        "error": "zenos-progress-error"
    }.get(color, "")
    
    label_html = f'<div style="margin-bottom: 8px; color: var(--text-secondary); font-size: 0.875rem;">{label}</div>' if label else ""
    
    progress_html = f"""
    {label_html}
    <div class="zenos-progress">
        <div class="zenos-progress-bar {color_class}" style="width: {percentage}%;"></div>
    </div>
    <div style="text-align: center; margin-top: 4px; color: var(--text-secondary); font-size: 0.875rem;">
        {percentage:.1f}%
    </div>
    """

    safe_progress = dedent(progress_html).strip()

    # Render inside components.html to avoid Markdown code-block issues
    line_count = max(1, safe_progress.count('\n'))
    height = min(200, 60 + line_count * 18)
    style_block = """
    <style>
    .zenos-progress { background: #e6eef8; height: 10px; border-radius: 6px; overflow: hidden; }
    .zenos-progress-bar { background: #2563eb; height: 100%; }
    .zenos-card, .zenos-metric { background: #ffffff; color: #0b1220; }
    </style>
    """
    try:
        components.html(style_block + safe_progress, height=height, scrolling=False)
    except Exception:
        st.markdown(safe_progress, unsafe_allow_html=True)

