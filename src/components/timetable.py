"""Deprecated timetable module.

Timetable UI has been replaced by `copilot.py`. To keep imports that
referencing the old `render_timetable` working, this file provides a
small shim that delegates to the Copilot component.
"""

from src.components.copilot import render_copilot


def render_timetable():
    """Shim to maintain compatibility with the previous timetable import."""
    """Deprecated timetable module.

    Timetable UI has been replaced by `copilot.py`. To keep imports that
    referencing the old `render_timetable` working, this file provides a
    small shim that delegates to the Copilot component.
    """

    from src.components.copilot import render_copilot


    def render_timetable():
        """Shim to maintain compatibility with the previous timetable import."""
        return render_copilot()
    st.title("📅 Timetable & Schedule")

    
