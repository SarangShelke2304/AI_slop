
import os
import random
from pathlib import Path
from typing import Optional

from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip, ImageClip


from src.config import settings
from src.utils.logger import logger
from src.database.connection import get_db_session
from src.database.queries import DBQueries

class VideoGenerator:
    def __init__(self):
        # Configure FFmpeg path for MoviePy if provided
        if settings.FFMPEG_PATH:
            logger.info(f"Setting MoviePy FFmpeg binary to: {settings.FFMPEG_PATH}")
            # MoviePy uses an internal config/env variable for binary path
            os.environ["IMAGEIO_FFMPEG_EXE"] = settings.FFMPEG_PATH
            # Also try to set for moviepy specifically if IMAGEIO_FFMPEG_EXE isn't enough
            # We can't import moviepy.config directly until after importing it generally
            # But we can try to find and set it.
            try:
                from moviepy.config import change_settings
                change_settings({"FFMPEG_BINARY": settings.FFMPEG_PATH})
            except Exception as e:
                logger.warning(f"Failed to set MoviePy FFMPEG_BINARY explicitly: {e}")

    async def generate_video(
        self, 
        audio_path: str, 
        subtitle_path: str, 
        output_path: str,
        duration: float,
        gameplay_video_id: str = None
    ) -> Optional[str]:
        """
        Generate final video using MoviePy.
        """
        try:
            # 1. Load Audio
            audio = AudioFileClip(audio_path)
            
            # 2. Get Gameplay Video
            gameplay_path = await self._get_gameplay_video_path(gameplay_video_id)
            if not gameplay_path:
                logger.error("No gameplay video found")
                return None
                
            video = VideoFileClip(gameplay_path)
            
            # 3. Process Video (Loop/Crop)
            # Add 3 seconds for the outro
            video_duration = duration + settings.OUTRO_DURATION_SECONDS
            
            if video.duration < video_duration:
                # Loop video
                loops = int(video_duration / video.duration) + 1
                video = video.loop(n=loops)
            
            # Crop to duration
            video = video.subclip(0, video_duration)
            
            # Resize/Crop to 9:16 vertical
            target_ratio = settings.VIDEO_WIDTH / settings.VIDEO_HEIGHT
            current_ratio = video.w / video.h
            
            if current_ratio > target_ratio:
                # Too wide
                new_width = int(video.h * target_ratio)
                center_x = video.w / 2
                video = video.crop(
                    x1=center_x - new_width/2, 
                    x2=center_x + new_width/2
                )
            else:
                # Too tall
                new_height = int(video.w / target_ratio)
                center_y = video.h / 2
                video = video.crop(
                    y1=center_y - new_height/2, 
                    y2=center_y + new_height/2
                )
                
            video = video.resize((settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT))
            
            # 4. Mix Audio
            video = video.set_audio(audio)
            
            # Export temp video without subtitles
            temp_video_path = output_path.replace(".mp4", "_temp.mp4")
            
            logger.info(f"Exporting base video: {temp_video_path}")
            video.write_videofile(
                temp_video_path, 
                codec='libx264', 
                audio_codec='aac', 
                fps=settings.VIDEO_FPS,
                preset='ultrafast',
                threads=4,
                logger=None 
            )
            
            # Close clips to free memory
            video.close()
            audio.close()
            
            # 8. Burn Subtitles, Watermark, and Outro via FFmpeg (all in ASS file)

            ass_path_unix = subtitle_path.replace('\\', '/').replace(':', '\\:')
            
            ffmpeg_bin = settings.FFMPEG_PATH or 'ffmpeg'
            
            import subprocess
            cmd = [
                ffmpeg_bin, '-y',
                '-i', temp_video_path,
                '-vf', f"ass='{ass_path_unix}'",
                '-c:a', 'copy',
                output_path
            ]
            
            logger.info(f"Running FFmpeg: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            
            # Cleanup temp
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
                
            return output_path

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            # Ensure cleanup
            if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            return None

    async def _get_gameplay_video_path(self, video_id: str = None) -> Optional[str]:
        """
        Get local path to a gameplay video.
        Checks local folder first, then downloads from Drive if empty.
        """
        from src.uploaders.drive_uploader import drive_uploader
        
        input_dir = settings.BASE_DIR / "temp" / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Check local files first (cached)
        files = list(input_dir.glob("*.mp4"))
        if files:
            return str(random.choice(files))
            
        # 2. If empty, try to download from Drive
        logger.info("No local gameplay videos found. Attempting to fetch from Drive...")
        
        try:
            drive_files = await drive_uploader.list_gameplay_videos()
            if not drive_files:
                logger.error("No gameplay videos found in Google Drive folder.")
                return None
                
            # Pick a random video
            drive_file = random.choice(drive_files)
            file_id = drive_file['id']
            file_name = drive_file['name']
            
            # Ensure it has .mp4 extension for local path
            if not file_name.endswith('.mp4'):
                file_name += '.mp4'
                
            output_path = input_dir / file_name
            
            logger.info(f"Downloading gameplay video: {file_name} ({file_id})")
            await drive_uploader.download_file(file_id, str(output_path))
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to fetch gameplay from Drive: {e}")
            return None


# Global instance
video_generator = VideoGenerator()
