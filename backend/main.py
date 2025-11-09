import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from dedalus_labs import Dedalus
import database  # This imports our database.py file

# Add ML directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "ml"))

# Import ML blackbox (graceful fallback if not available)
try:
    from ml.blackbox import StuckDetector
    ML_AVAILABLE = True
    print("✅ ML blackbox system loaded successfully")
except ImportError as e:
    ML_AVAILABLE = False
    print(f"⚠️ ML system not available: {e}")

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

# Initialize ML detector
stuck_detector = None
if ML_AVAILABLE:
    try:
        stuck_detector = StuckDetector()
        print("✅ ML stuck detector initialized")
    except Exception as e:
        print(f"⚠️ ML detector initialization failed: {e}")
        ML_AVAILABLE = False


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

class MLPredictionRequest(BaseModel):
    """Data model for ML stuck prediction request."""
    signals: dict  # Dictionary of feature_name -> value
    
class MLFeedbackRequest(BaseModel):
    """Data model for ML feedback logging."""
    signals: dict  # Dictionary of feature_name -> value
    was_stuck: bool  # Ground truth
    source: str = "manual"  # 'manual', 'confirmed', 'rejected'


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


# --- 6. ML ENDPOINTS ---

@app.post("/predict-stuck")
async def predict_stuck_ml(request: MLPredictionRequest):
    """
    ML-powered stuck detection using the blackbox system.
    
    The ML model expects up to 18 different signal features for optimal prediction.
    Missing features will be handled gracefully by the model.
    
    Expected signal features (18 total):
    - Idle time: idle_time_total, idle_time_max
    - Editing: edit_events, edit_velocity, backspace_ratio  
    - Cursor: cursor_moves, cursor_distance, cursor_entropy
    - Errors: error_events, unique_errors, error_repeat_count, error_persistence
    - Execution: time_since_last_run, run_attempt_count
    - Context: context_switches, focus_time_avg
    - Comments: comment_keywords, comment_length_avg
    
    Expects:
    {
        "signals": {
            "idle_time_total": 45.2,
            "edit_events": 23,
            "error_events": 5,
            // ... up to 18 total features for best accuracy
        }
    }
    
    Returns:
    {
        "is_stuck": true,
        "confidence": 0.87,
        "model_available": true
    }
    """
    if not ML_AVAILABLE or not stuck_detector:
        return JSONResponse(
            content={
                "is_stuck": False,
                "confidence": 0.0,
                "model_available": False,
                "message": "ML model not available"
            }
        )
    
    try:
        # Log the incoming signals for debugging
        print(f"🔍 Received signals ({len(request.signals)} total):")
        for signal_name, signal_value in request.signals.items():
            print(f"   {signal_name}: {signal_value}")
        
        is_stuck = stuck_detector.is_stuck(request.signals)
        
        return JSONResponse(
            content={
                "is_stuck": is_stuck,
                "confidence": 0.8,  # Blackbox doesn't expose confidence yet
                "model_available": True,
                "message": "Prediction successful"
            }
        )
        
    except Exception as e:
        print(f"ML prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ML prediction failed: {str(e)}"
        )

@app.post("/log-ml-feedback")
async def log_ml_feedback(request: MLFeedbackRequest):
    """
    Log feedback for ML model retraining.
    
    Expects:
    {
        "signals": { ... feature values ... },
        "was_stuck": true,
        "source": "manual"  // 'manual', 'confirmed', 'rejected'
    }
    """
    if not ML_AVAILABLE or not stuck_detector:
        return JSONResponse(
            content={
                "success": False,
                "message": "ML model not available"
            }
        )
    
    try:
        stuck_detector.log_feedback(
            signals=request.signals,
            was_stuck=request.was_stuck,
            # source=request.source
        )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Feedback logged successfully"
            }
        )
        
    except Exception as e:
        print(f"ML feedback logging error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to log ML feedback: {str(e)}"
        )

@app.post("/retrain-model")
async def retrain_model(force: bool = False):
    """
    Trigger ML model retraining if enough feedback has been collected.
    
    Query params:
    - force: boolean, force retraining even if threshold not met
    """
    if not ML_AVAILABLE or not stuck_detector:
        return JSONResponse(
            content={
                "success": False,
                "message": "ML model not available"
            }
        )
    
    try:
        stuck_detector.retrain_if_needed(force=force)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Model retrain check completed"
            }
        )
        
    except Exception as e:
        print(f"ML retraining error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model retraining failed: {str(e)}"
        )


# --- 7. ROOT ENDPOINT (FOR TESTING) ---

@app.get("/")
def read_root():
    return {
        "message": "Study Helper Backend is running!",
        "ml_available": ML_AVAILABLE,
        "endpoints": {
            "hint_generation": "/get-hint",
            "event_logging": "/log-stuck-event", 
            "ml_prediction": "/predict-stuck",
            "ml_feedback": "/log-ml-feedback",
            "ml_retraining": "/retrain-model"
        }
    }


# --- 8. SERVER STARTUP ---
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Study Helper Backend with ML integration...")
    print(f"🤖 ML System Available: {ML_AVAILABLE}")
    if stuck_detector:
        print(f"🧠 ML Model Type: {getattr(stuck_detector, 'model_type', 'unknown')}")
    print("📡 Server will be available at: http://localhost:8000")
    print("📋 API Documentation at: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)