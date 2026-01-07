
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import namedtuple

from src.config import settings
from src.utils.logger import logger
from src.utils.retry import retry_reddit
from src.database.connection import get_db_session
from src.database.queries import DBQueries

# Mimic PRAW Submission object for compatibility
Submission = namedtuple('Submission', ['id', 'title', 'selftext', 'author', 'url', 'score', 'stickied', 'distinguished', 'created_utc'])

class RedditScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": settings.REDDIT_USER_AGENT
        }
        self.base_url = "https://www.reddit.com"

    @retry_reddit
    async def _fetch_subreddit_posts(self, client: httpx.AsyncClient, subreddit_name: str, limit: int = 10) -> List[Submission]:
        """
        Fetch posts from a subreddit using JSON endpoint (No Auth).
        """
        # Mapping sort config to URL
        sort = settings.STORY_SORT  # top, hot, new
        time_filter = settings.STORY_TIME_FILTER # day, week, month, year, all (only for top)
        
        url = f"{self.base_url}/r/{subreddit_name}/{sort}.json"
        
        params = {
            "limit": limit,
            "t": time_filter if sort == "top" else None
        }
        
        response = await client.get(url, params=params, headers=self.headers)
        
        if response.status_code == 429:
            logger.warning("Rate limited by Reddit. Sleeping...")
            raise Exception("Rate limited") # Trigger retry
            
        if response.status_code != 200:
            logger.error(f"Failed to fetch r/{subreddit_name}: {response.status_code} {response.text}")
            return []
            
        data = response.json()
        children = data.get("data", {}).get("children", [])
        
        submissions = []
        for child in children:
            post_data = child.get("data", {})
            
            # Create object similar to PRAW submission
            sub = Submission(
                id=post_data.get("id"),
                title=post_data.get("title"),
                selftext=post_data.get("selftext", ""),
                author=type('Author', (), {'name': post_data.get("author")}), # Hack for getattr(post.author, 'name')
                url=post_data.get("url"),
                score=post_data.get("score", 0),
                stickied=post_data.get("stickied", False),
                distinguished=post_data.get("distinguished"),
                created_utc=post_data.get("created_utc")
            )
            submissions.append(sub)
            
        return submissions

    async def scrape_stories(self, limit: int = None) -> int:
        """
        Main scraping logic.
        Fetches stories from all configured subreddits.
        Stores new valid stories to database.
        Returns count of new stories added.
        """
        if limit is None:
            limit = settings.STORIES_PER_RUN
            
        logger.info(f"Starting scrape run (JSON method). Target: {limit} stories.")
        new_stories_count = 0
        
        subreddits = settings.SUBREDDITS
        if not subreddits:
            logger.warning("No subreddits configured.")
            return 0
            
        limit_per_sub = max(2, int(limit / len(subreddits)) + 1)
        
        async with httpx.AsyncClient() as client:
            async with get_db_session() as session:
                queries = DBQueries(session)
                
                for sub_name in subreddits:
                    try:
                        logger.info(f"Scraping r/{sub_name}...")
                        
                        # No need for executor, httpx is async
                        posts = await self._fetch_subreddit_posts(client, sub_name, limit=limit_per_sub)
                        
                        for post in posts:
                            # 1. Filter checks
                            if post.score < settings.MIN_UPVOTES:
                                logger.debug(f"Skipping post {post.id}: Score {post.score} < {settings.MIN_UPVOTES}")
                                continue
                                
                            if post.stickied or post.distinguished:
                                logger.debug(f"Skipping post {post.id}: Stickied/Distinguished")
                                continue
                                
                            # Check if already processed
                            existing = await queries.get_story_by_reddit_id(post.id)
                            if existing:
                                logger.debug(f"Skipping post {post.id}: Already in database")
                                continue
                                
                            # Basic content validation (ignore image-only posts)
                            if not post.selftext:
                                logger.debug(f"Skipping post {post.id}: No text content")
                                continue
                                
                            word_count = len(post.selftext.split())
                            if word_count < 50:
                                logger.debug(f"Skipping post {post.id}: Content too short ({word_count} words)")
                                continue

                            # 2. Store to DB
                            story_data = {
                                "reddit_id": post.id,
                                "subreddit": sub_name,
                                "original_title": post.title,
                                "original_content": post.selftext,
                                "original_author": getattr(post.author, 'name', "[deleted]"),
                                "original_url": post.url,
                                "upvotes": post.score,
                                "status": "scraped"
                            }
                            
                            await queries.create_story(story_data)
                            new_stories_count += 1
                            logger.info(f"Saved story: {post.title[:50]}... ({post.id})")
                            
                            if new_stories_count >= limit:
                                break
                                
                    except Exception as e:
                        logger.error(f"Error scraping r/{sub_name}: {e}")
                        # Continue to next subreddit
                    
                    if new_stories_count >= limit:
                        break
        
        # Update stats
        async with get_db_session() as session:
             queries = DBQueries(session)
             await queries.update_daily_stats("stories_scraped", new_stories_count)
             
        logger.info(f"Scraping completed. Added {new_stories_count} new stories.")
        return new_stories_count

# Global instance
scraper = RedditScraper()
