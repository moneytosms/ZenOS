"""Card UI component"""

import streamlit as st
import streamlit.components.v1 as components
from textwrap import dedent


def card(title: str, content: str = "", icon: str = "", color: str = "primary"):
    """
    Create a custom card component
    
    Args:
        title: Card title
        content: Card content (can be HTML)
        icon: Optional icon emoji or icon name
        color: Color theme (primary, success, warning, error)
    """
    icon_html = f"{icon} " if icon else ""
    
    card_html = f"""
    <div class="zenos-card fade-in">
        <div class="zenos-card-header">
            <h3 class="zenos-card-title">{icon_html}{title}</h3>
        </div>
        <div class="zenos-card-content">
            {content}
        </div>
    </div>
    """

    # Remove incidental indentation from multi-line content to avoid Markdown
    # treating leading spaces as code blocks. Dedent and strip to keep HTML
    # well-formed while preserving intended inner formatting.
    # Also dedent the incoming content itself to avoid embedded leading spaces
    # that can trigger code-block rendering.
    safe_content = dedent(str(content)).strip()
    card_html = card_html.replace(str(content), safe_content)
    safe_html = dedent(card_html).strip()

    # Render using an isolated HTML component so Streamlit's Markdown
    # parser doesn't accidentally treat fragments as code. Estimate height
    # from number of lines to give a reasonable default.
    line_count = max(3, safe_html.count('\n'))
    height = min(600, 80 + line_count * 18)
    # Inline safe styles to ensure readable contrast even if project CSS
    # is not loaded. Use a light card with dark text for maximum contrast.
    style_block = """
    <style>
    .zenos-card { background: #ffffff; color: #0b1220; border-radius: 10px; padding: 12px; margin: 8px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .zenos-card-header { margin-bottom: 8px; }
    .zenos-card-title { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial; margin: 0; font-size: 1.1rem; color: #0b1220; }
    .zenos-card-content { color: #0b1220; font-size: 0.95rem; }
    .zenos-card a { color: #1d4ed8; }
    .zenos-metric { background: #ffffff; color: #0b1220; padding: 10px; border-radius: 8px; text-align: center; }
    .zenos-metric-value { font-size: 1.6rem; font-weight: 700; }
    .zenos-metric-label { font-size: 0.9rem; color: #374151; }
    /* Progress bar defaults (in case metric embeds one) */
    .zenos-progress { background: #e6eef8; height: 10px; border-radius: 6px; overflow: hidden; }
    .zenos-progress-bar { background: #2563eb; height: 100%; }
    .zenos-timer { background: #ffffff; color: #0b1220; border-radius: 8px; padding: 8px; }
    </style>
    """
    try:
        components.html(style_block + safe_html, height=height, scrolling=False)
    except Exception:
        # Fallback to markdown if components are not available for some reason
        st.markdown(safe_html, unsafe_allow_html=True)


def metric_card(value: str, label: str, trend: str = "", trend_direction: str = "neutral"):
    """
    Create a metric card component
    
    Args:
        value: Main metric value
        label: Metric label
        trend: Trend indicator text (optional)
        trend_direction: up, down, or neutral
    """
    trend_html = ""
    if trend:
        trend_class = "up" if trend_direction == "up" else "down" if trend_direction == "down" else ""
        trend_html = f'<div class="zenos-metric-trend {trend_class}">{trend}</div>'
    
    metric_html = f"""
    <div class="zenos-card zenos-metric">
        <div class="zenos-metric-value">{value}</div>
        <div class="zenos-metric-label">{label}</div>
        {trend_html}
    </div>
    """

    safe_metric_html = dedent(metric_html).strip()
    # Render metric card via components.html for consistency
    line_count = max(1, safe_metric_html.count('\n'))
    height = min(200, 60 + line_count * 18)
    style_block_metric = """
    <style>
    .zenos-card, .zenos-card.zenos-metric { background: #ffffff; color: #0b1220; border-radius: 8px; padding: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
    .zenos-metric-value { font-size: 1.6rem; font-weight: 700; }
    .zenos-metric-label { color: #374151; }
    </style>
    """
    try:
        components.html(style_block_metric + safe_metric_html, height=height, scrolling=False)
    except Exception:
        st.markdown(safe_metric_html, unsafe_allow_html=True)

