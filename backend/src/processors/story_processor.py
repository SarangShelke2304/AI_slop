
import asyncio
from typing import List

from src.database.connection import get_db_session
from src.database.queries import DBQueries
from src.database.models import Story
from src.ai.gemini_client import gemini_client
from src.processors.censor import censor_engine
from src.processors.text_splitter import splitter
from src.utils.logger import logger
from src.config import settings

class StoryProcessor:
    async def process_scraped_stories(self, limit: int = 10) -> int:
        """
        Main processing loop.
        1. Fetch scraped stories
        2. Modify with AI
        3. Censor
        4. Split
        5. Save parts
        """
        processed_count = 0
        
        async with get_db_session() as session:
            queries = DBQueries(session)
            stories = await queries.get_scraped_stories(limit=limit)
            
            if not stories:
                logger.info("No scraped stories pending processing.")
                return 0
                
            logger.info(f"Processing {len(stories)} stories...")
            
            # Ensure censor words are loaded
            await censor_engine.load_custom_words()
            
            for story in stories:
                try:
                    logger.info(f"Processing story: {story.reddit_id}")
                    
                    # Update status to processing
                    await queries.update_story_status(story.id, "processing")
                    
                    # 1. AI Modification
                    # Add intro/outro/middle/rewrite
                    modified_content = await gemini_client.modify_story(
                        story.original_content, 
                        story.original_title
                    )
                    
                    # 2. Extend if too short (handled by prompt, but check here)
                    # If very short, might need another pass? 
                    # For now assume prompt handles it or we accept slightly short
                    
                    # 3. Generate Metadata
                    new_title = await gemini_client.generate_title(story.original_title)
                    hashtags = await gemini_client.generate_hashtags(new_title)
                    
                    # 4. Censor
                    censored_content = await censor_engine.censor_text(modified_content)
                    
                    # 5. Split
                    parts_data = splitter.split_story(censored_content)
                    
                    # 6. Save Updates
                    story.processed_content = censored_content # Storing censored version
                    story.processed_title = new_title
                    story.hashtags = hashtags
                    story.word_count = len(censored_content.split())
                    story.estimated_duration_seconds = splitter.estimate_duration(censored_content)
                    story.part_count = len(parts_data)
                    story.status = "processed"
                    story.processed_at = datetime.utcnow() # Use func.now() in model, but here explicitly helpful for tracking
                    # In python use datetime.now() if needed, but model handles it
                    
                    # Add parts to list for creation
                    final_parts = []
                    for p in parts_data:
                        part_dict = {
                            "story_id": story.id,
                            "part_number": p["part_number"],
                            "total_parts": p["total_parts"],
                            "content": p["content"],
                            "word_count": p["word_count"],
                            "status": "pending",
                            # Title for part: "Title [Part 1/3]"
                            "title": f"{new_title} [Part {p['part_number']}/{p['total_parts']}]" if p["total_parts"] > 1 else new_title
                        }
                        final_parts.append(part_dict)
                        
                    await queries.create_story_parts(final_parts)
                    
                    # Flush updates
                    session.add(story)
                    await session.commit()
                    
                    processed_count += 1
                    logger.info(f"Successfully processed story {story.reddit_id} into {story.part_count} parts.")
                    
                except Exception as e:
                    logger.error(f"Error processing story {story.reddit_id}: {e}")
                    await queries.update_story_status(story.id, "failed", error=str(e))
                    await session.commit()

        # Update daily stats
        async with get_db_session() as session:
             queries = DBQueries(session)
             await queries.update_daily_stats("stories_processed", processed_count)
             
        return processed_count

# Global instance
processor = StoryProcessor()
from datetime import datetime # Fix missing import
