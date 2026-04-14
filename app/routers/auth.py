"""
Auth endpoints — thin proxy to Supabase Auth.

Covers the full email flow:
  POST /auth/register          — sign up (sends confirmation email)
  POST /auth/login             — sign in with email + password
  POST /auth/reset-password    — send password reset email
  POST /auth/update-password   — set new password after reset (uses recovery token)
  GET  /auth/confirm           — handle email confirmation & password reset callbacks
                                  (Supabase redirects here after user clicks email link)
"""
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings
from app.models import (
    LoginRequest,
    OtpVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    ResendOtpRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdatePasswordRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_url(path: str) -> str:
    return f"{get_settings().supabase_url}/auth/v1/{path}"


def _headers() -> dict:
    return {
        "apikey": get_settings().supabase_secret_key,
        "Content-Type": "application/json",
    }


# ── Register ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, request: Request) -> TokenResponse:
    """
    Create a new account. Supabase sends a confirmation email.
    If email confirmation is disabled in Supabase, a session is returned immediately.
    """
    redirect_to = str(request.base_url) + "auth/confirm"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _auth_url("signup"),
            headers=_headers(),
            json={
                "email": payload.email,
                "password": payload.password,
                "data": {"name": payload.name or payload.email},
                "options": {"email_redirect_to": redirect_to},
            },
        )

    if resp.status_code not in (200, 201):
        body = resp.json()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=body.get("msg") or body.get("error_description") or "Registration failed",
        )

    data = resp.json()
    session = data.get("session") or {}
    return TokenResponse(
        access_token=session.get("access_token", ""),
        token_type="bearer",
        expires_in=session.get("expires_in"),
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    """Authenticate with email + password and return a Supabase JWT."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _auth_url("token?grant_type=password"),
            headers=_headers(),
            json={"email": payload.email, "password": payload.password},
        )

    if resp.status_code != 200:
        body = resp.json()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=body.get("error_description") or "Invalid credentials",
        )

    data = resp.json()
    return TokenResponse(
        access_token=data["access_token"],
        token_type="bearer",
        expires_in=data.get("expires_in"),
        refresh_token=data.get("refresh_token"),
    )


# ── Token refresh ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest) -> TokenResponse:
    """Exchange a refresh token for a new access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _auth_url("token?grant_type=refresh_token"),
            headers=_headers(),
            json={"refresh_token": payload.refresh_token},
        )

    if resp.status_code != 200:
        body = resp.json()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=body.get("error_description") or "Invalid or expired refresh token",
        )

    data = resp.json()
    return TokenResponse(
        access_token=data["access_token"],
        token_type="bearer",
        expires_in=data.get("expires_in"),
        refresh_token=data.get("refresh_token"),
    )


# ── Password reset request ────────────────────────────────────────────────────

@router.post("/reset-password", status_code=204)
async def reset_password(payload: ResetPasswordRequest, request: Request) -> None:
    """
    Send a password reset email. Supabase emails a link that points back to
    GET /auth/confirm?token_hash=...&type=recovery
    """
    redirect_to = str(request.base_url) + "auth/confirm"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _auth_url("recover"),
            headers=_headers(),
            json={"email": payload.email, "redirect_to": redirect_to},
        )

    # Always return 204 — don't leak whether the email exists
    if resp.status_code not in (200, 201, 204):
        logger.warning("Supabase recover returned %s: %s", resp.status_code, resp.text)


# ── Update password (after recovery) ─────────────────────────────────────────

@router.post("/update-password", response_model=TokenResponse)
async def update_password(payload: UpdatePasswordRequest) -> TokenResponse:
    """
    Set a new password using the access token obtained from the recovery callback.
    Call this after the user has been redirected to /auth/confirm?type=recovery
    and the dashboard has extracted the access_token from the URL fragment.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            _auth_url("user"),
            headers={**_headers(), "Authorization": f"Bearer {payload.access_token}"},
            json={"password": payload.password},
        )

    if resp.status_code != 200:
        body = resp.json()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=body.get("msg") or body.get("error_description") or "Password update failed",
        )

    data = resp.json()
    # Supabase returns a user object; the same token remains valid
    return TokenResponse(
        access_token=payload.access_token,
        token_type="bearer",
    )


# ── Verify signup OTP ────────────────────────────────────────────────────────

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(payload: OtpVerifyRequest) -> TokenResponse:
    """
    Verify the 6-digit OTP code sent to the user's email during signup.
    Returns a full session on success.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _auth_url("verify"),
            headers=_headers(),
            json={"type": "signup", "email": payload.email, "token": payload.token},
        )

    if resp.status_code != 200:
        body = resp.json()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=body.get("msg") or body.get("error_description") or "Invalid or expired code",
        )

    data = resp.json()
    session = data.get("session") or data
    return TokenResponse(
        access_token=session.get("access_token", ""),
        token_type="bearer",
        expires_in=session.get("expires_in"),
        refresh_token=session.get("refresh_token"),
    )


# ── Resend signup OTP ─────────────────────────────────────────────────────────

@router.post("/resend-otp", status_code=204)
async def resend_otp(payload: ResendOtpRequest) -> None:
    """Resend the signup confirmation OTP to the given email address."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _auth_url("resend"),
            headers=_headers(),
            json={"type": "signup", "email": payload.email},
        )

    if resp.status_code not in (200, 201, 204):
        logger.warning("Supabase resend OTP returned %s: %s", resp.status_code, resp.text)
        body = resp.json() if resp.content else {}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=body.get("msg") or body.get("error_description") or "Failed to resend code",
        )


# ── Email callback (confirm / recovery) ───────────────────────────────────────

_CONFIRM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DeepRaven</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           display:flex; align-items:center; justify-content:center; height:100vh;
           margin:0; background:#f8fafc; color:#1e293b; }}
    .card {{ background:#fff; border:1px solid #e2e8f0; border-radius:12px;
             padding:36px 32px; width:360px; text-align:center;
             box-shadow:0 4px 24px rgba(0,0,0,.07); }}
    h2 {{ margin:0 0 8px; font-size:20px; }}
    p  {{ color:#64748b; font-size:14px; margin:0 0 20px; }}
    input {{ width:100%; padding:9px 12px; border:1px solid #e2e8f0;
             border-radius:7px; font-size:14px; outline:none; box-sizing:border-box;
             margin-bottom:10px; }}
    input:focus {{ border-color:#6366f1; }}
    button {{ width:100%; padding:10px; background:#6366f1; color:#fff;
              border:none; border-radius:7px; font-size:14px; font-weight:600;
              cursor:pointer; }}
    button:hover {{ background:#4f46e5; }}
    button:disabled {{ opacity:.5; cursor:not-allowed; }}
    .msg {{ font-size:13px; margin-top:10px; }}
    .ok  {{ color:#16a34a; }}
    .err {{ color:#dc2626; }}
  </style>
</head>
<body>
<div class="card">
  <h2 id="title">{title}</h2>
  <p id="sub">{sub}</p>
  <div id="form-area">{form}</div>
  <div id="msg" class="msg"></div>
</div>
<script>
  // Extract access_token from URL fragment (Supabase puts it there)
  const params = new URLSearchParams(window.location.hash.replace('#', ''));
  const token  = params.get('access_token') || new URLSearchParams(window.location.search).get('access_token');
  const type   = '{type}';

  if (type === 'recovery' && !token) {{
    document.getElementById('sub').textContent = 'Missing token. Please request a new reset link.';
    document.getElementById('form-area').innerHTML = '';
  }}

  async function submit() {{
    const pw  = document.getElementById('pw').value;
    const pw2 = document.getElementById('pw2').value;
    const msg = document.getElementById('msg');
    const btn = document.getElementById('btn');
    if (!pw || pw.length < 6) {{ msg.className='msg err'; msg.textContent='Password must be at least 6 characters.'; return; }}
    if (pw !== pw2) {{ msg.className='msg err'; msg.textContent='Passwords do not match.'; return; }}
    btn.disabled = true; btn.textContent = 'Updating…';
    try {{
      const resp = await fetch('/api/v1/auth/update-password', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ access_token: token, password: pw }}),
      }});
      if (!resp.ok) {{ const d = await resp.json(); throw new Error(d.detail || 'Failed'); }}
      msg.className='msg ok'; msg.textContent='Password updated! Redirecting…';
      document.getElementById('form-area').innerHTML = '';
      setTimeout(() => window.location.href = '/dashboard', 1800);
    }} catch(e) {{
      msg.className='msg err'; msg.textContent=e.message;
      btn.disabled=false; btn.textContent='Update password';
    }}
  }}
</script>
</body>
</html>"""


@router.get("/confirm", include_in_schema=False)
async def auth_confirm(
    request: Request,
    token_hash: str = "",
    type: str = "",
    error: str = "",
    error_description: str = "",
) -> HTMLResponse:
    """
    Supabase redirects here after the user clicks an email confirmation or
    password reset link. Handles both flows:

    - type=email      → verify token, then redirect to /dashboard
    - type=recovery   → show set-new-password form
    """
    if error:
        logger.warning("Auth callback error: %s — %s", error, error_description)
        return HTMLResponse(
            _CONFIRM_HTML.format(
                title="Link expired",
                sub=error_description or error,
                form='<a href="/dashboard">Back to dashboard</a>',
                type="error",
            )
        )

    # ── Email confirmation ────────────────────────────────────────────────────
    if type == "email":
        if not token_hash:
            return RedirectResponse("/dashboard")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _auth_url("verify"),
                headers=_headers(),
                json={"token_hash": token_hash, "type": "email"},
            )

        if resp.status_code == 200:
            return RedirectResponse("/dashboard?confirmed=1")

        body = resp.json()
        logger.warning("Email confirm failed: %s", body)
        return HTMLResponse(
            _CONFIRM_HTML.format(
                title="Confirmation failed",
                sub=body.get("msg") or body.get("error_description") or "This link may have expired.",
                form='<a href="/dashboard">Back to dashboard</a>',
                type="error",
            )
        )

    # ── Password recovery ─────────────────────────────────────────────────────
    if type == "recovery":
        # Supabase puts the access_token in the URL fragment (#access_token=...)
        # The browser JS in the page extracts it and calls /auth/update-password.
        return HTMLResponse(
            _CONFIRM_HTML.format(
                title="Set new password",
                sub="Enter your new password below.",
                form="""
                  <input type="password" id="pw"  placeholder="New password">
                  <input type="password" id="pw2" placeholder="Confirm password">
                  <button id="btn" onclick="submit()">Update password</button>
                """,
                type="recovery",
            )
        )

    # Fallback — unknown type, just go to dashboard
    return RedirectResponse("/dashboard")
