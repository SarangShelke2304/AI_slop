
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, 
    ARRAY, Date
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class Story(Base):
    __tablename__ = "stories"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    reddit_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False)
    original_title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    original_author: Mapped[Optional[str]] = mapped_column(String(100))
    original_url: Mapped[Optional[str]] = mapped_column(String(500))
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    
    processed_title: Mapped[Optional[str]] = mapped_column(String(500))
    processed_content: Mapped[Optional[str]] = mapped_column(Text)
    hashtags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    suggested_caption: Mapped[Optional[str]] = mapped_column(Text)
    
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    estimated_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    part_count: Mapped[int] = mapped_column(Integer, default=1)
    
    status: Mapped[str] = mapped_column(String(50), default="scraped")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    parts: Mapped[List["StoryPart"]] = relationship(back_populates="story", cascade="all, delete-orphan")

class StoryPart(Base):
    __tablename__ = "story_parts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    story_id: Mapped[UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"))
    part_number: Mapped[int] = mapped_column(Integer, nullable=False)
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    title: Mapped[Optional[str]] = mapped_column(String(500))
    caption: Mapped[Optional[str]] = mapped_column(Text)
    
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    story: Mapped["Story"] = relationship(back_populates="parts")
    audio_files: Mapped[List["AudioFile"]] = relationship(back_populates="story_part", cascade="all, delete-orphan")
    videos: Mapped[List["Video"]] = relationship(back_populates="story_part", cascade="all, delete-orphan")

class AudioFile(Base):
    __tablename__ = "audio_files"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    story_part_id: Mapped[UUID] = mapped_column(ForeignKey("story_parts.id", ondelete="CASCADE"))
    
    local_path: Mapped[Optional[str]] = mapped_column(String(500))
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    voice_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    character_count: Mapped[Optional[int]] = mapped_column(Integer)
    has_bleep_sounds: Mapped[bool] = mapped_column(Boolean, default=False)
    
    status: Mapped[str] = mapped_column(String(50), default="generated")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    story_part: Mapped["StoryPart"] = relationship(back_populates="audio_files")

class Video(Base):
    __tablename__ = "videos"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    story_part_id: Mapped[UUID] = mapped_column(ForeignKey("story_parts.id", ondelete="CASCADE"))
    audio_file_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("audio_files.id"))
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    local_path: Mapped[Optional[str]] = mapped_column(String(500))
    drive_file_id: Mapped[Optional[str]] = mapped_column(String(100))
    drive_download_url: Mapped[Optional[str]] = mapped_column(String(500))
    drive_folder_path: Mapped[Optional[str]] = mapped_column(String(500))
    
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    width: Mapped[int] = mapped_column(Integer, default=720)
    height: Mapped[int] = mapped_column(Integer, default=1280)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    
    gameplay_filename: Mapped[Optional[str]] = mapped_column(String(255))
    
    status: Mapped[str] = mapped_column(String(50), default="generated")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    uploaded_to_drive_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    local_deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    story_part: Mapped["StoryPart"] = relationship(back_populates="videos")
    youtube_upload_items: Mapped[List["YoutubeUploadQueue"]] = relationship(back_populates="video", cascade="all, delete-orphan")

class YoutubeUploadQueue(Base):
    __tablename__ = "youtube_upload_queue"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(50))
    youtube_url: Mapped[Optional[str]] = mapped_column(String(255))
    
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    
    priority: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_date: Mapped[Optional[Date]] = mapped_column(Date)
    
    status: Mapped[str] = mapped_column(String(50), default="queued")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    video: Mapped["Video"] = relationship(back_populates="youtube_upload_items")

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    total_stories: Mapped[int] = mapped_column(Integer, default=0)
    processed_stories: Mapped[int] = mapped_column(Integer, default=0)
    failed_stories: Mapped[int] = mapped_column(Integer, default=0)
    
    total_videos: Mapped[int] = mapped_column(Integer, default=0)
    completed_videos: Mapped[int] = mapped_column(Integer, default=0)
    failed_videos: Mapped[int] = mapped_column(Integer, default=0)
    
    status: Mapped[str] = mapped_column(String(50), default="started")
    current_stage: Mapped[Optional[str]] = mapped_column(String(100))
    current_item_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    email_logs: Mapped[List["EmailLog"]] = relationship(back_populates="processing_job")

class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    email_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    processing_job_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("processing_jobs.id"))
    
    status: Mapped[str] = mapped_column(String(50), default="sent")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    processing_job: Mapped["ProcessingJob"] = relationship(back_populates="email_logs")

class CussWord(Base):
    __tablename__ = "cuss_words"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    word: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    replacement: Mapped[Optional[str]] = mapped_column(String(100), default="****")
    severity: Mapped[Optional[str]] = mapped_column(String(20), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

class GameplayVideo(Base):
    __tablename__ = "gameplay_videos"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    drive_file_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

class DailyStatistic(Base):
    __tablename__ = "daily_statistics"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    date: Mapped[Date] = mapped_column(Date, unique=True, nullable=False, default=func.current_date())
    
    stories_scraped: Mapped[int] = mapped_column(Integer, default=0)
    stories_processed: Mapped[int] = mapped_column(Integer, default=0)
    videos_generated: Mapped[int] = mapped_column(Integer, default=0)
    videos_uploaded_drive: Mapped[int] = mapped_column(Integer, default=0)
    videos_uploaded_youtube: Mapped[int] = mapped_column(Integer, default=0)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0)
    
    scraping_failures: Mapped[int] = mapped_column(Integer, default=0)
    processing_failures: Mapped[int] = mapped_column(Integer, default=0)
    generation_failures: Mapped[int] = mapped_column(Integer, default=0)
    upload_failures: Mapped[int] = mapped_column(Integer, default=0)
    
    gemini_requests: Mapped[int] = mapped_column(Integer, default=0)
    tts_characters: Mapped[int] = mapped_column(Integer, default=0)
    youtube_quota_used: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

class AppSettings(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
