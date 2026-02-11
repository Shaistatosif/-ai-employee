"""Quick test to send email via Gmail API."""
import pickle
import base64
from email.mime.text import MIMEText
from pathlib import Path

from googleapiclient.discovery import build

token_path = Path("token_send.pickle")

if not token_path.exists():
    print("ERROR: token_send.pickle not found! Run setup_gmail_send.py first")
    exit(1)

# Load credentials
with open(token_path, "rb") as f:
    creds = pickle.load(f)

print(f"Token valid: {creds.valid}")
print(f"Token expired: {creds.expired}")

# Refresh if needed
if creds.expired and creds.refresh_token:
    from google.auth.transport.requests import Request
    creds.refresh(Request())
    with open(token_path, "wb") as f:
        pickle.dump(creds, f)
    print("Token refreshed!")

# Build service
service = build("gmail", "v1", credentials=creds)

# Create email
message = MIMEText("Hello! This is a test email from AI Employee System. If you see this, email sending works!")
message["to"] = "shaistatosif34@gmail.com"
message["subject"] = "AI Employee - Email Test Working!"

raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

# Send
result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
print(f"\nEMAIL SENT! Message ID: {result.get('id')}")
print("Check your Gmail inbox!")
