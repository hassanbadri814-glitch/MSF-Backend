from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Sta toe dat je Vercel-app verbinding mag maken
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In productie strenger maken!
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionInfo(BaseModel):
    ip: str
    password: str

@app.get("/")
def read_root():
    return {"status": "MSF Backend is online"}

@app.post("/api/connect")
def connect_to_server(info: ConnectionInfo):
    # Voor nu doen we alsof het lukt. Later praten we hier met Metasploit.
    print(f"Poging tot verbinden met {info.ip} met wachtwoord {info.password}")
    return {"success": True, "message": "Verbinding succesvol (gesimuleerd)"}