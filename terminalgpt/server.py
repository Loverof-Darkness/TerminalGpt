from __future__ import annotations

import secrets

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
async def pair(token: str, session: str):
    if not token or not session:
        raise HTTPException(400, "Missing pairing token or session")
    if session not in sessions:
        raise HTTPException(404, "Session not found")
    # The pairing URL is the single-use approval action. Once opened,
    # the token becomes valid for the lifetime of the paired session.
    if not pairings.approve(token):
        raise HTTPException(401, "Invalid, expired, or already-used pairing token")

    return f"""
<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>TerminalGPT Approval</title>
<style>
body{{font-family:system-ui;max-width:1000px;margin:40px auto;padding:0 20px;background:#0b0b0b;color:#eee}}
pre{{background:#151515;color:#eee;padding:16px;border-radius:10px;overflow:auto;white-space:pre-wrap}}
button{{padding:10px 16px;margin:4px;border:0;border-radius:8px;cursor:pointer}}
.approve{{background:#24a148;color:white}}.deny{{background:#da1e28;color:white}}
.card{{background:#151515;padding:18px;border-radius:12px;margin:14px 0}}
</style></head>
<body><h1>TerminalGPT</h1><p>Browser control and approval console</p>
<div class='card'><strong>Status:</strong> <span id='status'>Paired</span></div>
<div class='card'><h3>Terminal output</h3><pre id='out'>Connecting...</pre></div>
<div class='card'><h3>Pending commands</h3><div id='approvals'>None</div></div>
<script>
const token={token!r};
const session={session!r};
async function poll() {{
 try {{
  const r=await fetch('/api/state?token='+encodeURIComponent(token)+'&session_id='+encodeURIComponent(session));
  const j=await r.json();
  if (!r.ok) throw new Error(j.detail || 'Request failed');
  document.getElementById('out').textContent=j.last_output || JSON.stringify(j.events,null,2);
  const box=document.getElementById('approvals'); box.innerHTML='';
  if (!j.pending_approvals.length) box.textContent='None';
  for (const a of j.pending_approvals) {{
    const card=document.createElement('div'); card.className='card';
    const pre=document.createElement('pre'); pre.textContent=a.command;
    const yes=document.createElement('button'); yes.className='approve'; yes.textContent='Approve';
    const no=document.createElement('button'); no.className='deny'; no.textContent='Deny';
    yes.onclick=()=>resolve(a.id,true); no.onclick=()=>resolve(a.id,false);
    card.append(pre,yes,no); box.appendChild(card);
  }}
 }} catch(e) {{ document.getElementById('status').textContent='Error: '+e.message; }}
 setTimeout(poll,1000);
}}
async function resolve(id, approved) {{
 await fetch('/api/approve',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{token,session_id:session,approval_id:id,approved}})}});
}}
poll();
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
