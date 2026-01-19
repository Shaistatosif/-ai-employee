#!/usr/bin/env python3
"""
Gmail OAuth Setup Script

This script helps you set up Gmail API access for the Personal AI Employee System.

Prerequisites:
1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Gmail API:
   - Go to APIs & Services > Library
   - Search for "Gmail API"
   - Click Enable
4. Create OAuth credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop application"
   - Download the JSON file
   - Save as "credentials.json" in the project root

Usage:
    python scripts/setup_gmail.py

This will:
1. Check if credentials.json exists
2. Open a browser for you to authorize the app
3. Save the token for future use
"""

import os
import pickle
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 60)
    print("Gmail OAuth Setup for Personal AI Employee System")
    print("=" * 60)
    print()

    credentials_path = Path("credentials.json")
    token_path = Path("token.pickle")

    # Check for credentials.json
    if not credentials_path.exists():
        print("ERROR: credentials.json not found!")
        print()
        print("To get credentials.json:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create/select a project")
        print("3. Enable Gmail API (APIs & Services > Library)")
        print("4. Create OAuth credentials (APIs & Services > Credentials)")
        print("5. Choose 'Desktop application'")
        print("6. Download JSON and save as 'credentials.json' here")
        print()
        print(f"Expected location: {credentials_path.absolute()}")
        return 1

    print(f"Found: {credentials_path}")

    # Check if already authorized
    if token_path.exists():
        print(f"Found existing token: {token_path}")
        response = input("Re-authorize? (y/N): ").strip().lower()
        if response != "y":
            print("Using existing token.")
            return 0
        token_path.unlink()

    # Import Google libraries
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: Google API libraries not installed!")
        print("Run: pip install google-api-python-client google-auth-oauthlib")
        return 1

    # Scopes - read-only for safety
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    print()
    print("Starting OAuth flow...")
    print("A browser window will open for authorization.")
    print()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0)

        # Save token
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

        print()
        print("SUCCESS! Token saved to:", token_path)

        # Test the connection
        print()
        print("Testing Gmail API connection...")
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        print(f"Connected as: {profile.get('emailAddress')}")
        print(f"Total messages: {profile.get('messagesTotal')}")

        print()
        print("=" * 60)
        print("Gmail setup complete! You can now run:")
        print("  python main.py")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
