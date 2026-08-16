from __future__ import annotations

import asyncio
import html
import secrets
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .agent import run_agent
from .security import PairingStore
from .state import Approval, SessionState

app = FastAPI(title="TerminalGPT Control Plane", version="0.1.0")
pairings = PairingStore()
sessions: dict[str, SessionState] = {}


class PromptRequest(BaseModel):
    token: str
    session_id: str
    message: str


class ApprovalRequest(BaseModel):
    token: str
    session_id: str
    approval_id: str
    approved: bool


async def require_session(token: str, session_id: str) -> SessionState:
    if not pairings.valid(token):
        raise HTTPException(401, "Invalid or expired pairing token")
    state = sessions.get(session_id)
    if not state:
        raise HTTPException(404, "Session not found")
    return state


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/pair", response_class=HTMLResponse)
async def pair(token: str):
    if not token:
        raise HTTPException(400, "Missing token")
    return f"""
<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>TerminalGPT Approval</title><style>body{{font-family:system-ui;max-width:900px;margin:40px auto;padding:0 20px}}button{{padding:12px 18px;margin:6px}}pre{{background:#111;color:#eee;padding:16px;overflow:auto}}</style></head>
<body><h1>TerminalGPT</h1><p>Browser approval console</p><pre id='out'>Connecting...</pre>
<script>
const token={token!r};
const qs=new URLSearchParams(location.search); const session=qs.get('session');
async function poll() {{ const r=await fetch('/api/state?token='+encodeURIComponent(token)+'&session_id='+encodeURIComponent(session)); const j=await r.json();
 document.getElementById('out').textContent=JSON.stringify(j,null,2); setTimeout(poll,1000); }} poll();
window.approve=async function(id,yes) {{ await fetch('/api/approve',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{token,session_id:session,approval_id:id,approved:yes}})}}); }};
</script></body></html>"""


@app.post("/api/session")
async def create_session():
    token = pairings.create()
    state = SessionState()
    sessions[state.session_id] = state
    state.emit("pairing_created", session_id=state.session_id)
    return {"token": token, "session_id": state.session_id, "pair_url": f"/pair?token={token}&session={state.session_id}"}


@app.get("/api/state")
async def get_state(token: str, session_id: str):
    state = await require_session(token, session_id)
    pending = [a.__dict__ for a in state.approvals.values() if not a.resolved]
    return {"session_id": session_id, "last_output": state.last_output, "events": state.events[-100:], "pending_approvals": pending}


@app.post("/api/approve")
async def approve(request: ApprovalRequest):
    state = await require_session(request.token, request.session_id)
    approval = state.approvals.get(request.approval_id)
    if not approval or approval.resolved:
        raise HTTPException(404, "Approval not found")
    approval.resolved = True
    approval.approved = request.approved
    state.emit("approval_resolved", approval_id=approval.id, approved=request.approved)
    state.resume_event.set()
    return {"ok": True}


@app.post("/api/prompt")
async def prompt(request: PromptRequest):
    state = await require_session(request.token, request.session_id)

    async def request_approval(command: str) -> bool:
        approval = Approval(id=secrets.token_urlsafe(12), command=command)
        state.approvals[approval.id] = approval
        state.emit("approval_required", approval_id=approval.id, command=command)
        state.resume_event.clear()
        await state.resume_event.wait()
        return approval.approved

    output = await run_agent(request.message, state, request_approval)
    return JSONResponse({"output": output})
