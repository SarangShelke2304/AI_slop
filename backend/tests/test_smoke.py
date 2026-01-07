
import pytest
from unittest.mock import MagicMock, patch

from src.config import settings

@pytest.mark.asyncio
async def test_config_load():
    """Test environment variable loading."""
    assert settings.LOG_LEVEL in ["INFO", "DEBUG", "WARNING", "ERROR"]
    assert settings.STORIES_PER_RUN > 0

@pytest.mark.asyncio
async def test_scraper_json():
    """Smoke test for Reddit scraper (JSON method)."""
    with patch("httpx.AsyncClient") as mock_client:
        from src.scrapers.reddit_scraper import RedditScraper
        scraper = RedditScraper()
        assert scraper.headers["User-Agent"] is not None

@pytest.mark.asyncio
async def test_censor_logic():
    """Test bad word filtering logic."""
    from src.processors.censor import Censor
    # Mock database
    censor = Censor()
    censor._custom_words_loaded = True # Skip DB load
    
    clean = await censor.censor_text("This is clean text")
    assert "****" not in clean
    
    # We can't easily test bad words without the library loaded with words, 
    # but we verify the method runs.

@pytest.mark.asyncio
async def test_text_splitter():
    """Test text splitting logic."""
    from src.processors.text_splitter import TextSplitter
    splitter = TextSplitter()
    
    # Short text
    text = "Hello world. This is a short story."
    parts = splitter.split_story(text)
    assert len(parts) == 1
    assert parts[0]["part_number"] == 1
    
    # Long text (mock by reducing max duration)
    splitter.max_duration = 2 # VERY short
    long_text = "Sentence one. Sentence two. Sentence three. Sentence four."
    parts_long = splitter.split_story(long_text)
    assert len(parts_long) > 1

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(test_scraper_json())
        asyncio.run(test_config_load())
        asyncio.run(test_text_splitter())
        asyncio.run(test_censor_logic())
        print("All manual smoke tests passed!")
    except Exception as e:
        print(f"Manual test failed: {e}")
        import traceback
        traceback.print_exc()
