# AI Slop - Reddit Story Video Generator

Automated pipeline to scrape Reddit stories, convert them to videos with TikTok-style subtitles, and distribute to YouTube and Instagram.

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ai_slop
   ```

2. **Set up environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or: .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   nano .env  # Fill in your values
   ```

4. **Set up database**
   - Create a PostgreSQL database (Supabase recommended)
   - Run `database_schema.sql` to create tables

5. **Test the pipeline**
   ```bash
   TEST_MODE=true python -m src.main
   ```

6. **Deploy to EC2**
   - Follow [ec2_setup.md](ec2_setup.md) for detailed instructions

## 📁 Project Structure

```
ai_slop/
├── src/                    # Source code
│   ├── scrapers/          # Reddit API integration
│   ├── processors/        # Story modification with AI
│   ├── generators/        # Audio, video, subtitle generation
│   ├── uploaders/         # Google Drive, YouTube upload
│   ├── notifiers/         # Email notifications
│   ├── database/          # Database models and queries
│   ├── ai/                # Gemini API integration
│   └── utils/             # Utilities and helpers
├── assets/                # Static assets (bleep sound, etc.)
├── logs/                  # Log files
├── temp/                  # Temporary processing files
└── tests/                 # Test suite
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [guide.md](guide.md) | Complete architecture guide |
| [ec2_setup.md](ec2_setup.md) | AWS EC2 setup instructions |
| [database_schema.sql](database_schema.sql) | Database schema |

## 🔧 Configuration

All configuration is done via environment variables. See [.env.example](.env.example) for all available options.

Key configurations:
- `STORIES_PER_RUN` - Number of stories per scheduled run
- `SCHEDULE_INTERVAL_HOURS` - How often to run the pipeline
- `SUBREDDITS` - Comma-separated list of subreddits to scrape
- `TEST_MODE` - Enable test mode for single-story processing

## 🔄 Pipeline Flow

```
Reddit → AI Processing → TTS → Video Generation → Google Drive → YouTube/Instagram
```

1. **Scrape** - Fetch top stories from configured subreddits
2. **Process** - Modify with AI, add intro/outro, censor cuss words
3. **Generate Audio** - Convert to speech with Google Cloud TTS
4. **Generate Video** - Combine with gameplay, add animated subtitles
5. **Upload** - Store in Google Drive, queue for YouTube
6. **Notify** - Send email with Instagram download links

## 📊 API Limits (Free Tier)

| Service | Limit |
|---------|-------|
| Reddit API | 60 requests/min |
| Gemini AI | 60 requests/min, 1500/day |
| Google Cloud TTS | 1M characters/month |
| YouTube Data API | ~6 uploads/day |
| AWS SES | 62,000 emails/month |

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_scraper.py -v

# Test mode run
TEST_MODE=true python -m src.main
```

## 📝 License

Private project - All rights reserved.

## ⚠️ Disclaimer

This project is for educational purposes. Ensure you comply with:
- Reddit's Terms of Service and API rules
- YouTube's Terms of Service
- Instagram's Terms of Service
- Copyright laws regarding content usage
