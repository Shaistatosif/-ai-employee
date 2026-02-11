#!/usr/bin/env python3
"""Setup Gmail Send Token - separate from read token."""

import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 60)
    print("Gmail SEND Token Setup")
    print("=" * 60)

    credentials_path = Path("credentials.json")
    token_path = Path("token_send.pickle")

    if not credentials_path.exists():
        print("ERROR: credentials.json not found!")
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: pip install google-api-python-client google-auth-oauthlib")
        return 1

    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    print("\nBrowser will open - login and allow SEND permission...\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

        print(f"\nSUCCESS! Send token saved to: {token_path}")

        # Test
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        print(f"Account: {profile.get('emailAddress')}")
        print("\nEmail sending is now enabled!")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
