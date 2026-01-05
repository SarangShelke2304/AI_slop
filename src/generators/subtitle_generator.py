
from typing import List, Dict

from src.config import settings
from src.utils.helpers import format_duration

class SubtitleGenerator:
    """
    Generates ASS (Advanced Substation Alpha) subtitle files for TikTok-style captions.
    """
    
    def generate_ass(self, word_timings: List[Dict], output_path: str) -> str:
        """
        Create .ass file from word timings.
        """
        header = self._get_header()
        events = self._get_events(word_timings)
        
        content = header + "\n" + events
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return output_path

    def _get_header(self) -> str:
        return f"""[Script Info]
Title: AI Slop Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: {settings.VIDEO_WIDTH}
PlayResY: {settings.VIDEO_HEIGHT}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{settings.SUBTITLE_FONT},60,{settings.SUBTITLE_COLOR},&H000000FF,{settings.SUBTITLE_OUTLINE_COLOR},&H00000000,1,0,0,0,100,100,0,0,1,2,0,5,10,10,250,1
Style: Highlight,{settings.SUBTITLE_FONT},60,{settings.SUBTITLE_HIGHLIGHT_COLOR},&H000000FF,{settings.SUBTITLE_OUTLINE_COLOR},&H00000000,1,0,0,0,110,110,0,0,1,2,0,5,10,10,250,1
Style: Watermark,{settings.SUBTITLE_FONT},30,&H80FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,3,10,10,10,1


[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

    def _get_events(self, word_timings: List[Dict]) -> str:
        events = []
        
        # We display one word at a time or small phrase?
        # TikTok style: usually 1-3 words at a time, fast paced.
        # Given we have individual word timings, let's do 1 word per event for maximum energy.
        # Or allow grouping if words are very short.
        # Let's stick to 1 word per line for "word by word" requirement.
        
        for timing in word_timings:
            start_time = self._format_ass_time(timing["start"])
            end_time = self._format_ass_time(timing["end"])
            word = timing["word"]
            
            # Simple keyword highlighting heuristic:
            # Words > 5 chars or CAPSLOCK words get highlighted
            style = "Default"
            if len(word) > 5 or word.isupper():
                style = "Highlight"
            
            # Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
            event_line = f"Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{word}"
            events.append(event_line)
            
        # Add Waterproof (Static watermark)
        if settings.WATERMARK_TEXT:
            # We want it to last the whole video. We'll use a very long duration or just enough for the story.
            total_duration = word_timings[-1]["end"] + 5 if word_timings else 3600
            events.append(f"Dialogue: 1,0:00:00.00,{self._format_ass_time(total_duration)},Watermark,,0,0,0,,{settings.WATERMARK_TEXT}")
            
            # Add Outro Text (last 3 seconds)
            outro_start = total_duration - 3 if total_duration > 3 else total_duration
            events.append(f"Dialogue: 2,{self._format_ass_time(outro_start)},{self._format_ass_time(total_duration)},Default,,0,0,0,,Follow for more!")

        return "\n".join(events)

    def _format_ass_time(self, seconds: float) -> str:
        """Format seconds to H:MM:SS.cs"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

# Global instance
subtitle_generator = SubtitleGenerator()
