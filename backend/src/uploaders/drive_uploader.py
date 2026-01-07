
import os
from pathlib import Path
from typing import Optional, List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from src.config import settings
from src.utils.logger import logger
from src.utils.retry import retry_google_api

# Scopes needed for Drive API - Using full drive scope to access existing gameplay videos
SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate():
    """
    Authenticate user via OAuth 2.0 and save token.
    Run this manually first time.
    """
    creds = None
    token_path = Path(settings.GOOGLE_OAUTH_TOKEN_PATH)
    
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.GOOGLE_OAUTH_CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)
            
        # Save credentials
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
    return creds

class DriveUploader:
    def __init__(self):
        try:
            self.creds = authenticate()
            self.service = build('drive', 'v3', credentials=self.creds)
        except Exception as e:
            logger.error(f"Drive authenticator failed: {e}")
            self.service = None

    @retry_google_api
    async def upload_video(self, file_path: str, filename: str) -> Optional[dict]:
        """
        Uploads a video to Google Drive output folder.
        Returns dict with file ID and webViewLink.
        """
        if not self.service:
            return None

        file_metadata = {
            'name': filename,
            'parents': [settings.DRIVE_OUTPUT_FOLDER_ID]
        }
        
        media = MediaFileUpload(
            file_path, 
            mimetype='video/mp4',
            resumable=True
        )
        
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            logger.info(f"File uploaded to Drive. ID: {file.get('id')}")
            
            # Make it shareable (anyone with link) so users can download?
            # Or just assume user is logged in. 
            # If for Instagram manual upload, user needs access.
            # We can create a permission.
            # For simplicity, we assume the user owns the folder.
            
            return {
                "id": file.get('id'),
                "download_url": file.get('webContentLink'), # Direct download
                "view_url": file.get('webViewLink')
            }
            
        except Exception as e:
            logger.error(f"Drive upload failed: {e}")
            raise

    async def list_gameplay_videos(self) -> List[dict]:
        """
        List all MP4 files in the input folder.
        """
        if not self.service:
            return []
            
        query = f"'{settings.DRIVE_INPUT_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed = false"
        
        results = self.service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, size)"
        ).execute()
        
        return results.get('files', [])

    async def download_file(self, file_id: str, output_path: str):
        """
        Download a file from Drive.
        """
        if not self.service:
            return
            
        request = self.service.files().get_media(fileId=file_id)
        
        with open(output_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                # logger.debug(f"Download {int(status.progress() * 100)}%.")

# Global instance
drive_uploader = DriveUploader()

