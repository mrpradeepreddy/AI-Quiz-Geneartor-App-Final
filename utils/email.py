# In file: utils/email.py

import os
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from models.user import User # Import your SQLAlchemy User model

load_dotenv()

# --- Connection Configuration ---
# This is shared by all email functions in this file.
def _must_get(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default)
    if val in (None, ""):
        raise RuntimeError(f"Missing required email configuration: {key}")
    return val

try:
    conf = ConnectionConfig(
        MAIL_USERNAME=_must_get("MAIL_USERNAME"),
        MAIL_PASSWORD=_must_get("MAIL_PASSWORD"),
        MAIL_FROM=_must_get("MAIL_FROM"),
        MAIL_PORT=int(_must_get("MAIL_PORT", "587")),
        MAIL_SERVER=_must_get("MAIL_SERVER"),
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False
    )
except Exception as e:
    # Fallback dummy config to avoid crashes; actual send will error with clear message
    conf = None
    print(f"[Email Config] WARNING: Email configuration invalid: {e}")

# --- FUNCTION 1: For Welcoming New Users ---
async def send_welcome_email(email: EmailStr, username: str):
    """
    Sends a standard welcome email to any newly registered user.
    """
    html_content = f"""
    <html>
        <body>
            <h2>Welcome, {username}!</h2>
            <p>Thank you for registering for our amazing quiz app.</p>
            <p>You can now log in and get started. Good luck!</p>
        </body>
    </html>
    """

    message = MessageSchema(
        subject="Welcome to the FastAPI Quiz App! 🎉",
        recipients=[email],
        body=html_content,
        subtype="html"
    )

    if conf is None:
        print("[Email] Skipping send_welcome_email: email config not set")
        return
    fm = FastMail(conf)
    await fm.send_message(message)

# --- FUNCTION 2: For Recruiter Invitations ---
async def send_invite_email(recipient_email: str, recruiter: User, invitation_link: str):
    """
    Sends a personalized quiz invite with a unique link.
    """

    # UPDATED: Include recruiter code in the invitation link for auto-linking
    recruiter_code_param = ""
    if recruiter.recruiter_code:
        # Add recruiter code as query parameter for auto-linking
        separator = "&" if "?" in invitation_link else "?"
        recruiter_code_param = f"{separator}recruiter_code={recruiter.recruiter_code}"
    
    full_invitation_link = invitation_link + recruiter_code_param

    # UPDATED: The HTML content now includes the full invitation link with recruiter code
    html_content = f"""
    <html>
        <body>
            <h3>Hi there,</h3>
            <p>
                {recruiter.name} has invited you to take a quiz on our platform.
            </p>
            <p>
                Please click the link below to begin:
                <br>
                <a href="{full_invitation_link}">{full_invitation_link}</a>
            </p>
            <p>
                <strong>Note:</strong> This link will automatically link you to {recruiter.name}'s recruiter account 
                and make all their assessments available to you.
            </p>
            <p>Good luck!</p>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject=f"Quiz Invitation from {recruiter.name}",
        recipients=[recipient_email],
        body=html_content,
        subtype="html",
        headers={"Reply-To": recruiter.email},
        sender=(f"{recruiter.name} (via QuizApp)", conf.MAIL_FROM)
    )

    if conf is None:
        print("[Email] Skipping send_invite_email: email config not set")
        return
    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        print(f"--- Email successfully sent to {recipient_email} ---")
    except Exception as e:
        print(f"!!! FAILED TO SEND EMAIL TO {recipient_email} !!!")
        print(f"ERROR: {e}")