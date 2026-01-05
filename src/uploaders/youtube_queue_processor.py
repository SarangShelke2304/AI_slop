
import asyncio
from datetime import datetime

from src.database.connection import get_db_session
from src.database.queries import DBQueries
from src.uploaders.youtube_uploader import youtube_uploader
from src.uploaders.drive_uploader import drive_uploader
from src.utils.logger import logger
from src.config import settings

async def process_queue():
    """
    Main entry point for queue processor script.
    Checks daily limit and uploads next items in queue.
    """
    logger.info("Starting YouTube Queue Processor...")
    
    async with get_db_session() as session:
        queries = DBQueries(session)
        
        # 1. Check daily limit
        uploaded_today = await queries.get_youtube_uploads_today()
        limit = settings.YOUTUBE_DAILY_UPLOAD_LIMIT
        
        if uploaded_today >= limit:
            logger.info(f"Daily upload limit reached ({uploaded_today}/{limit}). Exiting.")
            return

        remaining_quota = limit - uploaded_today
        logger.info(f"Uploads remaining today: {remaining_quota}")
        
        # 2. Get pending items
        queue_items = await queries.get_youtube_queue(limit=remaining_quota)
        
        if not queue_items:
            logger.info("No items in upload queue.")
            return

        for item in queue_items:
            try:
                # 3. Download/Prepare file
                # If local file deleted, download from Drive
                # We need the video object
                video = item.video
                file_path = video.local_path
                
                temp_download = False
                if not file_path or not os.path.exists(file_path):
                    if not video.drive_file_id:
                        logger.error(f"Video {video.filename} missing local file and Drive ID. Skipping.")
                        item.status = "failed"
                        item.error_message = "File missing"
                        continue
                        
                    # Download from Drive
                    logger.info(f"Downloading {video.filename} from Drive...")
                    file_path = str(settings.TEMP_DIR / video.filename)
                    await drive_uploader.download_file(video.drive_file_id, file_path)
                    temp_download = True

                # 4. Upload
                logger.info(f"Uploading {item.title}...")
                video_id = await youtube_uploader.upload_video(
                    file_path,
                    item.title,
                    item.description,
                    item.tags
                )
                
                if video_id:
                    item.status = "uploaded"
                    item.youtube_video_id = video_id
                    item.youtube_url = f"https://youtube.com/watch?v={video_id}"
                    item.uploaded_at = datetime.utcnow()
                    
                    # Update stats
                    await queries.update_daily_stats("videos_uploaded_youtube")
                    await queries.update_daily_stats("youtube_quota_used", 1600) # Approx cost
                
            except Exception as e:
                logger.error(f"Failed to process queue item {item.id}: {e}")
                item.status = "failed"
                item.error_message = str(e)
                item.retry_count += 1
                
            finally:
                # Cleanup if temporary download
                if temp_download and os.path.exists(file_path):
                    os.remove(file_path)
            
            # Commit processing of single item
            session.add(item)
            await session.commit()

def main():
    asyncio.run(process_queue())

if __name__ == "__main__":
    main()
import os # Fix missing import
