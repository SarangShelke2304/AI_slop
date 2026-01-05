
from datetime import datetime, date
from typing import List, Optional, Any
from uuid import UUID

from sqlalchemy import select, update, func, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import joinedload

from src.database.models import (
    Story, StoryPart, Video, ProcessingJob, DailyStatistic, 
    CussWord, GameplayVideo, YoutubeUploadQueue, EmailLog, AppSettings
)
from src.utils.logger import logger

class DBQueries:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_story_by_reddit_id(self, reddit_id: str) -> Optional[Story]:
        result = await self.session.execute(
            select(Story).where(Story.reddit_id == reddit_id)
        )
        return result.scalars().first()

    async def create_story(self, story_data: dict) -> Story:
        story = Story(**story_data)
        self.session.add(story)
        await self.session.flush()
        return story

    async def get_scraped_stories(self, limit: int = 10) -> List[Story]:
        result = await self.session.execute(
            select(Story)
            .where(Story.status == "scraped")
            .order_by(Story.scraped_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_story_status(self, story_id: UUID, status: str, error: str = None) -> None:
        values = {"status": status}
        if error:
            values["error_message"] = error
        
        await self.session.execute(
            update(Story)
            .where(Story.id == story_id)
            .values(**values)
        )

    async def create_story_parts(self, parts_data: List[dict]) -> List[StoryPart]:
        parts = [StoryPart(**data) for data in parts_data]
        self.session.add_all(parts)
        await self.session.flush()
        return parts

    async def get_pending_parts_for_audio(self, limit: int = 10) -> List[StoryPart]:
        result = await self.session.execute(
            select(StoryPart)
            .options(joinedload(StoryPart.story)) # Eagerly load story
            .where(StoryPart.status == "pending")
            # Join to ensure story is processed
            .join(Story)
            .where(Story.status == "processed")
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_active_gameplay_videos(self) -> List[GameplayVideo]:
        result = await self.session.execute(
            select(GameplayVideo)
            .where(GameplayVideo.is_active == True)
            .order_by(func.random()) # Postgres random order
        )
        return list(result.scalars().all())

    async def update_daily_stats(self, field: str, increment: int = 1) -> None:
        """Increment daily statistic safely."""
        today = date.today()
        stmt = insert(DailyStatistic).values(date=today).on_conflict_do_update(
            index_elements=['date'],
            set_={field: DailyStatistic.__table__.c[field] + increment}
        )
        await self.session.execute(stmt)

    async def create_processing_job(self, job_type: str) -> ProcessingJob:
        job = ProcessingJob(job_type=job_type, status="started")
        self.session.add(job)
        await self.session.flush()
        return job
        
    async def update_job_heartbeat(self, job_id: UUID) -> None:
        await self.session.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id == job_id)
            .values(last_heartbeat=func.now())
        )

    async def get_cuss_words(self) -> List[str]:
        result = await self.session.execute(select(CussWord.word))
        return list(result.scalars().all())

    async def bulk_add_cuss_words(self, words: List[str]) -> int:
        count = 0
        for word in words:
            word = word.lower().strip()
            stmt = insert(CussWord).values(word=word, replacement="****").on_conflict_do_nothing()
            result = await self.session.execute(stmt)
            if result.rowcount > 0:
                count += 1
        return count

    async def get_youtube_queue(self, limit: int = 6) -> List[YoutubeUploadQueue]:
        result = await self.session.execute(
             select(YoutubeUploadQueue)
             .where(YoutubeUploadQueue.status == 'queued')
             .join(Video) # Ensure video exists
             .order_by(YoutubeUploadQueue.priority.desc(), YoutubeUploadQueue.queued_at.asc())
             .limit(limit)
        )
        return list(result.scalars().all())

    async def get_incomplete_stories(self) -> List[Story]:
        """Get stories that were stuck in processing."""
        result = await self.session.execute(
            select(Story)
            .where(Story.status.in_(['processing', 'audio_generated']))
        )
        return list(result.scalars().all())
