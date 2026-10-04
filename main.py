from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import threading

# Voeg het RAJAN project toe aan het pad zodat we de modules kunnen importeren
RAJAN_PATH = os.path.expanduser("~/msf-app/sliver/RAJAN")
if RAJAN_PATH not in sys.path:
    sys.path.append(RAJAN_PATH)

from core.memory import Memory
from core.llm import LLMConnector
from core.logger import Logger
from core.brain import Brain

app = FastAPI()

# Sta toe dat je Vercel-app verbinding mag maken
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In productie strenger maken!
    allow_methods=["*"],
    allow_headers=["*"],
)

# Houd bij welke scans er actief zijn in het geheugen
active_scans = {}


# ---------- Bestaande modellen ----------
class ConnectionInfo(BaseModel):
    ip: str
    password: str


# ---------- Nieuwe modellen voor RAJAN ----------
class ScanRequest(BaseModel):
    target: str
    scope: str = ""
    mode: str = "auto"  # "auto" of "semi"


# ---------- Achtergrond functie om RAJAN te draaien ----------
def run_rajan_scan(session_id: str, target: str, scope: str, mode: str):
    """Draait de RAJAN Brain in een aparte thread."""
    try:
        memory = Memory()
        llm = LLMConnector()
        logger = Logger()
        
        # Zorg dat de logger weet welke sessie het is
        logger.session_id = session_id
        logger.memory = memory

        brain = Brain(memory, llm, logger, session_id)
        brain.start_autonomous(target, scope, mode)
        
    except Exception as e:
        print(f"[RAJAN] Scan error in session {session_id}: {e}")
    finally:
        # Markeer de scan als voltooid in het geheugen
        active_scans[session_id] = "completed"


# ---------- Bestaande Endpoints ----------
@app.get("/")
def read_root():
    return {"status": "MSF Backend is online", "rajan": "ready"}


@app.post("/api/connect")
def connect_to_server(info: ConnectionInfo):
    print(f"Poging tot verbinden met {info.ip} met wachtwoord {info.password}")
    return {"success": True, "message": "Verbinding succesvol (gesimuleerd)"}


# ---------- Nieuwe RAJAN Endpoints ----------
@app.post("/api/rajan/scan")
def start_rajan_scan(request: ScanRequest):
    """Start een nieuwe RAJAN scan op de achtergrond."""
    memory = Memory()
    
    # Maak een nieuwe sessie aan in de SQLite database
    session_id = memory.create_session(request.target, request.scope)
    active_scans[session_id] = "running"

    # Start de scan in een aparte thread
    thread = threading.Thread(
        target=run_rajan_scan,
        args=(session_id, request.target, request.scope, request.mode),
        daemon=True
    )
    thread.start()

    return {
        "success": True,
        "session_id": session_id,
        "message": f"RAJAN scan gestart op {request.target}",
        "status": "running"
    }


@app.get("/api/rajan/status/{session_id}")
def get_scan_status(session_id: str):
    """Haal de live status en bevindingen van een scan op."""
    memory = Memory()
    session = memory.get_session(session_id)
    
    if not session:
        return {"success": False, "error": "Sessie niet gevonden"}

    findings = memory.get_findings(session_id)
    counts = memory.count_findings(session_id)

    return {
        "success": True,
        "session_id": session_id,
        "target": session["target"],
        "scope": session.get("scope", ""),
        "status": active_scans.get(session_id, session["status"]),
        "findings_count": len(findings),
        "severity_counts": counts,
        "findings": findings
    }


@app.get("/api/rajan/sessions")
def list_rajan_sessions():
    """Lijst van alle eerdere scans."""
    memory = Memory()
    sessions = memory.get_all_sessions()
    return {
        "success": True,
        "sessions": [
            {"id": s[0], "target": s[1], "status": s[2], "started": s[3]} 
            for s in sessions
        ]
    }