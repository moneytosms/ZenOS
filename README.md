# ZenOS: The Personal Learning OS

> "ZenOS doesn't add another tab. It replaces chaos with clarity."

## Overview

ZenOS is a **personal learning operating system** - a unified cockpit where planning, studying, tracking, wellness, and research converge in one place. Unlike fragmented productivity apps, ZenOS integrates all academic needs into one adaptive system.

## Features

### 🎯 Core Features

1. **Unified Academic Cockpit** - One dashboard for timetable, tasks, attendance, exams, progress, flashcards, and habits
2. **Adaptive Timetable & Lesson Planner** - Auto-generates and recalculates study plans based on syllabus and deadlines
3. **Smart Study Session Co-Pilot** - Pomodoro mode with topic briefs, quizzes, and flashcards
4. **Attendance & Grade Tracker** - Live attendance % with cutoff alerts and grade predictions
5. **Research Coach** - Conversational assistant that helps brainstorm and generates structured outlines + drafts
6. **Spaced Repetition & Flashcards** - Auto-created flashcards using SM-2 scheduling algorithm
7. **Wellness Layer** - Focus streaks, recovery nudges, and reflection logs
8. **Distraction Guard & Focus Analytics** - Built-in timer with focus metrics and best hours tracking
9. **Future Stretch Features** - Calendar sync, peer accountability, voice-to-notes

## Tech Stack

- **Frontend**: Streamlit with custom CSS/JS
- **Package Manager**: uv (modern Python package manager)
- **AI**: Google Gemini API
- **Database**: SQLite with SQLAlchemy ORM
- **PDF Processing**: PyPDF2 / pdfplumber
- **Export**: python-docx, reportlab for document generation

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager installed

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ZenOS
   ```

2. **Install dependencies using uv**
   ```bash
   uv sync
   ```

3. **Run the application**
   ```bash
   uv run streamlit run app.py
   ```

4. **Access the application**
   - Open your browser to `http://localhost:8501`
   - Enter your Gemini API key when prompted (first time only)

### Getting a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key and paste it into ZenOS when prompted

## Project Structure

```
ZenOS/
├── app.py                    # Main Streamlit entry point
├── assets/                   # Static assets (CSS, JS, icons)
├── src/                      # Source package
│   ├── database/            # Database models and setup
│   ├── services/            # Business logic (AI, scheduling, etc.)
│   ├── components/          # UI components
│   └── utils/               # Utility functions
├── data/                     # SQLite database (gitignored)
└── pyproject.toml           # Project configuration
```

## Usage Guide

### Getting Started

1. **Set up your API key**: Enter your Gemini API key in the sidebar
2. **Import your syllabus**: Upload a PDF or paste text to auto-generate your timetable
3. **Explore the dashboard**: View your unified academic cockpit
4. **Start a study session**: Use the study session feature with Pomodoro timer
5. **Track attendance**: Input your class attendance and monitor your percentage
6. **Use Research Coach**: Chat with ZenOS to brainstorm and generate outlines

### Key Workflows

- **Syllabus Upload** → Auto-generates timetable and extracts course information
- **Study Session** → Start session → Get topic briefs → Use Pomodoro → Track confidence
- **Attendance Tracking** → Mark classes → View percentage → Get alerts on low attendance
- **Research Coach** → Chat about ideas → Get questions → Generate outline → Export document

## Development

### Adding Dependencies

```bash
uv add package-name
```

### Running in Development Mode

```bash
uv run streamlit run app.py --server.headless true
```

### Database

The SQLite database is automatically created on first run in the `data/` directory.

## Alignment with SDGs

- **SDG 4: Quality Education** → Makes learning more personalized, efficient, and accessible
- **SDG 3: Good Health and Well-Being** → Wellness nudges prevent burnout and support balance
- **SDG 8: Decent Work and Economic Growth** → Boosts academic efficiency, reducing dropout rates

## Philosophy

Students don't need 7 different apps that don't talk to each other. They need one cockpit for their academic life—something that organizes, adapts, and protects their focus.

**ZenOS isn't another app. It's the OS for learning itself.**

## License

[Add your license here]

## Contributors

[Add contributors here]

