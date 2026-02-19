import re
import joblib
import os
import io
import streamlit as st
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION & PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "model_lr.pkl")

@st.cache_resource
def load_assets():
    """
    Loads the SentenceTransformer and the Logistic Regression model.
    Includes a binary repair fix for cross-platform (Windows/Linux) pickle issues.
    """
    # 1. Load Sentence Transformer Embedder
    try:
        # Note: This may take a moment on first run to download/initialize
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        st.error(f"❌ Failed to load SentenceTransformer: {e}")
        return None, None

    # 2. Verify Model File Path
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️ CRITICAL: Model file NOT found at {MODEL_PATH}")
        return None, embedder

    # 3. Load the Logistic Regression Classifier
    try:
        model = joblib.load(MODEL_PATH)
        return model, embedder
    except Exception as e:
        # In-memory binary repair for 'joblib\x0d' or Windows/Unix line ending issues
        try:
            with open(MODEL_PATH, 'rb') as f:
                content = f.read()
            
            # Binary cleaning of the pickle file content
            fixed_content = content.replace(b'\r\n', b'\n').replace(b'joblib\x0d', b'joblib')
            model = joblib.load(io.BytesIO(fixed_content))
            return model, embedder
        except Exception as repair_error:
            st.error(f"❌ AI Model load failed even after repair: {repair_error}")
            return None, embedder

# Initialize assets
model_lr, embedder = load_assets()

def predict_log(log_message):
    """
    Hybrid Classification: 
    1. Checks Regex for high-confidence matches.
    2. Falls back to AI Embedding + Logistic Regression if model is loaded.
    """
    log_str = str(log_message).strip()
    if not log_str:
        return "Empty Log", "N/A"

    # --- LAYER 1: REGEX ENGINE ---
    regex_patterns = {
        # SECURITY & ACCESS
        r"Unauthorized access|Access denied|Permission denied": "Security Alert",
        r"Brute-force|Login attempt failed|Too many login attempts": "Security Alert",
        r"Password (reset|changed|expired)|Credentials updated": "Security Alert",
        r"SQL Injection|Cross-site scripting|XSS|Exploit": "Security Alert",
        r"Firewall (blocked|dropped)|Port scan detected": "Security Alert",
        r"SSH login failure|Invalid SSH key": "Security Alert",

        # DATABASE & STORAGE
        r"Database (connection|query|pool) (failed|refused|timeout|error|closed)": "Critical Error",
        r"Deadlock detected|Transaction aborted|Integrity constraint": "Critical Error",
        r"MongoDB|MySQL|PostgreSQL|Redis|Oracle (Error|Down)": "Critical Error",
        r"Disk (full|quota exceeded)|No space left on device": "Resource Warning",
        r"I/O error|Read-only file system|Corrupt block": "Critical Error",
        r"Migration (failed|aborted)|Schema mismatch": "System Notification",

        # WEB & NETWORK
        r"returned [45]\d{2}": "Web Error",
        r"returned [23]\d{2}": "Web Success",
        r"DNS (lookup|resolution) failed|Host unreachable": "Network Issue",
        r"Connection (timed out|reset|refused by peer)": "Network Issue",
        r"Gateway Timeout|Bad Gateway|Proxy Error": "Web Error",
        r"SSL (certificate|handshake) (failed|expired|invalid)": "Security Alert",
        r"API (Rate limit|Throttled|Quota exceeded)": "Resource Warning",

        # SYSTEM & HARDWARE
        r"Memory usage (high|critical)|Out of memory|OOM killer": "Resource Warning",
        r"CPU (load|temperature) (high|exceeded)|Thermal throttling": "Resource Warning",
        r"Kernel panic|Segmentation fault|Core dumped": "Critical Error",
        r"Service (started|stopped|restarted|crashed)": "System Notification",
        r"System updated to version|Patch applied": "System Notification",
        r"Hardware failure|Fan speed low|Voltage drop": "Critical Error",

        # USER ACTION
        r"User User\d+ logged (in|out)|Session (started|ended)": "User Action",
        r"Account (created|deleted|suspended|activated)": "User Action",
        r"File (uploaded|downloaded|deleted|moved)": "User Action",
        r"Backup (started|ended|failed|completed)": "System Notification",
        r"Task (queued|processing|finished|retrying)": "System Notification",
        r"Payment (processed|failed|refunded)|Order #\d+": "User Action",
        r"(User|Account|Profile) .* (cannot|failed to) be created": "Application Error",
r"Validation failed for user creation": "Application Error",# Add these to logic.py to catch your specific examples
    
    # 1. Catching failures (Application Error)
    r"(User|Account|Profile) .* (cannot|failed|unable)": "Application Error",
    
    # 2. Catching successful creation (User Action)
    r"(User|Account|Profile) .* (created|registered|signed up)": "User Action",
    # 1. CRITICAL FAILURES (Check these first!)
        r"cannot be created: (DB|Database|SQL|Timeout)": "Critical Error",
        r"Kernel panic|Segmentation fault|Core dumped": "Critical Error",
        r"Database (connection|query|pool) (failed|refused|timeout)": "Critical Error",

        # 2. APPLICATION ERRORS (Negations/Failures)
        r"(User|Account|Profile|Task) .* (cannot|failed|unable|error|rejected)": "Application Error",
        r"Validation (failed|error)|Invalid (input|credentials)": "Application Error",
        r"returned [45]\d{2}": "Web Error", 

        # 3. SECURITY ALERTS
        r"Unauthorized|Access denied|Brute-force|SQL Injection": "Security Alert",
        r"JWT (expired|invalid)|MFA failure": "Security Alert",

        # 4. SUCCESSFUL USER ACTIONS (Standard flow)
        r"User User\d+ logged (in|out)|Session (started|ended)": "User Action",
        r"Account (created|registered|activated|signed up)": "User Action",
        r"File (uploaded|downloaded|moved)": "User Action",
        r"Payment (processed|completed)|Order #\d+": "User Action",

        # 5. SYSTEM NOTIFICATIONS
        r"Backup (started|completed)|Task (finished|queued)": "System Notification",
        r"Service (started|restarted)": "System Notification",
        r"System updated to version|Patch applied": "System Notification",
    
    # 3. Catching Database-related failures (Critical Error)
    # This must come BEFORE the general "cannot be created" rule to take priority
    r"cannot be created: (DB|Database|SQL|Timeout)": "Critical Error",
        # --- WEB SERVICES & API ---
    r"GraphQL (query|mutation) (failed|invalid)": "Application Error",
    r"CORS (policy|origin) (blocked|rejected)": "Security Alert",
    r"Webhook (delivery failed|retry limit)": "System Notification",
    r"Request body too large|413 Payload": "Resource Warning",
    r"429 Too Many Requests|Rate limit": "Resource Warning",

    # --- IAM & AUTH ---
    r"JWT (expired|invalid|malformed)": "Security Alert",
    r"OAuth (error|callback failed)": "Security Alert",
    r"LDAP (bind failed|unreachable)": "Critical Error",
    r"User (locked out|disabled)|MFA failure": "Security Alert",

    # --- MESSAGING QUEUES ---
    r"Kafka (broker disconnected|rebalance)": "Critical Error",
    r"RabbitMQ (queue full|consumer timeout)": "Resource Warning",
    r"Pub/Sub (ack deadline|retry)": "System Notification",
    r"Buffer overflow|Message dropped": "Resource Warning",

    # --- FRONTEND & CLIENT ---
    r"React (hydration failed|boundary error)": "Application Error",
    r"ChunkLoadError|Script error": "Application Error",
    r"Local storage (full|denied)": "System Notification",

    # --- AUDIT & COMPLIANCE ---
    r"Sensitive data detected|PII leak": "Security Alert",
    r"Audit log (tampering|gap)": "Security Alert",
    r"GDPR (deletion|export) (started|completed)": "User Action",
    r"Insecure protocol|Weak cipher": "Security Alert",

    # --- OS & NETWORK INTERNALS ---
    r"Out of file descriptors|ulimit reached": "Critical Error",
    r"Zombie process detected|PID limit reached": "Resource Warning",
    r"Network interface (down|flap|saturated)": "Network Issue",
    r"Packet loss > \d+%|High latency detected": "Network Issue"
    }

    for pattern, label in regex_patterns.items():
        if re.search(pattern, log_str, re.IGNORECASE):
            return label, "Regex Engine"

    # --- LAYER 2: AI ENGINE (Fallback) ---
    if model_lr and embedder:
        try:
            embedding = embedder.encode([log_str])
            prediction = model_lr.predict(embedding)[0]
            return prediction, "AI Model (Sentence Transformer)"
        except Exception as e:
            return "Error", f"AI Prediction Failed: {e}"
    
    # Final Fallback if AI isn't loaded
    return "Unknown", "Logic Error: Model not loaded"