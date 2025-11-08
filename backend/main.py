import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from dedalus_labs import Dedalus
import database  # This imports our database.py file

# Load environment variables from .env file
load_dotenv()

# --- 1. INITIALIZE SDKs & APP ---

# Initialize Dedalus client
DEDALUS_API_KEY = os.getenv("DEDALUS_API_KEY")
if not DEDALUS_API_KEY:
    print("FATAL ERROR: DEDALUS_API_KEY not found in .env file")
    # In a real app, you'd exit. For a hackathon, you can hardcode it here
    # if you're careful: DEDALUS_API_KEY = "your_key_here"
dedalus_client = Dedalus(api_key=DEDALUS_API_KEY)

# Initialize FastAPI app
app = FastAPI()

# Initialize Firebase (this happens when database.py is imported)
# The `db` object is available from the database module
print("Firebase Admin SDK initialized.")


# --- 2. CONFIGURE CORS ---
# This is CRITICAL for your VS Code extension to be able to call this server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (good for hackathon)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# --- 3. DEFINE DATA MODELS (PYDANTIC) ---
# These models define the exact JSON your frontend *must* send.

class HintRequest(BaseModel):
    """Data model for a hint request from the VS Code extension."""
    contextWord: str
    languageId: str
    heuristic: str  # e.g., "idle", "repetitive_editing", "cursor_thrashing"
    codeSnippet: str # A chunk of code for better context

class LogRequest(BaseModel):
    """Data model for logging a stuck event to the database."""
    studentId: str # or some anonymous user ID
    contextWord: str
    heuristic: str
    languageId: str
    hint: str # The hint that was provided to the student
    codeSnippet: str


# --- 4. API ENDPOINT 1: GET HINT ---

@app.post("/get-hint")
async def get_hint_from_ai(request: HintRequest):
    """
    Receives code context from the extension, calls Dedalus to get a hint,
    and returns the hint.
    """
    
    # This is the "prompt engineering" - the most important part!
    system_prompt = f"""
    You are a "Study Helper" AI tutor. A student is programming in {request.languageId}
    and appears stuck. The "stuck signal" we detected was "{request.heuristic}".
    They are currently looking at the word "{request.contextWord}".

    Here is a snippet of their code:
    ---
    {request.codeSnippet}
    ---

    Your task is to help them.
    1.  **DO NOT** write the correct code or give the direct answer.
    2.  **DO** ask a single, short, guiding question that helps them think.
    3.  OR, if applicable, suggest a *specific* official documentation page
        (like MDN, Python docs, etc.) that explains the *concept* of "{request.contextWord}".
    
    Example response (question): "I see you're using '{request.contextWord}'. What do you expect that function to return?"
    Example response (docs): "It looks like you're working with '{request.contextWord}'. This documentation on [Concept Name] might be helpful: [URL]"
    """

    print(f"Received hint request for: {request.contextWord}")

    try:
        # Call the Dedalus MCP (Model Context Protocol)
        response = dedalus_client.chat.completions.create(
            model="gemini-2.5-flash-preview-09-2025",  # A fast and smart model
            messages=[
                {"role": "user", "content": system_prompt}
            ]
        )
        
        ai_hint = response.choices[0].delta.content
        print(f"Generated hint: {ai_hint}")
        
        # Send the hint back to the VS Code extension
        return {"hint": ai_hint}

    except Exception as e:
        print(f"Error calling Dedalus: {e}")
        # Send a user-friendly error back to the extension
        raise HTTPException(
            status_code=500, 
            detail="The AI hint generator failed. Please try again."
        )


# --- 5. API ENDPOINT 2: LOG STUCK EVENT ---

@app.post("/log-stuck-event")
async def log_stuck_event_to_db(request: LogRequest):
    """
    Receives a stuck event from the extension and logs it to Firebase
    for the professor dashboard.
    """
    
    print(f"Logging event for student: {request.studentId}, word: {request.contextWord}")

    try:
        # Use our database module to log the event
        # .model_dump() converts the Pydantic model to a dictionary
        database.log_event(request.model_dump())
        
        return {"status": "success", "message": "Event logged."}

    except Exception as e:
        print(f"Error logging to Firebase: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to log event to database."
        )


# --- 6. ML INTEGRATION ENDPOINTS (FOR ML TEAMMATE) ---

class PredictionRequest(BaseModel):
    """Request for ML model to predict if user is stuck."""
    features: list[float]  # Feature vector (typing_speed, cursor_movements, etc.)
    context: dict  # Additional context data

class TrainingDataRequest(BaseModel):
    """Training data collection for ML model."""
    session_id: str
    features: list[float]
    user_feedback: bool  # True if user confirmed they were stuck
    intervention_effective: bool | None = None  # Did the hint help?

@app.post("/ml/predict-stuck")
async def predict_stuck(request: PredictionRequest):
    """
    ML endpoint to predict if user is stuck.
    Your ML teammate will implement the model logic here.
    """
    # TODO: Integrate with trained ML model
    # For now, return a placeholder
    return {
        "is_stuck_probability": 0.7,
        "confidence": 0.85,
        "suggested_intervention": "hint"
    }

@app.post("/ml/training-data")
async def collect_training_data(request: TrainingDataRequest):
    """
    Collect training data with user feedback.
    Your ML teammate will use this to improve the model.
    """
    # TODO: Store training data for model improvement
    # For now, just log it to the same collection
    database.log_event({
        "type": "training_data",
        **request.model_dump()
    })
    return {"status": "success", "message": "Training data logged."}


# --- 7. DASHBOARD ENDPOINTS (FOR FRONTEND TEAMMATE) ---

@app.get("/dashboard/class-overview")
async def get_class_overview(class_id: str | None = None):
    """
    Get overview statistics for professor dashboard.
    Your frontend teammate will use this for the main dashboard.
    """
    # TODO: Query database for class statistics
    return {
        "total_students": 25,
        "total_stuck_events": 150,
        "avg_stuck_events_per_student": 6.0,
        "most_problematic_concepts": [
            {"concept": "async/await", "frequency": 45, "language": "javascript"},
            {"concept": "list comprehensions", "frequency": 32, "language": "python"}
        ],
        "activity_timeline": [
            {"date": "2025-11-08", "stuck_events": 12, "students_active": 18},
            {"date": "2025-11-07", "stuck_events": 8, "students_active": 22}
        ]
    }

@app.get("/dashboard/student-stats/{student_id}")
async def get_student_statistics(student_id: str):
    """
    Get detailed statistics for a specific student.
    Useful for individual student progress tracking.
    """
    # TODO: Query database for student-specific data
    return {
        "student_id": student_id,
        "total_stuck_events": 12,
        "avg_resolution_time": 4.5,
        "most_common_stuck_areas": ["functions", "loops", "conditionals"],
        "progress_trend": "improving"
    }

@app.get("/dashboard/stuck-events")
async def get_stuck_events_summary(
    start_date: str | None = None, 
    end_date: str | None = None,
    language_id: str | None = None
):
    """
    Get filtered stuck events for analytics.
    Frontend can use this for charts and detailed views.
    """
    # TODO: Query database with filters
    return [
        {
            "date": "2025-11-08",
            "language_id": "python",
            "context_word": "for",
            "heuristic": "idle",
            "student_count": 3,
            "avg_resolution_time": 5.2
        },
        {
            "date": "2025-11-08",
            "language_id": "javascript", 
            "context_word": "async",
            "heuristic": "cursor_thrashing",
            "student_count": 2,
            "avg_resolution_time": 8.7
        }
    ]

@app.get("/dashboard/real-time-activity")
async def get_realtime_activity():
    """
    Get current active students and recent stuck events.
    For real-time dashboard updates.
    """
    from datetime import datetime
    # TODO: Query recent activity from database
    return {
        "active_students": 12,
        "recent_stuck_events": 3,
        "current_help_requests": 1,
        "last_updated": datetime.now().isoformat()
    }


# --- 8. ROOT ENDPOINT (FOR TESTING) ---

@app.get("/")
def read_root():
    return {"message": "Study Helper Backend is running!"}