"""Card UI component"""

import re
import html as _html
import streamlit as st
import streamlit.components.v1 as components
from textwrap import dedent


def _simple_markdown_to_html(md: str) -> str:
    """A tiny Markdown -> HTML converter for common constructs.

    Supports fenced code blocks, headings (#), bold/italic, inline code,
    and unordered lists. Escapes HTML first to avoid XSS and then
    converts basic markdown patterns.
    """
    if not md:
        return ""

    text = md.replace('\r\n', '\n').replace('\r', '\n')

    # If the input already contains HTML tags (e.g. <p>, <strong>), assume
    # it's preformatted HTML and return it (dedented) so tags render
    # correctly instead of being escaped. This preserves earlier behavior
    # where upstream code or the assistant returned HTML fragments.
    if re.search(r"<\/?[a-zA-Z]+[\s>]", text):
        return dedent(text).strip()

    # Escape HTML for plain-markdown input
    text = _html.escape(text)

    # Fenced code blocks ``` ``` -> <pre><code>
    def _fenced_repl(m):
        inner = m.group(1)
        return f"<pre><code>{inner}</code></pre>"

    text = re.sub(r"```\n?(.*?)\n?```", _fenced_repl, text, flags=re.DOTALL)

    # Headings
    def _hd(m):
        level = len(m.group(1))
        content = m.group(2).strip()
        return f"<h{level}>{content}</h{level}>"

    text = re.sub(r"^(#{1,3})\s+(.+)$", _hd, text, flags=re.MULTILINE)

    # Unordered lists
    lines = text.split('\n')
    out_lines = []
    in_list = False
    list_items = []
    for line in lines:
        if re.match(r"^\s*([-*])\s+", line):
            item = re.sub(r"^\s*([-*])\s+", "", line)
            list_items.append(item)
            in_list = True
        else:
            if in_list:
                out_lines.append("<ul>" + "".join(f"<li>{li}</li>" for li in list_items) + "</ul>")
                list_items = []
                in_list = False
            out_lines.append(line)
    if in_list and list_items:
        out_lines.append("<ul>" + "".join(f"<li>{li}</li>" for li in list_items) + "</ul>")

    text = "\n".join(out_lines)

    # Inline formatting
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    # Paragraphs
    blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
    html_blocks = []
    for b in blocks:
        if b.startswith('<h') or b.startswith('<ul') or b.startswith('<pre'):
            html_blocks.append(b)
        else:
            b = b.replace('\n', '<br>')
            html_blocks.append(f"<p>{b}</p>")
    return '\n'.join(html_blocks)


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
    safe_content = dedent(str(content)).strip()
    # Convert basic markdown into HTML so it renders like Streamlit.markdown
    rendered_content = _simple_markdown_to_html(safe_content)
    card_html = card_html.replace(str(content), rendered_content)
    safe_html = dedent(card_html).strip()

    # Render using an isolated HTML component so Streamlit's Markdown
    # parser doesn't accidentally treat fragments as code. Estimate height
    # from number of lines to give a reasonable default.
    line_count = max(3, safe_html.count('\n'))
    height = min(600, 80 + line_count * 18)
    # Inline safe styles that blend with a dark Streamlit background but
    # provide slight contrast. We don't force text color so it follows
    # the user's chosen Streamlit theme; the background and border give
    # a subtle card effect.
    style_block = """
    <style>
    /* White-ish, high-visibility card styling for dark themes */
    .zenos-card { background: rgba(255,255,255,0.08); color: #f8fafc; border-radius: 10px; padding: 12px; margin: 8px 0; border: 1px solid rgba(255,255,255,0.06); }
    .zenos-card-header { margin-bottom: 8px; }
    .zenos-card-title { margin: 0; font-size: 1.1rem; color: #ffffff; }
    .zenos-card-content { font-size: 0.95rem; color: #f1f5f9; }
    /* Allow card content to scroll internally when it grows too tall */
    .zenos-card-content { max-height: 360px; overflow: auto; }
    .zenos-card a { color: #9fbfff; }
    .zenos-metric { background: rgba(255,255,255,0.06); color: #f8fafc; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.06); }
    .zenos-progress { background: rgba(255,255,255,0.04); height: 10px; border-radius: 6px; overflow: hidden; }
    .zenos-progress-bar { background: #9fbfff; height: 100%; }
    .zenos-timer { background: rgba(255,255,255,0.06); color: #f8fafc; border-radius: 8px; padding: 8px; }
    </style>
    """
    try:
        components.html(style_block + safe_html, height=height, scrolling=True)
    except Exception:
        # Fallback: render the converted HTML as markdown (unsafe) if components not available
        st.markdown(style_block + safe_html, unsafe_allow_html=True)


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
    .zenos-card, .zenos-card.zenos-metric { background: rgba(255,255,255,0.06); color: #f8fafc; border-radius: 8px; padding: 8px; border: 1px solid rgba(255,255,255,0.06); }
    .zenos-metric-value { font-size: 1.6rem; font-weight: 700; color: #ffffff; }
    .zenos-metric-label { color: #e6eef8; }
    </style>
    """
    try:
        components.html(style_block_metric + safe_metric_html, height=height, scrolling=True)
    except Exception:
        st.markdown(safe_metric_html, unsafe_allow_html=True)

