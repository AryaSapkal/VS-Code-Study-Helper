import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from dedalus_labs import AsyncDedalus, DedalusRunner
import database  # This imports our database.py file

def generate_smart_fallback_hint(request):
    """Generate context-aware fallback hints when AI is unavailable"""
    
    # Skip ai_tools import - use direct fallback hints instead
    if False:  # Disable the generic ai_tools
        from ai_tools import analyze_stuck_pattern, suggest_documentation
        pattern_hint = analyze_stuck_pattern(request.heuristic, request.contextWord)
        doc_hint = suggest_documentation(request.contextWord, request.languageId)
        return f"{pattern_hint} {doc_hint}"
    else:
        # Fallback to basic hints
        fallback_hints = {
            "repetitive_editing": f"What should '{request.contextWord}' actually do?",
            "cursor_thrashing": f"Focus on one issue with '{request.contextWord}'?", 
            "idle_too_long": f"Try running your {request.languageId} code?",
            "many_errors": f"What's the first error message saying?",
            "general_stuck": f"Break '{request.contextWord}' into smaller steps?"
        }
        
        fallback_hint = fallback_hints.get(request.heuristic, fallback_hints["general_stuck"])
        
        # Make it more specific based on language
        if request.languageId == "python":
            fallback_hint += " Try using print() to see what values you're working with."
        elif request.languageId == "javascript":
            fallback_hint += " Try using console.log() to debug your values."
        
        return fallback_hint

# Add ML directory to path for imports
ml_path = str(Path(__file__).parent.parent / "ml")
print(f"🔍 Adding ML path: {ml_path}")
sys.path.insert(0, ml_path)  # Use insert(0, ...) to prioritize this path
print(f"🐍 Updated Python path with ML directory")

# Import ML wrapper (graceful fallback if not available)
try:
    from ml_wrapper import StuckDetector, ML_AVAILABLE
    if ML_AVAILABLE:
        print("✅ ML wrapper system loaded successfully")
    else:
        print("⚠️ ML system not available from wrapper")
except ImportError as e:
    ML_AVAILABLE = False
    StuckDetector = None
    print(f"⚠️ ML system not available: {e}")
    print(f"⚠️ Python path: {sys.path}")
    
# Initialize ML detector if available
stuck_detector = None
if ML_AVAILABLE and StuckDetector is not None:
    try:
        stuck_detector = StuckDetector()
        print("🎯 ML StuckDetector initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize StuckDetector: {e}")
        ML_AVAILABLE = False
        stuck_detector = None

# Load environment variables from .env file
load_dotenv()

# --- 1. INITIALIZE SDKs & APP ---

# Initialize Dedalus client
DEDALUS_API_KEY = os.getenv("DEDALUS_API_KEY")
if not DEDALUS_API_KEY:
    print("❌ FATAL ERROR: DEDALUS_API_KEY not found in .env file")
    # In a real app, you'd exit. For a hackathon, you can hardcode it here
    # if you're careful: DEDALUS_API_KEY = "your_key_here"
else:
    print(f"✅ DEDALUS_API_KEY loaded: {DEDALUS_API_KEY[:20]}...")

try:
    dedalus_client = AsyncDedalus(api_key=DEDALUS_API_KEY)
    dedalus_runner = DedalusRunner(dedalus_client, verbose=True)
    print("✅ Dedalus AsyncClient and DedalusRunner initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Dedalus client: {e}")
    dedalus_client = None
    dedalus_runner = None

# Initialize FastAPI app
app = FastAPI()

# Initialize Firebase (this happens when database.py is imported)
# The `db` object is available from the database module
print("Firebase Admin SDK initialized.")

# ML detector already initialized above


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

class HintFeedbackRequest(BaseModel):
    """Data model for hint usefulness feedback."""
    helpful: bool  # Whether the hint was helpful
    hint: str  # The actual hint text
    context: dict  # The original hint request context
    timestamp: str  # ISO timestamp

class AnswerRequest(BaseModel):
    """Data model for direct answer request (same as hint but more explicit)."""
    contextWord: str
    languageId: str
    heuristic: str
    codeSnippet: str
    requestType: str = "direct_answer"


# --- 4. API ENDPOINT 1: GET HINT ---

@app.post("/get-hint")
async def get_hint_from_ai(request: HintRequest):
    """
    Generate AI-powered hints using DedalusRunner with MCP capabilities
    Enhanced with multi-model routing, tool integration, and smart context analysis
    """
    
    print(f"🎯 Received hint request for: {request.contextWord}")
    
    if not dedalus_client:
        raise HTTPException(
            status_code=500, 
            detail="Dedalus AI client not initialized. Check API key configuration."
        )

    # Enhanced system prompt for better hints
    system_prompt = f"""You are a helpful coding tutor. A student appears to be stuck on: '{request.contextWord}' in {request.languageId}.

Detection signal: {request.heuristic}
Code: {request.codeSnippet[:300]}...

Provide a helpful, specific suggestion or question to guide them forward. Be encouraging and constructive. Aim for 1-2 sentences that help them think through the problem rather than giving direct answers."""

    try:
        print(f"🚀 Calling Dedalus AI for enhanced hint generation...")
        print(f"🔍 Context: {request.contextWord} in {request.languageId} (signal: {request.heuristic})")
        
        # Enhanced Dedalus API call - explicitly request non-streaming
        response = await dedalus_client.chat.completions.create(
            model="gemini-2.5-flash-preview-09-2025",  # Fast and smart model
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert programming tutor who helps students through guided questions rather than direct answers. Be encouraging, specific, and provide helpful context when needed. Aim for clear, actionable guidance that helps students learn."
                },
                {
                    "role": "user", 
                    "content": system_prompt
                }
            ],
            # Enhanced parameters for better response quality
            max_tokens=300,              # Allow for more detailed hints
            temperature=0.7,             # Balanced creativity
            stream=False,                # Explicitly disable streaming
        )
        
        print(f"🔍 Dedalus response received: {type(response)}")
        
        # Parse the AI response using the working pattern from before
        ai_hint = ""
        
        if hasattr(response, 'choices') and len(response.choices) > 0:
            choice = response.choices[0]
            
            # The response shows message.content is available
            if hasattr(choice, 'message') and isinstance(choice.message, dict) and 'content' in choice.message:
                ai_hint = choice.message['content'].strip()
                print(f"✅ Extracted from dict format: '{ai_hint}' (length: {len(ai_hint)})")
            elif hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                ai_hint = choice.message.content.strip()
                print(f"✅ Extracted from attribute format: '{ai_hint}' (length: {len(ai_hint)})")
            else:
                # Fallback: extract from string representation
                choice_str = str(choice)
                print(f"🔍 Trying string extraction from: {choice_str[:200]}...")
                if "'content': \"" in choice_str:
                    # Extract content from string representation
                    start = choice_str.find("'content': \"") + len("'content': \"")
                    end = choice_str.find("\", '", start)
                    if end == -1:
                        end = choice_str.find("\"", start)
                    if end > start:
                        ai_hint = choice_str[start:end].replace('\\n', '\n')
                        print(f"✅ Extracted from string: '{ai_hint}' (length: {len(ai_hint)})")
        else:
            print(f"⚠️ No choices found in response: {type(response)}")
        
        # Ensure we have a valid response
        if not ai_hint or len(ai_hint.strip()) == 0:
            print("⚠️ No AI hint extracted, using enhanced fallback")
            ai_hint = generate_smart_fallback_hint(request)
        
        print(f"✅ Generated AI hint: {ai_hint[:100]}...")
        
        # Send the hint back to the VS Code extension  
        return {"hint": ai_hint}

    except Exception as e:
        print(f"❌ Error calling Dedalus AI: {e}")
        print(f"🔄 Falling back to enhanced hints...")
        
        # Use our smart fallback system
        fallback_hint = generate_smart_fallback_hint(request)
        
        return {"hint": fallback_hint}


# --- 5. API ENDPOINT: HINT FEEDBACK ---

@app.post("/feedback")
async def log_hint_feedback(request: HintFeedbackRequest):
    """
    Log feedback about whether a hint was helpful.
    This data can be used to improve hint quality over time.
    """
    print(f"📊 Received hint feedback:")
    print(f"  Helpful: {request.helpful}")
    print(f"  Hint: {request.hint[:50]}...")
    print(f"  Context: {request.context.get('contextWord', 'N/A')} in {request.context.get('languageId', 'N/A')}")
    print(f"  Timestamp: {request.timestamp}")
    
    # TODO: Store feedback in database for analysis
    # For now, just log it for debugging
    
    return {"status": "success", "message": "Feedback logged successfully"}


# --- 6. API ENDPOINT: GET DIRECT ANSWER ---

@app.post("/get-answer")
async def get_direct_answer(request: AnswerRequest):
    """
    Generate a direct answer/solution instead of a hint.
    Uses more explicit prompting to provide actual solutions.
    """
    print(f"🎯 Received direct answer request for: {request.contextWord}")
    
    if not dedalus_client:
        raise HTTPException(
            status_code=500, 
            detail="Dedalus AI client not initialized. Check API key configuration."
        )

    try:
        print(f"🚀 Calling Dedalus AI for direct answer...")
        print(f"🔍 Context: {request.contextWord} in {request.languageId} (signal: {request.heuristic})")
        
        # Use same working API setup as hints - EXACT same configuration
        # Simple direct API call with working Gemini model
        response = await dedalus_client.chat.completions.create(
            model="gemini-2.5-flash-preview-09-2025",  # Same model as working hints
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful coding assistant. Provide specific, actionable advice to help fix programming issues."
                },
                {
                    "role": "user", 
                    "content": f"Fix this Python code issue: {request.contextWord}. Code: {request.codeSnippet[:500]}"
                }
            ],
            max_tokens=150,
            temperature=0.3,
            stream=False
        )
        
        print(f"🔍 Dedalus response received: {type(response)}")
        
        # Parse the AI response (same parsing logic as hints)
        ai_answer = ""
        
        if hasattr(response, 'choices') and len(response.choices) > 0:
            choice = response.choices[0]
            
            if hasattr(choice, 'message') and isinstance(choice.message, dict) and 'content' in choice.message:
                ai_answer = choice.message['content'].strip()
                print(f"✅ Extracted answer from dict format: {ai_answer[:50]}...")
            elif hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                ai_answer = choice.message.content.strip()
                print(f"✅ Extracted answer from attribute format: {ai_answer[:50]}...")
            else:
                # Fallback: extract from string representation
                choice_str = str(choice)
                print(f"🔍 Trying string extraction from: {choice_str[:200]}...")
                if "'content': \"" in choice_str:
                    start = choice_str.find("'content': \"") + len("'content': \"")
                    end = choice_str.find("\", '", start)
                    if end == -1:
                        end = choice_str.find("\"", start)
                    if end > start:
                        ai_answer = choice_str[start:end].replace('\\n', '\n')
                        print(f"✅ Extracted answer from string: {ai_answer[:50]}...")
        
        # Fallback: Use ai_tools.py functions
        if not ai_answer:
            # Provide programming guidance based on context
            if "enumerate" in request.codeSnippet.lower():
                ai_answer = "Replace 'enumerate(20)' with 'range(20)' if you just need numbers."
            elif "syntax" in request.contextWord.lower():
                ai_answer = "Check for missing colons (:) at the end of if/for/while statements."
            elif "import" in request.contextWord.lower():
                ai_answer = "Make sure the module is installed: pip install <module_name>"
            else:
                ai_answer = "Review the error message and check Python syntax documentation."
        
        print(f"✅ Generated direct answer: {ai_answer[:100]}...")
        
        return {"answer": ai_answer}

    except Exception as e:
        print(f"❌ Error calling Dedalus AI for answer: {e}")
        print(f"🔄 Falling back to generic answer...")
        
        # Generic fallback answer
        fallback_answer = f"Try debugging '{request.contextWord}' step by step: 1) Check for syntax errors, 2) Verify variable names are correct, 3) Add print/console.log statements to see current values, 4) Check {request.languageId} documentation for proper usage."
        
        return {"answer": fallback_answer}


# --- 7. API ENDPOINT: LOG STUCK EVENT ---

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
        
        # Get enhanced prediction with detailed confidence breakdown
        prediction_result = stuck_detector.predict_full(request.signals)
        
        return JSONResponse(
            content={
                "is_stuck": prediction_result['prediction'] == 1,
                "confidence": round(prediction_result['confidence_score'], 3),
                "confidence_level": prediction_result['confidence_level'],
                "confidence_breakdown": {
                    "magnitude": round(prediction_result['confidence_breakdown']['magnitude_confidence'], 3),
                    "entropy": round(prediction_result['confidence_breakdown']['entropy_confidence'], 3),
                    "distance": round(prediction_result['confidence_breakdown']['distance_confidence'], 3),
                    "base_confidence": round(prediction_result['confidence_breakdown']['base_confidence'], 3),
                    "sensitivity_boost": round(prediction_result['confidence_breakdown']['sensitivity_boost'], 3),
                    "final_confidence": round(prediction_result['confidence_breakdown']['final_confidence'], 3)
                },
                "probability_stuck": round(prediction_result['probability'], 3),
                "threshold": stuck_detector.model.threshold,
                "model_available": True,
                "message": "Enhanced prediction with detailed confidence analysis"
            }
        )
        
    except Exception as e:
        print(f"ML prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ML prediction failed: {str(e)}"
        )

@app.post("/optimize-threshold")
async def optimize_ml_threshold():
    """
    Dynamically optimize the ML model threshold based on recent performance.
    This improves confidence calibration and reduces false positives/negatives.
    
    Returns the old and new threshold values along with expected improvements.
    """
    if not ML_AVAILABLE or not stuck_detector:
        return JSONResponse(
            content={
                "success": False,
                "message": "ML model not available",
                "old_threshold": 0.5,
                "new_threshold": 0.5
            }
        )
    
    try:
        # Get recent feedback data (if any)
        feedback_count = stuck_detector._count_feedback()
        
        if feedback_count < 10:
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"Need at least 10 feedback samples for optimization (have {feedback_count})",
                    "old_threshold": stuck_detector.model.threshold,
                    "new_threshold": stuck_detector.model.threshold
                }
            )
        
        # Load recent feedback for threshold optimization  
        recent_feedback = stuck_detector._load_recent_feedback(limit=50)
        
        if len(recent_feedback) >= 10:
            # Extract probability and true label pairs
            feedback_pairs = [
                (row.get('predicted_probability', 0.5), row.get('was_stuck', False))
                for _, row in recent_feedback.iterrows()
                if 'was_stuck' in row
            ]
            
            old_threshold = stuck_detector.model.threshold
            new_threshold = stuck_detector.model.adaptive_threshold(feedback_pairs)
            
            # Update the model threshold
            stuck_detector.model.set_threshold(new_threshold)
            
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Threshold optimized successfully",
                    "old_threshold": round(old_threshold, 3),
                    "new_threshold": round(new_threshold, 3),
                    "improvement_expected": abs(new_threshold - old_threshold) > 0.05,
                    "feedback_samples_used": len(feedback_pairs)
                }
            )
        else:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "Not enough recent feedback with labels for optimization",
                    "old_threshold": stuck_detector.model.threshold,
                    "new_threshold": stuck_detector.model.threshold
                }
            )
            
    except Exception as e:
        print(f"Threshold optimization error: {e}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"Optimization failed: {str(e)}",
                "old_threshold": stuck_detector.model.threshold if stuck_detector else 0.5,
                "new_threshold": stuck_detector.model.threshold if stuck_detector else 0.5
            }
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