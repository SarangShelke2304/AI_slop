
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Pillow Monkeypatch ---
# MoviePy 1.0.3 uses PIL.Image.ANTIALIAS which was removed in Pillow 10.0.0.
# We monkeypatch it to use Resampling.LANCZOS for backward compatibility.
try:
    import PIL.Image
    if not hasattr(PIL.Image, 'ANTIALIAS'):
        from PIL import Image
        if hasattr(Image, 'Resampling'):
            PIL.Image.ANTIALIAS = Image.Resampling.LANCZOS
        else:
            PIL.Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

class Settings:

    """
    Application configuration loaded from environment variables.
    """
    
    # Project Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    LOGS_DIR: Path = BASE_DIR / "logs"
    TEMP_DIR: Path = BASE_DIR / "temp"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    
    # Reddit Configuration
    # No Auth Required: Using direct JSON scraping
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    SUBREDDITS: List[str] = [s.strip() for s in os.getenv("SUBREDDITS", "").split(",") if s.strip()]
    
    # Scraping Configuration
    STORIES_PER_RUN: int = int(os.getenv("STORIES_PER_RUN", "10"))
    MIN_UPVOTES: int = int(os.getenv("MIN_UPVOTES", "100"))
    STORY_SORT: str = os.getenv("STORY_SORT", "top")
    STORY_TIME_FILTER: str = os.getenv("STORY_TIME_FILTER", "all")
    MIN_WORD_COUNT: int = int(os.getenv("MIN_WORD_COUNT", "300"))
    MAX_VIDEO_DURATION_SECONDS: int = int(os.getenv("MAX_VIDEO_DURATION_SECONDS", "60"))
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Groq Configuration (Free)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Edge TTS configuration
    # No Auth Required
    TTS_VOICE: str = os.getenv("TTS_VOICE", "en-US-ChristopherNeural")  # Male: Christopher, Female: Aria
    
    # FFmpeg Configuration
    # If set, will explicitly tell MoviePy and Pydub where FFmpeg is
    FFMPEG_PATH: Optional[str] = os.getenv("FFMPEG_PATH", None)
    
    # Google Drive
    DRIVE_INPUT_FOLDER_ID: str = os.getenv("DRIVE_INPUT_FOLDER_ID", "")
    DRIVE_OUTPUT_FOLDER_ID: str = os.getenv("DRIVE_OUTPUT_FOLDER_ID", "")
    GOOGLE_OAUTH_CREDENTIALS_PATH: str = os.getenv("GOOGLE_OAUTH_CREDENTIALS_PATH", "")
    GOOGLE_OAUTH_TOKEN_PATH: str = os.getenv("GOOGLE_OAUTH_TOKEN_PATH", "token.json")
    
    # YouTube
    YOUTUBE_DAILY_UPLOAD_LIMIT: int = int(os.getenv("YOUTUBE_DAILY_UPLOAD_LIMIT", "6"))
    
    # Email Configuration (SMTP)
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    NOTIFICATION_EMAIL: str = os.getenv("NOTIFICATION_EMAIL", "")
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Scheduling
    SCHEDULE_INTERVAL_HOURS: int = int(os.getenv("SCHEDULE_INTERVAL_HOURS", "6"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    
    # Video Settings
    VIDEO_WIDTH: int = int(os.getenv("VIDEO_WIDTH", "720"))
    VIDEO_HEIGHT: int = int(os.getenv("VIDEO_HEIGHT", "1280"))
    VIDEO_FPS: int = int(os.getenv("VIDEO_FPS", "30"))
    VIDEO_BITRATE: str = os.getenv("VIDEO_BITRATE", "2M")
    WATERMARK_TEXT: str = os.getenv("WATERMARK_TEXT", "@YourChannel")
    OUTRO_DURATION_SECONDS: int = int(os.getenv("OUTRO_DURATION_SECONDS", "3"))
    
    # Subtitle Settings
    SUBTITLE_FONT: str = os.getenv("SUBTITLE_FONT", "DejaVu Sans")
    SUBTITLE_COLOR: str = os.getenv("SUBTITLE_COLOR", "&H00FFFFFF")  # ASS format BGR
    SUBTITLE_OUTLINE_COLOR: str = os.getenv("SUBTITLE_OUTLINE_COLOR", "&H00000000")
    SUBTITLE_HIGHLIGHT_COLOR: str = os.getenv("SUBTITLE_HIGHLIGHT_COLOR", "&H000000FF") # Red in BGR
    
    # Testing
    TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() == "true"
    TEST_STORY_LIMIT: int = int(os.getenv("TEST_STORY_LIMIT", "1"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE_PATH: str = os.getenv("LOG_FILE_PATH", str(LOGS_DIR / "app.log"))
    CLOUDWATCH_LOG_GROUP: str = os.getenv("CLOUDWATCH_LOG_GROUP", "ai-slop-pipeline")

# Global settings instance
settings = Settings()

# --- Runtime PATH Injection ---
# In Windows, MoviePy and Pydub often need the FFmpeg 'bin' folder 
# in the system PATH to find sub-tools like ffprobe.
if settings.FFMPEG_PATH:
    ffmpeg_dir = str(Path(settings.FFMPEG_PATH).parent)
    if ffmpeg_dir not in os.environ["PATH"]:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]

