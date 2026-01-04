-- ============================================
--          AI SLOP DATABASE SCHEMA
--          PostgreSQL / Supabase
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
--              STORIES TABLE
-- ============================================
-- Stores scraped Reddit stories
CREATE TABLE stories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reddit_id VARCHAR(20) UNIQUE NOT NULL,           -- Reddit post ID
    subreddit VARCHAR(100) NOT NULL,                  -- Source subreddit
    original_title VARCHAR(500) NOT NULL,             -- Original Reddit title
    original_content TEXT NOT NULL,                   -- Original story text
    original_author VARCHAR(100),                     -- Reddit username
    original_url VARCHAR(500),                        -- Reddit post URL
    upvotes INTEGER NOT NULL DEFAULT 0,               -- Upvote count at scrape time
    
    -- Processed content
    processed_title VARCHAR(500),                     -- AI-generated catchy title
    processed_content TEXT,                           -- Modified story with intro/outro
    hashtags TEXT[],                                  -- Generated hashtags array
    suggested_caption TEXT,                           -- AI-generated caption
    
    -- Metadata
    word_count INTEGER,                               -- Total word count
    estimated_duration_seconds INTEGER,               -- Estimated audio duration
    part_count INTEGER DEFAULT 1,                     -- Number of parts after splitting
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'scraped',
    -- Possible statuses: scraped, processing, processed, failed, completed
    
    error_message TEXT,                               -- Error details if failed
    retry_count INTEGER DEFAULT 0,                    -- Number of retries attempted
    
    -- Timestamps
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_stories_subreddit ON stories(subreddit);
CREATE INDEX idx_stories_reddit_id ON stories(reddit_id);
CREATE INDEX idx_stories_scraped_at ON stories(scraped_at);

-- ============================================
--            STORY PARTS TABLE
-- ============================================
-- Individual parts of split stories (for long stories)
CREATE TABLE story_parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    part_number INTEGER NOT NULL,                     -- 1, 2, 3, etc.
    total_parts INTEGER NOT NULL,                     -- Total number of parts
    
    -- Content
    content TEXT NOT NULL,                            -- This part's text content
    word_count INTEGER NOT NULL,
    
    -- Generated title for this part
    title VARCHAR(500),                               -- e.g., "Story Title [Part 1/3]"
    caption TEXT,                                     -- Caption with part info
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- Possible: pending, audio_generated, video_generated, uploaded, completed, failed
    
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(story_id, part_number)
);

CREATE INDEX idx_story_parts_story_id ON story_parts(story_id);
CREATE INDEX idx_story_parts_status ON story_parts(status);

-- ============================================
--              AUDIO FILES TABLE
-- ============================================
-- Generated audio file references
CREATE TABLE audio_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    story_part_id UUID NOT NULL REFERENCES story_parts(id) ON DELETE CASCADE,
    
    -- File info
    local_path VARCHAR(500),                          -- Temporary local path
    duration_seconds FLOAT NOT NULL,                  -- Actual audio duration
    voice_name VARCHAR(100),                          -- TTS voice used
    
    -- Metadata
    character_count INTEGER,                          -- Characters processed
    has_bleep_sounds BOOLEAN DEFAULT FALSE,           -- Whether censoring was applied
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'generated',
    -- Possible: generated, used, deleted, failed
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_audio_files_story_part_id ON audio_files(story_part_id);

-- ============================================
--              VIDEOS TABLE
-- ============================================
-- Generated video file references
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    story_part_id UUID NOT NULL REFERENCES story_parts(id) ON DELETE CASCADE,
    audio_file_id UUID REFERENCES audio_files(id),
    
    -- File info
    filename VARCHAR(255) NOT NULL,                   -- e.g., nosleep_abc123_1.mp4
    local_path VARCHAR(500),                          -- Temporary local path
    drive_file_id VARCHAR(100),                       -- Google Drive file ID
    drive_download_url VARCHAR(500),                  -- Direct download link
    drive_folder_path VARCHAR(500),                   -- Folder path in Drive
    
    -- Video metadata
    duration_seconds FLOAT,
    width INTEGER DEFAULT 720,
    height INTEGER DEFAULT 1280,
    file_size_bytes BIGINT,
    
    -- Gameplay used
    gameplay_filename VARCHAR(255),                   -- Which gameplay video was used
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'generated',
    -- Possible: generated, uploaded_to_drive, youtube_queued, youtube_uploaded, 
    --           instagram_notified, completed, failed
    
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_to_drive_at TIMESTAMP WITH TIME ZONE,
    local_deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_videos_story_part_id ON videos(story_part_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_drive_file_id ON videos(drive_file_id);

-- ============================================
--          YOUTUBE UPLOAD QUEUE
-- ============================================
-- Queue for YouTube uploads (6/day limit)
CREATE TABLE youtube_upload_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    
    -- YouTube info
    youtube_video_id VARCHAR(50),                     -- YouTube video ID after upload
    youtube_url VARCHAR(255),                         -- Public YouTube URL
    
    -- Upload details
    title VARCHAR(100) NOT NULL,                      -- YouTube title (max 100 chars)
    description TEXT,                                 -- Video description
    tags TEXT[],                                      -- YouTube tags
    
    -- Queue management
    priority INTEGER DEFAULT 0,                       -- Higher = upload first
    scheduled_date DATE,                              -- Target upload date
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    -- Possible: queued, uploading, uploaded, failed, cancelled
    
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    queued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_youtube_queue_status ON youtube_upload_queue(status);
CREATE INDEX idx_youtube_queue_scheduled_date ON youtube_upload_queue(scheduled_date);
CREATE INDEX idx_youtube_queue_video_id ON youtube_upload_queue(video_id);

-- ============================================
--          PROCESSING JOBS TABLE
-- ============================================
-- Track each pipeline run for resume capability
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Job info
    job_type VARCHAR(50) NOT NULL,                    -- 'main_pipeline', 'youtube_upload'
    
    -- Progress tracking
    total_stories INTEGER DEFAULT 0,
    processed_stories INTEGER DEFAULT 0,
    failed_stories INTEGER DEFAULT 0,
    
    total_videos INTEGER DEFAULT 0,
    completed_videos INTEGER DEFAULT 0,
    failed_videos INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'started',
    -- Possible: started, in_progress, completed, failed, cancelled
    
    current_stage VARCHAR(100),                       -- Current processing stage
    current_item_id UUID,                             -- Current story/video being processed
    
    error_message TEXT,
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_job_type ON processing_jobs(job_type);

-- ============================================
--            EMAIL LOGS TABLE
-- ============================================
-- Track all sent emails
CREATE TABLE email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Email content
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    email_type VARCHAR(100) NOT NULL,
    -- Types: progress_25, progress_50, progress_75, progress_100, 
    --        daily_summary, instagram_links, error_notification
    
    -- Related entities
    processing_job_id UUID REFERENCES processing_jobs(id),
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'sent',
    -- Possible: sent, failed, bounced
    
    error_message TEXT,
    
    -- Timestamps
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_email_logs_email_type ON email_logs(email_type);
CREATE INDEX idx_email_logs_processing_job_id ON email_logs(processing_job_id);

-- ============================================
--           CUSS WORDS TABLE
-- ============================================
-- Session-generated cuss word list (regenerated each session)
CREATE TABLE cuss_words (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    word VARCHAR(100) NOT NULL,
    replacement VARCHAR(100) DEFAULT '****',
    severity VARCHAR(20) DEFAULT 'medium',            -- low, medium, high
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_cuss_words_word ON cuss_words(LOWER(word));

-- ============================================
--          GAMEPLAY VIDEOS TABLE
-- ============================================
-- Track available gameplay videos from Drive
CREATE TABLE gameplay_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- File info
    drive_file_id VARCHAR(100) UNIQUE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    duration_seconds FLOAT,
    file_size_bytes BIGINT,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,                   -- Can be used for videos
    usage_count INTEGER DEFAULT 0,                    -- Times used
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Sync info
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_gameplay_videos_is_active ON gameplay_videos(is_active);

-- ============================================
--          DAILY STATISTICS TABLE
-- ============================================
-- Daily summary for reporting
CREATE TABLE daily_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE UNIQUE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Counts
    stories_scraped INTEGER DEFAULT 0,
    stories_processed INTEGER DEFAULT 0,
    videos_generated INTEGER DEFAULT 0,
    videos_uploaded_drive INTEGER DEFAULT 0,
    videos_uploaded_youtube INTEGER DEFAULT 0,
    emails_sent INTEGER DEFAULT 0,
    
    -- Failures
    scraping_failures INTEGER DEFAULT 0,
    processing_failures INTEGER DEFAULT 0,
    generation_failures INTEGER DEFAULT 0,
    upload_failures INTEGER DEFAULT 0,
    
    -- API usage
    gemini_requests INTEGER DEFAULT 0,
    tts_characters INTEGER DEFAULT 0,
    youtube_quota_used INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_daily_statistics_date ON daily_statistics(date);

-- ============================================
--               SETTINGS TABLE
-- ============================================
-- Runtime configurable settings (some .env values can be overridden)
CREATE TABLE settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default settings
INSERT INTO settings (key, value, description) VALUES
    ('stories_per_run', '10', 'Number of stories to scrape per run'),
    ('min_upvotes', '100', 'Minimum upvotes required for a story'),
    ('youtube_daily_limit', '6', 'Maximum YouTube uploads per day'),
    ('enable_youtube_upload', 'true', 'Enable/disable YouTube uploads'),
    ('enable_email_notifications', 'true', 'Enable/disable email notifications'),
    ('maintenance_mode', 'false', 'Pause all processing when true');

-- ============================================
--            TRIGGER FUNCTIONS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_stories_updated_at 
    BEFORE UPDATE ON stories 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_story_parts_updated_at 
    BEFORE UPDATE ON story_parts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_youtube_queue_updated_at 
    BEFORE UPDATE ON youtube_upload_queue 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_statistics_updated_at 
    BEFORE UPDATE ON daily_statistics 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
--            USEFUL VIEWS
-- ============================================

-- View: Pending stories ready for processing
CREATE VIEW v_pending_stories AS
SELECT s.*, 
       (SELECT COUNT(*) FROM story_parts sp WHERE sp.story_id = s.id) as parts_created
FROM stories s
WHERE s.status IN ('scraped', 'processing')
ORDER BY s.scraped_at ASC;

-- View: YouTube upload queue with video details
CREATE VIEW v_youtube_queue AS
SELECT 
    yuq.*,
    v.filename,
    v.drive_download_url,
    v.duration_seconds,
    sp.title as part_title,
    s.subreddit
FROM youtube_upload_queue yuq
JOIN videos v ON yuq.video_id = v.id
JOIN story_parts sp ON v.story_part_id = sp.id
JOIN stories s ON sp.story_id = s.id
WHERE yuq.status = 'queued'
ORDER BY yuq.priority DESC, yuq.queued_at ASC;

-- View: Today's statistics
CREATE VIEW v_todays_stats AS
SELECT * FROM daily_statistics 
WHERE date = CURRENT_DATE;

-- View: Resume state for pending jobs
CREATE VIEW v_incomplete_jobs AS
SELECT pj.*,
       s.reddit_id as current_story,
       s.status as story_status
FROM processing_jobs pj
LEFT JOIN stories s ON pj.current_item_id = s.id
WHERE pj.status IN ('started', 'in_progress')
ORDER BY pj.started_at DESC
LIMIT 1;

-- ============================================
--         UTILITY FUNCTIONS
-- ============================================

-- Function: Get next story to process
CREATE OR REPLACE FUNCTION get_next_story_to_process()
RETURNS UUID AS $$
DECLARE
    next_id UUID;
BEGIN
    SELECT id INTO next_id
    FROM stories
    WHERE status = 'scraped'
    ORDER BY scraped_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;
    
    RETURN next_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Get videos ready for YouTube upload today
CREATE OR REPLACE FUNCTION get_youtube_uploads_today()
RETURNS INTEGER AS $$
DECLARE
    upload_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO upload_count
    FROM youtube_upload_queue
    WHERE DATE(uploaded_at) = CURRENT_DATE
    AND status = 'uploaded';
    
    RETURN upload_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Increment daily statistic
CREATE OR REPLACE FUNCTION increment_daily_stat(stat_name TEXT, increment_value INTEGER DEFAULT 1)
RETURNS VOID AS $$
BEGIN
    INSERT INTO daily_statistics (date)
    VALUES (CURRENT_DATE)
    ON CONFLICT (date) DO NOTHING;
    
    EXECUTE format('UPDATE daily_statistics SET %I = %I + $1 WHERE date = CURRENT_DATE', 
                   stat_name, stat_name)
    USING increment_value;
END;
$$ LANGUAGE plpgsql;

-- ============================================
--            INITIAL DATA
-- ============================================

-- Seed common cuss words (will be regenerated by AI each session)
INSERT INTO cuss_words (word, replacement, severity) VALUES
    ('damn', '****', 'low'),
    ('hell', '****', 'low'),
    ('ass', '****', 'medium'),
    ('shit', '****', 'medium'),
    ('fuck', '****', 'high'),
    ('bitch', '****', 'high')
ON CONFLICT DO NOTHING;

-- ============================================
--          SCHEMA VERSION
-- ============================================
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description) VALUES (1, 'Initial schema');
