
import re
from typing import List, Tuple
from better_profanity import profanity

from src.ai.gemini_client import gemini_client
from src.database.connection import get_db_session
from src.database.queries import DBQueries
from src.utils.logger import logger

class Censor:
    def __init__(self):
        self._custom_words_loaded = False
        # Set default replacement
        profanity.load_censor_words()
        
    async def load_custom_words(self):
        """
        Load cuss words from database into profanity filter.
        If DB is empty, generate initial list from AI.
        """
        if self._custom_words_loaded:
            return

        async with get_db_session() as session:
            queries = DBQueries(session)
            db_words = await queries.get_cuss_words()
            
            if not db_words:
                logger.info("No cuss words in DB. Generating from AI...")
                ai_words = await gemini_client.generate_cuss_word_list()
                if ai_words:
                    await queries.bulk_add_cuss_words(ai_words)
                    db_words = ai_words
            
            if db_words:
                profanity.add_censor_words(db_words)
                logger.info(f"Loaded {len(db_words)} cuss words into filter.")
                self._custom_words_loaded = True

    async def censor_text(self, text: str) -> str:
        """
        Replace cuss words with ****.
        """
        await self.load_custom_words()
        return profanity.censor(text, censor_char="*")

    async def get_bleep_locations(self, text: str) -> List[dict]:
        """
        Analyze text to find locations of censored words for audio bleeping.
        Returns list of dicts with word and approximate position.
        Note: Precise timestamping happens during TTS alignment, 
        this might be used for heuristic checks.
        """
        await self.load_custom_words()
        
        # This is a complex task because 'profanity' lib returns censored text string
        # but doesn't give positions.
        # We will iterate through words and check if they are censored.
        
        words = text.split()
        bleep_words = []
        
        for i, word in enumerate(words):
            if profanity.contains_profanity(word):
                bleep_words.append({
                    "word": word,
                    "index": i
                })
                
        return bleep_words

# Global instance
censor_engine = Censor()
