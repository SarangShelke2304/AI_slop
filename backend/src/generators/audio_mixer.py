
from pathlib import Path
from pydub import AudioSegment

from src.config import settings
from src.utils.logger import logger
from src.processors.censor import censor_engine

class AudioMixer:
    def __init__(self):
        self.bleep_path = settings.ASSETS_DIR / "bleep.mp3"
        self._bleep_sound = None
        
        # Configure FFmpeg path for pydub if provided
        if settings.FFMPEG_PATH:
            logger.info(f"Setting Pydub FFmpeg converter to: {settings.FFMPEG_PATH}")
            AudioSegment.converter = settings.FFMPEG_PATH

    def _load_bleep(self):
        if not self._bleep_sound:
            if self.bleep_path.exists():
                self._bleep_sound = AudioSegment.from_mp3(str(self.bleep_path))
            else:
                # Fallback: Sine wave if file missing
                from pydub.generators import Sine
                self._bleep_sound = Sine(1000).to_audio_segment(duration=300).apply_gain(-5)

    async def mix_audio(self, story_content: str, tts_audio_path: str, word_timings: list) -> str:
        """
        Insert bleep sounds at cuss word locations.
        Overwrite the original audio file with mixed version.
        Returns path to mixed audio.
        """
        self._load_bleep()
        
        original_audio = AudioSegment.from_mp3(tts_audio_path)
        mixed_audio = original_audio
        
        # Find cuss words to bleep
        bleep_words = await censor_engine.get_bleep_locations(story_content)
        
        # Match censor locations to word timings
        # This is heuristic: we assume 'get_bleep_locations' returns word list
        # and 'word_timings' has matching sequence.
        
        # We need to map the words. Since censoring replaced chars with '*',
        # we check the text content. Wait, `story_content` passed here 
        # should be the *original* uncensored text for detection, 
        # OR `story_content` is censored text and we check for asterisks?
        # The `tts_generator` receives CENSORED text (from story processor). 
        # So TTS pronounces "star star star star".
        # We want to overlay bleep on that.
        
        bleep_indices = []
        words = story_content.split()
        for i, word in enumerate(words):
            if "****" in word or "*" * len(word) in word:
                bleep_indices.append(i)
        
        # Overlay bleeps
        for idx in bleep_indices:
            if idx < len(word_timings):
                timing = word_timings[idx]
                start_ms = int(timing["start"] * 1000)
                end_ms = int(timing["end"] * 1000)
                duration_ms = end_ms - start_ms
                
                # Resize bleep to fit word duration (min 200ms)
                bleep_dur = max(200, duration_ms)
                bleep_segment = self._bleep_sound[:bleep_dur]
                
                # Overlay (mute original section + overlay bleep)
                # Muting original is effectively done since it's just silence/unintelligible "asterisk"
                # But creating a clean censor: 
                # Crossfade or just overlay? Overlay is simpler.
                
                mixed_audio = mixed_audio.overlay(bleep_segment, position=start_ms)

        # Export over original
        mixed_audio.export(tts_audio_path, format="mp3")
        return tts_audio_path

# Global instance
audio_mixer = AudioMixer()
