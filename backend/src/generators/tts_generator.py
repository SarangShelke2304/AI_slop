
import random
import edge_tts
from typing import Tuple, List, Dict

from src.config import settings
from src.utils.logger import logger
from src.utils.retry import with_retry

class TTSGenerator:
    def __init__(self):
        # Edge TTS voices (High Quality Neural)
        # We can dynamically fetch these, but for speed we list popular English ones
        self.voices = [
            "en-US-GuyNeural",
            "en-US-ChristopherNeural",
            "en-US-EricNeural",
            "en-US-AriaNeural",
            "en-US-JennyNeural",
            "en-US-MichelleNeural"
        ]

    def _get_random_voice(self) -> str:
        """
        Select a random voice or use configured override.
        """
        if settings.TTS_VOICE and settings.TTS_VOICE in self.voices:
            # If specifically configured, maybe user wants consistent voice?
            # But "random" adds variety. 
            # If TTS_VOICE is just a default fallback, we ignore it?
            # Let's say: if user set a specific voice in env that is NOT default, use it?
            # Simpler: Just randomize from list for variety unless hardcoded in code.
            pass
            
        return random.choice(self.voices)

    @with_retry(max_attempts=3)
    async def generate_audio(self, text: str, output_path: str) -> Tuple[float, str, List[Dict]]:
        """
        Generate audio from text using Edge TTS.
        Returns: (duration_seconds, voice_name, word_timings)
        """
        voice = self._get_random_voice()
        communicate = edge_tts.Communicate(text, voice)
        
        word_timings = []
        duration_sec = 0.0
        
        # We need to capture audio and timing events
        # edge-tts streaming yields (offset, chunk, type) or similar objects
        # Official API: 
        # async for chunk in communicate.stream():
        #   if chunk["type"] == "audio": ...
        #   elif chunk["type"] == "WordBoundary": ...
        
        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # Chunk structure: 
                    # {
                    #   "type": "WordBoundary",
                    #   "offset": 12345 (ticks? 100ns units usually),
                    #   "duration": 123,
                    #   "text": "word"
                    # }
                    # Microsoft typically uses 100-nanosecond units (ticks) for offset/duration.
                    # 1 second = 10,000,000 ticks.
                    
                    start_sec = chunk["offset"] / 10_000_000
                    dur_sec = chunk["duration"] / 10_000_000
                    
                    word_timings.append({
                        "word": chunk["text"],
                        "start": start_sec,
                        "end": start_sec + dur_sec
                    })
                    
                    # Track max duration from last word end
                    if (start_sec + dur_sec) > duration_sec:
                        duration_sec = start_sec + dur_sec

        logger.info(f"Generated TTS audio ({duration_sec:.2f}s) with voice {voice}")
        
        return duration_sec, voice, word_timings

# Global instance
tts_engine = TTSGenerator()
