
import asyncio
import os
import time
from pathlib import Path
from typing import List, Dict

from src.config import settings
from src.utils.logger import logger
from src.utils.helpers import cleanup_temp_files
from src.database.connection import get_db_session
from src.database.queries import DBQueries

# Components
from src.scrapers.reddit_scraper import scraper
from src.processors.story_processor import processor
from src.generators.tts_generator import tts_engine
from src.generators.audio_mixer import audio_mixer
from src.generators.subtitle_generator import subtitle_generator
from src.generators.video_generator import video_generator
from src.uploaders.drive_uploader import drive_uploader
from src.uploaders.youtube_uploader import youtube_uploader
from src.notifiers.email_notifier import email_notifier

from src.database.models import StoryPart, Video

async def run_pipeline():
    """
    Main pipeline orchestration.
    """
    start_time = time.time()
    logger.info(f"Pipeline started at {time.ctime()} (Test Mode: {settings.TEST_MODE})")
    
    # Create temp dirs
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Stats tracking
    stats = {
        "new_stories": 0,
        "processed_stories": 0,
        "videos_created": 0,
        "successful_videos": []
    }
    
    try:
        # ==========================================
        # 0. Startup & Cleaning
        # ==========================================
        cleanup_temp_files(settings.TEMP_DIR, "*.mp3")
        cleanup_temp_files(settings.TEMP_DIR, "*.mp4")
        cleanup_temp_files(settings.TEMP_DIR, "*.ass")
        
        async with get_db_session() as session:
             queries = DBQueries(session)
             job = await queries.create_processing_job("main_pipeline")
             
        # Notify start
        email_notifier.send_email(
            "AI Slop Pipeline Started", 
            f"Run ID: {job.id}\nTest Mode: {settings.TEST_MODE}"
        )

        # ==========================================
        # 1. Scrape Reddit
        # ==========================================
        scrape_limit = settings.TEST_STORY_LIMIT if settings.TEST_MODE else settings.STORIES_PER_RUN
        stats["new_stories"] = await scraper.scrape_stories(limit=scrape_limit)
        
        await queries.update_job_heartbeat(job.id)

        # ==========================================
        # 2. Process Stories (AI)
        # ==========================================
        process_limit = 1 if settings.TEST_MODE else 10 # Batch size
        stats["processed_stories"] = await processor.process_scraped_stories(limit=process_limit)
        
        await queries.update_job_heartbeat(job.id)

        # ==========================================
        # 3. Content Generation Loop
        # ==========================================
        
        # Get pending parts
        async with get_db_session() as session:
            queries = DBQueries(session)
            pending_parts = await queries.get_pending_parts_for_audio(limit=process_limit * 3) # Approx 3 parts per story
        
        logger.info(f"Found {len(pending_parts)} story parts suitable for video generation.")
        
        if not pending_parts:
            logger.info("No stories need video generation. Skipping stage.")
        else:
            email_notifier.send_progress_update(0, len(pending_parts), "Starting Content Generation")
        
        for i, part in enumerate(pending_parts):
            try:
                logger.info(f"Generating content for Part {part.id}...")
                
                # --- A. TTS Generation ---
                audio_filename = f"{part.id}_audio.mp3"
                audio_path = str(settings.TEMP_DIR / audio_filename)
                
                duration, voice, word_timings = await tts_engine.generate_audio(
                    part.content, audio_path
                )
                
                # --- B. Audio Mixing (Bleeps) ---
                # Note: tts_generator.generate_audio already saved file.
                # Now we operate on it.
                # In censor module, 'get_bleep_locations' works on text. 
                # We need original or censored text? Censored text has stars.
                # The 'word_timings' are for spoken text.
                # Audio mixer will overlay bleeps.
                audio_path = await audio_mixer.mix_audio(part.content, audio_path, word_timings)
                
                # --- C. Subtitles ---
                ass_filename = f"{part.id}_subs.ass"
                ass_path = str(settings.TEMP_DIR / ass_filename)
                subtitle_generator.generate_ass(word_timings, ass_path)
                
                # --- D. Video Generation ---
                video_filename = f"{part.story.subreddit}_{part.story.reddit_id}_{part.part_number}.mp4"
                video_path = str(settings.TEMP_DIR / video_filename)
                
                final_video = await video_generator.generate_video(
                    audio_path=audio_path,
                    subtitle_path=ass_path,
                    output_path=video_path,
                    duration=duration
                )
                
                if not final_video:
                    raise RuntimeError("Video generation returned None")
                    
                stats["videos_created"] += 1
                
                # --- E. Upload to Drive ---
                drive_res = None
                if not settings.TEST_MODE:
                    drive_res = await drive_uploader.upload_video(final_video, video_filename)
                else:
                    logger.info(f"[TEST] Skipping Drive upload for {video_filename}")
                    drive_res = {"download_url": "http://test-url.com", "id": "test_id"}
                
                # --- F. Queue for YouTube ---
                if not settings.TEST_MODE and settings.YOUTUBE_DAILY_UPLOAD_LIMIT > 0:
                    # Logic to queue video
                    # Needs db interaction.
                    # We need to Create Video record first.
                    pass 
                    
                # Store Video Record
                # We have to reconnect session/refresh to ensure we are adding correctly
                # Or just use the 'queries' object if session is valid. 
                # But loop might take long, better to use short sessions or refresh
                # Let's do a quick update session per item
                
                async with get_db_session() as update_sess:
                    q = DBQueries(update_sess)
                    
                    # Create Video DB Entry
                    video_db = Video(
                        story_part_id=part.id,
                        filename=video_filename,
                        duration_seconds=duration,
                        drive_file_id=drive_res.get("id"),
                        drive_download_url=drive_res.get("download_url"),
                        status="uploaded_to_drive" if not settings.TEST_MODE else "generated"
                    )
                    update_sess.add(video_db)
                    await update_sess.flush()
                    
                    # Add to YouTube Queue
                    if not settings.TEST_MODE:
                        from src.database.models import YoutubeUploadQueue
                        
                        queue_item = YoutubeUploadQueue(
                            video_id=video_db.id,
                            title=part.title or "Reddit Story",
                            description=f"{part.caption}\n\n{part.story.suggested_caption}",
                            tags=part.story.hashtags or []
                        )
                        update_sess.add(queue_item)
                        
                    # Update Part Status
                    await update_sess.execute(
                        "UPDATE story_parts SET status='completed' WHERE id=:id",
                        {"id": part.id}
                    ) 
                    # Note: Using raw SQL for quick status update to avoid detach issues or just query fetch
                    # Re-fetching part in new session helps.
                
                # Add to report
                stats["successful_videos"].append({
                    "title": part.title,
                    "download_url": drive_res.get("download_url"),
                    "caption": part.caption or part.story.suggested_caption,
                    "hashtags": " ".join(part.story.hashtags or [])
                })
                
                # Progress Update
                if (i + 1) % 5 == 0:
                    email_notifier.send_progress_update(i + 1, len(pending_parts), "Video Generation")
                    
                 # Cleanup loop temp
                if os.path.exists(audio_path): os.remove(audio_path)
                if os.path.exists(ass_path): os.remove(ass_path)
                if os.path.exists(video_path): os.remove(video_path)
                    
            except Exception as e:
                logger.error(f"Failed to generate content for Part {part.id}: {e}")
                # Update status to failed
                async with get_db_session() as err_sess:
                    # q = DBQueries(err_sess)
                    # Use sql needed
                    pass

        # Use update_job status
        
    except Exception as e:
        logger.error(f"Pipeline crashed: {e}")
        email_notifier.send_email("Pipeline Failure", str(e))
        
    finally:
        duration = time.time() - start_time
        logger.info(f"Pipeline finished in {duration:.2f}s")
        
        # Send completion report
        if stats["successful_videos"]:
            email_notifier.send_completion_report(stats["successful_videos"])
            
        settings.TEMP_DIR.rmdir() if not any(settings.TEMP_DIR.iterdir()) else None # Optional cleanup

def main():

        
    asyncio.run(run_pipeline())

if __name__ == "__main__":
    main()
