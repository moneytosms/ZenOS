"""Layout utilities for custom Streamlit styling"""

import os
import streamlit as st
from pathlib import Path


def inject_custom_css():
    """Load and inject custom CSS files"""
    # Intentionally no-op: we remove all custom CSS injection so Streamlit
    # renders using its default styling. This prevents custom styles from
    # interfering with code blocks, copy-paste behavior and layout clipping.
    return


def setup_custom_layout():
    """Setup custom layout - hide Streamlit branding and apply styles"""
    # Custom CSS injection intentionally disabled. Keep layout defaults.
    
    # Page config
    st.set_page_config(
        page_title="ZenOS - Personal Learning OS",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def hide_streamlit_style():
    """Hide Streamlit default elements"""
    hide_default_format = """
    <style>
    footer {visibility: hidden;}
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
    """
    st.markdown(hide_default_format, unsafe_allow_html=True)


def create_custom_sidebar():
    """Create styled sidebar navigation"""
    st.sidebar.markdown("## 📚 ZenOS")
    st.sidebar.markdown("---")
    return st.sidebar


def apply_theme(theme: str = "light"):
    """Apply theme (light/dark)"""
    # This is handled by CSS variables in themes.css
    # In the future, we can add JavaScript to toggle data-theme attribute
    pass

