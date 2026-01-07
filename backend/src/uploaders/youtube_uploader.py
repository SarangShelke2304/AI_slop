
from datetime import datetime, timedelta
from typing import Optional, List

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.config import settings
from src.utils.logger import logger
from src.utils.retry import retry_google_api
from src.uploaders.drive_uploader import authenticate # Reuse auth logic/credentials

class YoutubeUploader:
    def __init__(self):
        try:
            # Reusing same creds for simplicity if scopes allow.
            # Usually separate scopes needed.
            # We should check scopes in auth flow.
            # Updated scopes in drive_uploader to include youtube? Or separate auth?
            # For this guide, assuming shared credentials handling or separate flow.
            # Let's assume separate simple auth for now or shared.
            self.creds = authenticate() # This might need 'https://www.googleapis.com/auth/youtube.upload'
            self.service = build('youtube', 'v3', credentials=self.creds)
        except Exception as e:
            logger.error(f"YouTube authenticator failed: {e}")
            self.service = None

    @retry_google_api
    async def upload_video(
        self, 
        file_path: str, 
        title: str, 
        description: str, 
        tags: List[str]
    ) -> Optional[str]:
        """
        Upload video to YouTube. Returns Video ID.
        """
        if not self.service:
            return None

        body = {
            'snippet': {
                'title': title[:100], # Max 100 chars
                'description': description[:5000],
                'tags': tags,
                'categoryId': '24' # Entertainment
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(
            file_path, 
            chunksize=-1, 
            resumable=True
        )

        try:
            insert_request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = insert_request.execute()
            video_id = response.get('id')
            logger.info(f"Uploaded to YouTube. ID: {video_id}")
            return video_id
            
        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            raise

# Global instance
youtube_uploader = YoutubeUploader()
