"""Gemini API service wrapper"""

import os
import streamlit as st
from typing import Optional, List, Dict, Any
import json
import re

# Try new API first (from google import genai), fallback to old API
USE_NEW_API = False
google_genai = None

try:
    # Try new API format: from google import genai
    from google import genai
    google_genai = genai
    USE_NEW_API = True
except ImportError:
    try:
        # Fallback to old API: google.generativeai
        import google.generativeai as genai
        google_genai = genai
        USE_NEW_API = False
    except ImportError:
        google_genai = None


class GeminiService:
    """Service for interacting with Google Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini service
        
        Args:
            api_key: Google Gemini API key. If not provided, tries to get from environment.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model = None
        
        if not google_genai:
            return
        
        if self.api_key and google_genai:
            if USE_NEW_API:
                # New API: from google import genai
                # Initialize client with API key
                self.client = google_genai.Client(api_key=self.api_key)
                # Default to gemini-2.5-flash (most recent)
                self.model = "gemini-2.5-flash"
            else:
                # Old API: google.generativeai
                google_genai.configure(api_key=self.api_key)
                # Try models in order of preference
                model_names = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-pro', 'gemini-pro']
                self.model = None
                for model_name in model_names:
                    try:
                        self.model = google_genai.GenerativeModel(model_name)
                        break  # Success, use this model
                    except Exception:
                        continue
    
    def set_api_key(self, api_key: str):
        """Set API key and initialize model"""
        self.api_key = api_key
        
        if not google_genai:
            raise ValueError("Google GenAI package not installed. Install with: uv add google-generativeai")
        
        if USE_NEW_API:
            # New API: from google import genai
            # Initialize client with API key
            self.client = google_genai.Client(api_key=api_key)
            # Default to gemini-2.5-flash (most recent)
            self.model = "gemini-2.5-flash"
        else:
            # Old API: google.generativeai  
            google_genai.configure(api_key=api_key)
            # Try models in order of preference
            model_names = ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-pro', 'gemini-pro']
            self.model = None
            last_error = None
            for model_name in model_names:
                try:
                    self.model = google_genai.GenerativeModel(model_name)
                    break  # Success, use this model
                except Exception as e:
                    last_error = str(e)
                    continue
            
            if self.model is None:
                raise ValueError(f"Failed to initialize Gemini model. Tried: {', '.join(model_names)}. Last error: {last_error}")
    
    def is_configured(self) -> bool:
        """Check if API key is configured"""
        if USE_NEW_API:
            return self.client is not None and self.model is not None
        else:
            return self.model is not None
    
    def _generate_content(self, prompt: str) -> str:
        """Generate content using the appropriate API"""
        if not self.is_configured():
            raise ValueError("Gemini API key not configured")
        
        try:
            if USE_NEW_API and self.client:
                # New API format: client.models.generate_content
                # Format: contents can be a string or list following REST API structure
                model_name = self.model or "gemini-2.5-flash"
                # The Python SDK should handle conversion, but ensure we match REST API format
                # REST API expects: {"contents": [{"parts": [{"text": "..."}]}]}
                # Try direct string first (SDK should convert)
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    return response.text
                except (AttributeError, TypeError, ValueError) as e:
                    # If string doesn't work, try REST API structure format
                    # Format matches: {"contents": [{"parts": [{"text": "..."}]}]}
                    try:
                        contents_struct = [{
                            "parts": [{"text": str(prompt)}]
                        }]
                        response = self.client.models.generate_content(
                            model=model_name,
                            contents=contents_struct
                        )
                        return response.text
                    except Exception as e2:
                        # Fallback: try direct client method
                        try:
                            response = self.client.generate_content(
                                model=model_name,
                                contents=prompt
                            )
                            return response.text
                        except Exception:
                            raise e2
                except Exception as e:
                    # If model doesn't exist, try alternative models
                    error_msg = str(e)
                    if "404" in error_msg or "not found" in error_msg.lower() or "is not found" in error_msg:
                        alt_models = ["gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
                        contents_struct = [{
                            "parts": [{"text": str(prompt)}]
                        }]
                        for alt_model in alt_models:
                            if alt_model != model_name:
                                try:
                                    # Try with REST API structure format
                                    response = self.client.models.generate_content(
                                        model=alt_model,
                                        contents=contents_struct
                                    )
                                    # Update model for future calls
                                    self.model = alt_model
                                    return response.text
                                except Exception:
                                    # Try as string
                                    try:
                                        response = self.client.models.generate_content(
                                            model=alt_model,
                                            contents=prompt
                                        )
                                        self.model = alt_model
                                        return response.text
                                    except Exception:
                                        continue
                    raise Exception(f"Model error: {error_msg}")
            else:
                # Old API format: model.generate_content
                response = self.model.generate_content(prompt)
                return response.text
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages
            if "API key" in error_msg.lower() or "auth" in error_msg.lower():
                raise Exception(f"Authentication error: Please check your API key. {error_msg}")
            elif "404" in error_msg or "not found" in error_msg.lower() or "is not found" in error_msg:
                # Model not found, try alternatives
                if USE_NEW_API and self.client:
                    alt_models = ["gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
                    contents_struct = [{
                        "parts": [{"text": str(prompt)}]
                    }]
                    for alt_model in alt_models:
                        if alt_model != self.model:
                            try:
                                # Try with REST API structure format first (matches curl format)
                                response = self.client.models.generate_content(
                                    model=alt_model,
                                    contents=contents_struct
                                )
                                self.model = alt_model
                                return response.text
                            except Exception:
                                # Try as string (SDK might convert)
                                try:
                                    response = self.client.models.generate_content(
                                        model=alt_model,
                                        contents=prompt
                                    )
                                    self.model = alt_model
                                    return response.text
                                except Exception:
                                    continue
                raise Exception(f"Model not found. Tried: {self.model}. Error: {error_msg}")
            else:
                raise Exception(f"Error calling Gemini API: {error_msg}")

    def stream_generate_content(self, prompt: str):
        """Attempt to stream content from the Gemini SDK.

        This is a best-effort implementation that tries multiple possible
        streaming entry points depending on which GenAI package is available.
        If streaming is not supported, it falls back to returning the full
        response as a single chunk.

        Yields: successive text chunks (strings)
        """
        if not self.is_configured():
            raise ValueError("Gemini API key not configured")

        # New API (google.genai)
        if USE_NEW_API and self.client:
            model_name = self.model or "gemini-2.5-flash"
            # Try known streaming interfaces (best-effort)
            try:
                # genai.Client.responses.stream or client.responses.stream
                if hasattr(self.client, 'responses') and hasattr(self.client.responses, 'stream'):
                    for part in self.client.responses.stream(model=model_name, input=prompt):
                        # part may be an object with .text or dict-like
                        text = getattr(part, 'text', None) or (part.get('text') if isinstance(part, dict) else None)
                        if text:
                            yield text
                    return
            except Exception:
                pass

            try:
                # Some SDK versions expose models.stream_generate_content
                if hasattr(self.client, 'models') and hasattr(self.client.models, 'stream_generate_content'):
                    for ev in self.client.models.stream_generate_content(model=model_name, contents=prompt):
                        # ev may contain .text or be dict-like
                        text = getattr(ev, 'text', None) or (ev.get('text') if isinstance(ev, dict) else None) or getattr(ev, 'delta', None)
                        if text:
                            yield text
                    return
            except Exception:
                pass

        # Old API: google.generativeai
        if not USE_NEW_API and self.model:
            try:
                # Some wrappers may provide a streaming generator on the model
                if hasattr(self.model, 'stream'):
                    for chunk in self.model.stream(prompt):
                        text = getattr(chunk, 'text', None) or (chunk.get('text') if isinstance(chunk, dict) else None)
                        if text:
                            yield text
                    return
            except Exception:
                pass

        # Fallback: no streaming available; yield full response once
        full = self._generate_content(prompt)
        yield full
    
    def parse_syllabus(self, syllabus_text: str) -> Dict[str, Any]:
        """
        Parse syllabus text and extract structured course information
        
        Returns:
            Dictionary with courses, deadlines, exam dates, etc.
        """
        if not self.is_configured():
            raise ValueError("Gemini API key not configured")
        
        prompt = f"""You are parsing a course syllabus. Extract all course information into structured JSON.

The syllabus may contain:
- Course name and code (e.g., "IMA211 Probability, Statistics and Random Processes")
- Credits (e.g., "[3-1-0-4]" means 3 lecture, 1 tutorial, 0 lab, 4 credits total)
- Course objectives and outcomes
- Detailed syllabus/topics list
- Textbooks and references
- Assignments, exams, projects with dates
- Instructor information
- Attendance requirements

Return a JSON object with this structure:
{{
    "courses": [
        {{
            "name": "Full course name",
            "code": "Course code like IMA211",
            "instructor": "Instructor name if mentioned",
            "credits": <number> (extract from credit notation like [3-1-0-4] = 4),
            "topics": ["topic1", "topic2", ...] (list of main topics from syllabus section),
            "objectives": ["objective1", "objective2", ...],
            "outcomes": ["outcome1", "outcome2", ...],
            "textbooks": ["textbook1", "textbook2", ...],
            "assignments": [
                {{
                    "title": "Assignment name",
                    "due_date": "YYYY-MM-DD" (if mentioned),
                    "weight": <decimal>
                }}
            ],
            "exams": [
                {{
                    "title": "Exam name",
                    "date": "YYYY-MM-DD" (if mentioned),
                    "weight": <decimal>
                }}
            ],
            "attendance_required": true/false,
            "attendance_threshold": <number> (default 75.0)
        }}
    ],
    "semester_start": "YYYY-MM-DD" (if mentioned),
    "semester_end": "YYYY-MM-DD" (if mentioned),
    "important_dates": []
}}

Rules:
1. Extract course code from patterns like "IMA211", "COURSE123", etc.
2. For credits, look for patterns like [3-1-0-4], [4-0-0-4], or just "3 credits" - extract the total credit value
3. Extract all topics from the "Syllabus" section as an array
4. Extract objectives and outcomes as arrays
5. Extract textbook/reference titles as an array
6. If multiple courses are mentioned, create multiple course objects
7. If no dates are mentioned, leave assignments/exams arrays empty or with titles only

Syllabus text:
{syllabus_text[:20000]}

Return ONLY valid JSON. No markdown, no explanations. Start with {{ and end with }}."""
        
        try:
            text = self._generate_content(prompt)
            text = text.strip()
            
            # Remove markdown code blocks if present
            if "```json" in text:
                parts = text.split("```json")
                if len(parts) > 1:
                    text = parts[1].split("```")[0].strip()
            elif "```" in text:
                parts = text.split("```")
                if len(parts) > 1:
                    text = parts[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()
            
            # Try to find JSON object in text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group(0)
            
            text = text.strip()
            
            parsed = json.loads(text)
            
            # Validate structure
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a dictionary")
            
            # Ensure courses key exists
            if 'courses' not in parsed:
                parsed['courses'] = []
            
            # Validate courses structure
            if isinstance(parsed.get('courses'), list):
                validated_courses = []
                for course in parsed['courses']:
                    if isinstance(course, dict) and course.get('name'):
                        validated_courses.append(course)
                parsed['courses'] = validated_courses
            
            return parsed
            
        except json.JSONDecodeError as e:
            # Log error but don't use st functions here (might not be in Streamlit context)
            if 'text' in locals():
                print(f"Failed to parse JSON response: {str(e)}")
                print(f"Raw response preview: {text[:500]}")
            # Return minimal structure on error
            return {
                "courses": [],
                "semester_start": None,
                "semester_end": None,
                "important_dates": []
            }
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            # Return minimal structure on error
            return {
                "courses": [],
                "semester_start": None,
                "semester_end": None,
                "important_dates": []
            }
    
    def generate_study_plan(self, course_name: str, topics: List[str], days_until_exam: int) -> str:
        """Generate a study plan for given topics and timeframe"""
        if not self.is_configured():
            return "API key not configured"
        
        topics_str = "\n".join(f"- {topic}" for topic in topics)
        prompt = f"""Create a {days_until_exam}-day study plan for {course_name}.
        
        Topics to cover:
        {topics_str}
        
        Provide a day-by-day breakdown with specific study activities."""
        
        try:
            return self._generate_content(prompt)
        except Exception as e:
            return f"Error generating study plan: {str(e)}"
    
    def generate_topic_brief(self, topic: str, course_context: Optional[str] = None, course_background: Optional[Dict[str, Any]] = None) -> str:
        """Generate a brief overview of a study topic"""
        if not self.is_configured():
            return "API key not configured"
        
        # Build comprehensive course context
        context_parts = []
        if course_background:
            context_parts.append(f"\nCourse: {course_background.get('name', '')} ({course_background.get('code', '')})")
            if course_background.get('instructor'):
                context_parts.append(f"Instructor: {course_background['instructor']}")
            
            if course_background.get('topics'):
                topics_str = ", ".join(course_background['topics'][:10])  # Limit to first 10 topics
                context_parts.append(f"\nCourse Topics Covered:\n{topics_str}")
            
            if course_background.get('objectives'):
                objectives_str = "\n".join(f"- {obj}" for obj in course_background['objectives'][:5])
                context_parts.append(f"\nCourse Objectives:\n{objectives_str}")
            
            if course_background.get('textbooks'):
                textbooks_str = "\n".join(f"- {book}" for book in course_background['textbooks'][:3])
                context_parts.append(f"\nRecommended Textbooks:\n{textbooks_str}")
        elif course_context:
            context_parts.append(f"\nCourse: {course_context}")
        
        context = "\n".join(context_parts) if context_parts else ""
        
        prompt = f"""Provide a concise study brief for the topic: {topic}
        
        {context if context else ''}
        
        Include:
        - Key concepts and definitions
        - Important formulas or equations (if applicable)
        - Study tips specific to this course
        - Common questions and areas of focus
        - How this topic relates to the broader course material
        
        Keep it concise but comprehensive (3-5 paragraphs)."""
        
        try:
            return self._generate_content(prompt)
        except Exception as e:
            return f"Error generating topic brief: {str(e)}"
    
    def generate_quiz_questions(self, topic: str, num_questions: int = 5, course_background: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """Generate quiz questions for a topic"""
        if not self.is_configured():
            return []
        
        # Build course context for quiz generation
        context_parts = []
        if course_background:
            context_parts.append(f"\nCourse: {course_background.get('name', '')} ({course_background.get('code', '')})")
            
            if course_background.get('topics'):
                topics_str = ", ".join(course_background['topics'][:15])
                context_parts.append(f"\nRelevant Course Topics: {topics_str}")
            
            if course_background.get('objectives'):
                objectives_str = "\n".join(f"- {obj}" for obj in course_background['objectives'][:3])
                context_parts.append(f"\nCourse Objectives:\n{objectives_str}")
        
        context = "\n".join(context_parts) if context_parts else ""
        
        prompt = f"""Generate {num_questions} quiz questions about: {topic}
        
        {context if context else ''}
        
        Instructions:
        - Create questions that align with the course content and objectives
        - Questions should test understanding of key concepts, not just memorization
        - Include a mix of difficulty levels
        - Ensure options are plausible and well-distributed
        
        Return as JSON array:
        [
            {{
                "question": "Question text",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct": 0,
                "explanation": "Brief explanation of why this is the correct answer"
            }}
        ]
        
        Return ONLY valid JSON."""
        
        try:
            text = self._generate_content(prompt)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            questions = json.loads(text)
            return questions if isinstance(questions, list) else []
        except Exception as e:
            return []
    
    def brainstorm_research(self, topic: str, initial_thoughts: str) -> Dict[str, Any]:
        """
        Help brainstorm research ideas - returns questions to refine thinking
        
        Returns:
            Dictionary with questions, suggestions, and refined outline
        """
        if not self.is_configured():
            raise ValueError("Gemini API key not configured")
        
        prompt = f"""You are a research coach. A student is working on: {topic}

        Their initial thoughts:
        {initial_thoughts}

        Help them refine their thinking by:
        1. Asking 3-5 probing questions that challenge assumptions and deepen understanding
        2. Suggesting 2-3 angles or perspectives to explore
        3. Identifying potential gaps or areas needing more clarity

        Return as JSON:
        {{
            "questions": ["question1", "question2", ...],
            "suggestions": ["suggestion1", "suggestion2", ...],
            "gaps": ["gap1", "gap2", ...],
            "refined_focus": "A refined statement of their research focus"
        }}
        
        Return ONLY valid JSON."""
        
        try:
            text = self._generate_content(prompt)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            return json.loads(text)
        except Exception as e:
            return {
                "questions": [],
                "suggestions": [],
                "gaps": [],
                "refined_focus": topic
            }
    
    def generate_outline(self, topic: str, research_focus: str, key_points: List[str]) -> str:
        """Generate a structured outline for research"""
        if not self.is_configured():
            return ""
        
        points_str = "\n".join(f"- {point}" for point in key_points)
        prompt = f"""Create a detailed research outline for: {topic}

        Research focus: {research_focus}

        Key points to include:
        {points_str}

        Create a hierarchical outline with:
        - Main sections (I, II, III)
        - Subsections (A, B, C)
        - Sub-subsections (1, 2, 3)
        
        Make it comprehensive and well-structured."""
        
        try:
            return self._generate_content(prompt)
        except Exception as e:
            return f"Error generating outline: {str(e)}"
    
    def generate_draft(self, outline: str, topic: str) -> str:
        """Generate a draft document from outline"""
        if not self.is_configured():
            return ""
        
        prompt = f"""Write a research draft based on this outline:

        Topic: {topic}
        
        Outline:
        {outline[:4000]}
        
        Write a well-structured draft with:
        - Introduction
        - Body paragraphs following the outline
        - Conclusion
        
        Use academic writing style. Aim for approximately 1000-1500 words."""
        
        try:
            return self._generate_content(prompt)
        except Exception as e:
            return f"Error generating draft: {str(e)}"
    
    def create_flashcards_from_text(self, text: str, num_cards: int = 10) -> List[Dict[str, str]]:
        """Generate flashcards from text content"""
        if not self.is_configured():
            return []
        
        prompt = f"""Create {num_cards} flashcards from this text:

        {text[:3000]}
        
        Return as JSON array:
        [
            {{
                "front": "Question or prompt",
                "back": "Answer or explanation"
            }}
        ]
        
        Focus on key concepts, definitions, formulas, and important facts.
        Return ONLY valid JSON."""
        
        try:
            text_response = self._generate_content(prompt)
            text = text_response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            cards = json.loads(text)
            return cards if isinstance(cards, list) else []
        except Exception as e:
            return []

