# Reddit Story to Video Pipeline - Complete Guide

> **Project Goal**: Automatically scrape Reddit stories, modify them with AI, generate voice narration, create videos with gameplay background and TikTok-style subtitles, upload to YouTube (automated) and prepare for Instagram (manual upload via email links).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Pipeline Flow](#pipeline-flow)
4. [Module Breakdown](#module-breakdown)
5. [Database Design](#database-design)
6. [Google Drive Structure](#google-drive-structure)
7. [API Services & Free Tier Limits](#api-services--free-tier-limits)
8. [Configuration Reference](#configuration-reference)
9. [Scheduling & Automation](#scheduling--automation)
10. [Error Handling & Notifications](#error-handling--notifications)
11. [Testing Mode](#testing-mode)
12. [File Naming Conventions](#file-naming-conventions)
13. [Related Documentation](#related-documentation)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AWS EC2 (Free Tier)                                │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                           Scheduler (Cron)                                │  │
│  │                    Runs every X hours (configurable)                      │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                          │
│                                      ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         Main Orchestrator                                 │  │
│  │   • Checks resume state from DB                                           │  │
│  │   • Coordinates all pipeline stages                                       │  │
│  │   • Sends progress emails (25%, 50%, 75%, 100%)                          │  │
│  │   • Handles errors and retries                                            │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                          │
│       ┌──────────────────────────────┼──────────────────────────────┐           │
│       ▼                              ▼                              ▼           │
│  ┌─────────────┐            ┌─────────────────┐            ┌─────────────────┐  │
│  │   Reddit    │            │   Story         │            │   TTS           │  │
│  │   Scraper   │───────────▶│   Processor     │───────────▶│   Generator     │  │
│  │             │            │   (Gemini AI)   │            │ (Google Cloud)  │  │
│  └─────────────┘            └─────────────────┘            └─────────────────┘  │
│                                                                    │            │
│                                                                    ▼            │
│  ┌─────────────────┐       ┌─────────────────┐            ┌─────────────────┐  │
│  │   YouTube       │       │   Google Drive  │            │   Video         │  │
│  │   Uploader      │◀──────│   Uploader      │◀───────────│   Generator     │  │
│  │   (6/day queue) │       │                 │            │   (FFmpeg)      │  │
│  └─────────────────┘       └─────────────────┘            └─────────────────┘  │
│           │                        │                               │            │
│           │                        │                               │            │
│           ▼                        ▼                               ▼            │
│  ┌─────────────────┐       ┌─────────────────┐            ┌─────────────────┐  │
│  │   YouTube       │       │   Email         │            │   Subtitle      │  │
│  │   (Automated)   │       │   Notifier      │            │   Generator     │  │
│  │                 │       │   (Instagram)   │            │   (TikTok-style)│  │
│  └─────────────────┘       └─────────────────┘            └─────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │         PostgreSQL (Supabase)       │
                    │   • stories                         │
                    │   • videos                          │
                    │   • youtube_upload_queue            │
                    │   • processing_jobs                 │
                    │   • email_logs                      │
                    └─────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| **Language** | Python 3.11+ | As specified |
| **Reddit API** | PRAW (Python Reddit API Wrapper) | Official, reliable |
| **LLM** | Google Gemini API | Free tier: 60 requests/min, 1500 requests/day |
| **TTS** | Google Cloud Text-to-Speech | Free tier: 1M characters/month (WaveNet voices) |
| **Video Processing** | FFmpeg + MoviePy | Open source, powerful |
| **Subtitle Generation** | Custom Python (word-by-word timing) | TikTok-style animated captions |
| **Cloud Storage** | Google Drive API | OAuth, unlimited via personal account |
| **YouTube Upload** | YouTube Data API v3 | Official API, 6 uploads/day on free tier |
| **Database** | PostgreSQL (Supabase) | Free tier available, reliable |
| **Email** | AWS SES | Free tier: 62,000 emails/month (from EC2) |
| **Hosting** | AWS EC2 (t2.micro/t3.micro) | Free tier: 750 hours/month |
| **Logging** | CloudWatch + Local Files | AWS native, has free tier |
| **Scheduler** | Cron (systemd timer) | Native Linux, no overhead |

---

## Pipeline Flow

### Stage 1: Reddit Scraping
```
1. Connect to Reddit API using PRAW
2. For each subreddit in SUBREDDITS list:
   a. Fetch top posts (sorted by: configurable, default "top")
   b. Filter by:
      - Minimum upvotes (default: 100)
      - Time period (default: all time)
      - Not already in database
   c. Store raw stories in database with status "scraped"
3. Limit to 5-10 stories per run (configurable)
```

### Stage 2: Story Processing (AI)
```
1. For each story with status "scraped":
   a. Generate cuss word list using Gemini (once per session)
   b. Light reword the story using Gemini
   c. Add intro lines (2-3 sentences)
   d. Add middle insertion (2-3 sentences at ~50% point)
   e. Add outro lines (2-3 sentences)
   f. If word count < 300, extend using AI
   g. Detect and replace cuss words with ****
   h. Split into parts if > 60 seconds when spoken (~150 words)
   i. Generate catchy title using AI
   j. Generate viral hashtags using AI
   k. Update status to "processed"
```

### Stage 3: Audio Generation
```
1. For each story part with status "processed":
   a. Select random voice from Google Cloud TTS voices
   b. Generate speech audio (normal human speed)
   c. Detect cuss word timestamps
   d. Insert bleep sounds at cuss word positions
   e. Calculate audio duration
   f. Store audio file path in database
   g. Update status to "audio_generated"
```

### Stage 4: Video Generation
```
1. For each story part with status "audio_generated":
   a. Select random gameplay video from Google Drive input folder
   b. If gameplay < audio duration: loop gameplay
   c. If gameplay > audio duration: crop to audio length
   d. Mute gameplay audio (voice only)
   e. Overlay voice audio on video
   f. Generate word-by-word subtitle timing
   g. Add TikTok-style animated subtitles:
      - White text with black outline
      - Keywords highlighted in red
      - Font: System default (fastest processing)
   h. Add watermark (from .env)
   i. Add 3-second outro with follow CTA
   j. Export as 720x1280 MP4 (optimized for speed)
   k. Update status to "video_generated"
```

### Stage 5: Upload & Distribution
```
1. For each video with status "video_generated":
   a. Upload to Google Drive output folder
   b. Get shareable download link
   c. Delete local file immediately
   d. Add to youtube_upload_queue (if not already queued)
   e. Update status to "uploaded_to_drive"

2. YouTube Upload Queue (separate process):
   a. Check quota (6 uploads/day max)
   b. Upload oldest queued videos (up to daily limit)
   c. Set title: AI-generated catchy title + [Part X/Y]
   d. Set description: Caption + hashtags
   e. Update queue status

3. Email Notification (for Instagram):
   a. Compile list of new videos
   b. Generate email with:
      - Individual download links
      - Suggested captions with [Part X/Y] format
      - Hashtags for each video
   c. Send to configured email address
```

### Stage 6: Cleanup & Reporting
```
1. Delete all local temporary files
2. Update processing_jobs table with completion status
3. Send daily summary email:
   - Total stories scraped
   - Videos generated
   - YouTube uploads (success/queued)
   - Failures and reasons
   - Storage usage
```

---

## Module Breakdown

### Directory Structure
```
ai_slop/
├── .env                          # Environment variables (secrets)
├── .env.example                  # Template for .env
├── .gitignore                    # Git ignore rules
├── README.md                     # Project readme
├── requirements.txt              # Python dependencies
├── guide.md                      # This guide
├── ec2_setup.md                  # EC2 setup instructions
├── database_schema.sql           # Database schema
│
├── src/
│   ├── __init__.py
│   ├── main.py                   # Entry point & orchestrator
│   ├── config.py                 # Configuration loader
│   │
│   ├── scrapers/
│   │   ├── __init__.py
│   │   └── reddit_scraper.py     # Reddit API integration
│   │
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── story_processor.py    # Story modification with AI
│   │   ├── censor.py             # Cuss word detection & censoring
│   │   └── text_splitter.py      # Split stories into parts
│   │
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── tts_generator.py      # Google Cloud TTS integration
│   │   ├── video_generator.py    # FFmpeg/MoviePy video creation
│   │   ├── subtitle_generator.py # Word-by-word subtitle timing
│   │   └── audio_mixer.py        # Bleep sound insertion
│   │
│   ├── uploaders/
│   │   ├── __init__.py
│   │   ├── drive_uploader.py     # Google Drive API
│   │   └── youtube_uploader.py   # YouTube Data API
│   │
│   ├── notifiers/
│   │   ├── __init__.py
│   │   └── email_notifier.py     # AWS SES email sending
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py         # Database connection
│   │   ├── models.py             # SQLAlchemy models
│   │   └── queries.py            # Database queries
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py             # Logging setup (CloudWatch + local)
│   │   ├── retry.py              # Retry decorator
│   │   └── helpers.py            # Misc utilities
│   │
│   └── ai/
│       ├── __init__.py
│       ├── gemini_client.py      # Gemini API wrapper
│       └── prompts.py            # AI prompt templates
│
├── assets/
│   └── bleep.mp3                 # Bleep sound for censoring
│
├── logs/                         # Local log files
│   └── .gitkeep
│
├── temp/                         # Temporary processing files
│   └── .gitkeep
│
└── tests/
    ├── __init__.py
    ├── test_scraper.py
    ├── test_processor.py
    ├── test_generator.py
    └── test_integration.py
```

---

## Database Design

See [database_schema.sql](file:///d:/ai_slop/database_schema.sql) for complete schema.

### Tables Overview

| Table | Purpose |
|-------|---------|
| `stories` | Stores scraped Reddit stories and their processing status |
| `story_parts` | Individual parts of split stories |
| `videos` | Generated video metadata and file references |
| `youtube_upload_queue` | Queue for YouTube uploads (6/day limit) |
| `processing_jobs` | Track each pipeline run for resume capability |
| `email_logs` | Log of sent emails |
| `cuss_words` | Session-generated cuss word list |

### Status Flow

```
Story Status Flow:
scraped → processed → audio_generated → video_generated → uploaded_to_drive → completed

YouTube Queue Status:
queued → uploading → uploaded → failed

Processing Job Status:
started → in_progress → completed → failed
```

---

## Google Drive Structure

```
My Drive/
└── AI_Slop/
    ├── Input/
    │   └── Gameplay/                    # You upload gameplay videos here
    │       ├── minecraft_parkour_1.mp4
    │       ├── subway_surfers_1.mp4
    │       └── ...
    │
    └── Output/
        ├── 2026-01-04/                  # Date-organized folders
        │   ├── nosleep_abc123_1.mp4
        │   ├── nosleep_abc123_2.mp4
        │   ├── AmITheAsshole_def456_1.mp4
        │   └── ...
        │
        ├── 2026-01-05/
        │   └── ...
        │
        └── YouTube_Uploaded/            # Moved after YouTube upload
            └── ...
```

---

## API Services & Free Tier Limits

### Reddit API
- **Rate Limit**: 60 requests/minute
- **Requirements**: Client ID, Client Secret, Username, Password
- **Setup**: Create app at https://www.reddit.com/prefs/apps

### Google Gemini API
- **Free Tier**: 60 requests/minute, 1,500 requests/day
- **Model**: gemini-1.5-flash (fastest, sufficient for text)
- **Setup**: Get API key at https://makersuite.google.com/app/apikey

### Google Cloud Text-to-Speech
- **Free Tier**: 1 million characters/month (WaveNet voices)
- **Voices**: Multiple human-like voices (randomized per video)
- **Setup**: Enable API in Google Cloud Console, create service account

### Google Drive API
- **Free Tier**: Unlimited (storage depends on Google account - 15GB free)
- **Auth**: OAuth 2.0 (user consent required once)
- **Setup**: Enable API in Google Cloud Console, create OAuth credentials

### YouTube Data API v3
- **Free Tier**: 10,000 quota units/day
- **Upload Cost**: ~1,600 units per upload = **6 uploads/day max**
- **Setup**: Enable API in Google Cloud Console, OAuth credentials

### AWS SES (Simple Email Service)
- **Free Tier**: 62,000 emails/month when sent from EC2
- **Setup**: Verify sender email, request production access

### AWS CloudWatch
- **Free Tier**: 5GB log ingestion, 5GB log storage
- **Setup**: Automatic with EC2 instance, install CloudWatch agent

---

## Configuration Reference

See [.env.example](file:///d:/ai_slop/.env.example) for the complete template.

### Environment Variables

```bash
# ============================================
#           REDDIT CONFIGURATION
# ============================================
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=AI_Slop_Bot/1.0

# Comma-separated list of subreddits
SUBREDDITS=nosleep,AmITheAsshole,stories,tifu

# ============================================
#           SCRAPING CONFIGURATION
# ============================================
STORIES_PER_RUN=10
MIN_UPVOTES=100
STORY_SORT=top
STORY_TIME_FILTER=all
MIN_WORD_COUNT=300
MAX_VIDEO_DURATION_SECONDS=60

# ============================================
#           GOOGLE AI (GEMINI)
# ============================================
GEMINI_API_KEY=your_gemini_api_key

# ============================================
#           GOOGLE CLOUD TTS
# ============================================
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
TTS_LANGUAGE_CODE=en-US

# ============================================
#           GOOGLE DRIVE
# ============================================
DRIVE_INPUT_FOLDER_ID=your_input_folder_id
DRIVE_OUTPUT_FOLDER_ID=your_output_folder_id
GOOGLE_OAUTH_CREDENTIALS_PATH=/path/to/oauth-credentials.json
GOOGLE_OAUTH_TOKEN_PATH=/path/to/token.json

# ============================================
#           YOUTUBE
# ============================================
YOUTUBE_DAILY_UPLOAD_LIMIT=6

# ============================================
#           AWS / EMAIL
# ============================================
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
NOTIFICATION_EMAIL=your_email@example.com
SENDER_EMAIL=noreply@yourdomain.com

# ============================================
#           DATABASE
# ============================================
DATABASE_URL=postgresql://user:password@host:5432/database

# ============================================
#           SCHEDULING
# ============================================
SCHEDULE_INTERVAL_HOURS=6
TIMEZONE=Asia/Kolkata

# ============================================
#           VIDEO SETTINGS
# ============================================
VIDEO_WIDTH=720
VIDEO_HEIGHT=1280
VIDEO_FPS=30
VIDEO_BITRATE=2M
WATERMARK_TEXT=@YourChannel
OUTRO_DURATION_SECONDS=3

# ============================================
#           TESTING
# ============================================
TEST_MODE=false
TEST_STORY_LIMIT=1

# ============================================
#           LOGGING
# ============================================
LOG_LEVEL=INFO
LOG_FILE_PATH=/var/log/ai_slop/app.log
```

---

## Scheduling & Automation

### Cron Job Setup

The application will be scheduled using **systemd timers** for reliability:

```bash
# /etc/systemd/system/ai-slop.service
[Unit]
Description=AI Slop Video Pipeline
After=network.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/ai_slop
ExecStart=/home/ubuntu/ai_slop/venv/bin/python -m src.main
Environment=PYTHONPATH=/home/ubuntu/ai_slop
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# /etc/systemd/system/ai-slop.timer
[Unit]
Description=Run AI Slop every X hours

[Timer]
OnBootSec=5min
OnUnitActiveSec=6h  # Matches SCHEDULE_INTERVAL_HOURS
Persistent=true

[Install]
WantedBy=timers.target
```

### YouTube Queue Processor (Separate Timer)

```bash
# Runs every 4 hours to spread uploads throughout the day
# /etc/systemd/system/ai-slop-youtube.timer
[Unit]
Description=Process YouTube upload queue

[Timer]
OnCalendar=*-*-* 02,06,10,14,18,22:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Error Handling & Notifications

### Retry Strategy

| Component | Max Retries | Wait Between |
|-----------|-------------|--------------|
| Reddit API | 3 | 30 seconds |
| Gemini API | 3 | 10 seconds |
| Google TTS | 2 | 15 seconds |
| Drive Upload | 3 | 30 seconds |
| YouTube Upload | 2 | 60 seconds |
| Email Send | 2 | 10 seconds |

### Email Notifications

| Event | Recipient | Content |
|-------|-----------|---------|
| **Run Started** | You | "Pipeline started at {time}, processing {N} stories" |
| **25% Progress** | You | "{N} of {Total} videos completed" |
| **50% Progress** | You | "{N} of {Total} videos completed" |
| **75% Progress** | You | "{N} of {Total} videos completed" |
| **100% Complete** | You | Summary of all videos with Drive links |
| **Failure (after retry)** | You | Error details + story text |
| **Daily Summary** | You | Full day statistics |

### Resume Capability

After a crash, the pipeline will:
1. Check `processing_jobs` table for incomplete jobs
2. Find the last successful status for each story
3. Resume from that point
4. Skip already completed stories

---

## Testing Mode

When `TEST_MODE=true` in `.env`:

- Scrapes only **1 story** (ignores `STORIES_PER_RUN`)
- Skips actual YouTube upload (marks as "test_skipped")
- Skips email sending (logs to console instead)
- Uses a test gameplay video if available
- Saves video locally instead of uploading to Drive
- Adds "[TEST]" prefix to all generated content

### Running Tests

```bash
# Unit tests
python -m pytest tests/ -v

# Integration test (uses TEST_MODE)
TEST_MODE=true python -m src.main

# Test specific components
python -m pytest tests/test_scraper.py -v
python -m pytest tests/test_processor.py -v
```

---

## File Naming Conventions

### Video Files
```
{subreddit}_{story_id}_{part}.mp4

Examples:
- nosleep_xk7j2m_1.mp4
- nosleep_xk7j2m_2.mp4
- AmITheAsshole_9f3kl2_1.mp4
```

### Audio Files (Temporary)
```
{story_id}_{part}_audio.mp3
```

### Subtitle Files (Temporary)
```
{story_id}_{part}_subs.ass
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [ec2_setup.md](file:///d:/ai_slop/ec2_setup.md) | Step-by-step EC2 instance setup |
| [database_schema.sql](file:///d:/ai_slop/database_schema.sql) | Complete database schema |
| [.env.example](file:///d:/ai_slop/.env.example) | Environment variable template |
| [README.md](file:///d:/ai_slop/README.md) | Quick start guide |

---

## Implementation Checklist

- [ ] Set up AWS EC2 instance (see ec2_setup.md)
- [ ] Create PostgreSQL database (Supabase)
- [ ] Run database_schema.sql to create tables
- [ ] Create Reddit app and get credentials
- [ ] Create Google Cloud project:
  - [ ] Enable Gemini API and get key
  - [ ] Enable Cloud TTS and create service account
  - [ ] Enable Drive API and create OAuth credentials
  - [ ] Enable YouTube Data API
- [ ] Set up AWS SES and verify email
- [ ] Copy .env.example to .env and fill all values
- [ ] Upload gameplay videos to Google Drive input folder
- [ ] Test with TEST_MODE=true
- [ ] Enable systemd timers for production

---

> **Note**: This guide will be updated as the implementation progresses. All API keys and credentials should be stored securely in .env and NEVER committed to version control.
