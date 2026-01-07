
"""
Script to generate Google OAuth token.json locally.
Run this on your local machine with a browser.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.uploaders.drive_uploader import authenticate, SCOPES
from src.config import settings

def main():
    print("="*50)
    print("Google OAuth Token Generator")
    print("="*50)
    
    creds_path = Path(settings.GOOGLE_OAUTH_CREDENTIALS_PATH)
    if not creds_path.exists():
        print(f"ERROR: Credentials file not found at: {creds_path}")
        print("Please verify GOOGLE_OAUTH_CREDENTIALS_PATH in your .env")
        return

    print(f"Using credentials from: {creds_path}")
    print("Opening browser for authentication...")
    
    try:
        creds = authenticate()
        if creds and creds.valid:
            print("\nSUCCESS! Authentication complete.")
            print(f"Token saved to: {settings.GOOGLE_OAUTH_TOKEN_PATH}")
            print("\nNEXT STEPS:")
            print(f"1. Locate this file: {settings.GOOGLE_OAUTH_TOKEN_PATH}")
            print("2. Upload it to your EC2 instance at the same path defined in your EC2 .env")
        else:
            print("\nAuthentication failed.")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()
