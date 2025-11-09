import os
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import SERVER_TIMESTAMP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Initialize Firebase Admin SDK ---

try:
    # Get the path to your service account key JSON file from .env
    key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")

    if not key_path:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY_PATH not set in .env")

    # Check if the app is already initialized (prevents crash on hot-reload)
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized.")
    
    # Get a reference to the Firestore database
    db = firestore.client()

except Exception as e:
    print(f"FATAL ERROR: Failed to initialize Firebase Admin SDK: {e}")
    print("Please check your .env file and the path to your service account key.")
    db = None

# --- Database Functions ---

def log_event(event_data: dict):
    """
    Logs a "stuck event" document to the 'stuckEvents' collection in Firestore.
    
    event_data (dict): A dictionary containing all data to be logged.
                       e.g., {"studentId": "...", "contextWord": "...", ...}
    """
    if db is None:
        print("Error: Firestore is not initialized. Cannot log event.")
        raise Exception("Firestore database is not available.")

    try:
        # Add a server-side timestamp for accurate logging
        event_data['timestamp'] = SERVER_TIMESTAMP
        
        # Add the data as a new document to the "stuckEvents" collection
        db.collection("stuckEvents").add(event_data)
        
        print(f"Successfully logged event for: {event_data.get('studentId')}")

    except Exception as e:
        print(f"Error writing to Firestore: {e}")
        # Re-raise the exception so the API endpoint can handle it
        raise