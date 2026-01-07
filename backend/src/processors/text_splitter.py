
import math
from typing import List, Dict, Any

from src.config import settings

class TextSplitter:
    def __init__(self):
        self.words_per_minute = 150  # Average speaking rate
        self.max_duration = settings.MAX_VIDEO_DURATION_SECONDS
        
    def estimate_duration(self, text: str) -> int:
        """
        Estimate audio duration in seconds based on word count.
        """
        word_count = len(text.split())
        return math.ceil((word_count / self.words_per_minute) * 60)

    def split_story(self, text: str) -> List[Dict[str, Any]]:
        """
        Split story into parts if it exceeds max duration.
        Returns list of dicts:
        [
            {"part_number": 1, "content": "...", "word_count": ...},
            {"part_number": 2, "content": "...", "word_count": ...}
        ]
        """
        # Split into sentences to avoid cutting mid-sentence
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        parts = []
        current_part_sentences = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence_word_count = len(sentence.split())
            
            # Check if adding this sentence exceeds limit
            # Limit is in words approx equivalent to MAX_VIDEO_DURATION
            # e.g., 60s -> 150 words
            max_words = (self.max_duration / 60) * self.words_per_minute
            
            if current_word_count + sentence_word_count > max_words and current_part_sentences:
                # Finish current part
                part_content = " ".join(current_part_sentences)
                parts.append({
                    "content": part_content,
                    "word_count": current_word_count
                })
                
                # Start new part
                current_part_sentences = [sentence]
                current_word_count = sentence_word_count
            else:
                current_part_sentences.append(sentence)
                current_word_count += sentence_word_count
        
        # Add final part
        if current_part_sentences:
            part_content = " ".join(current_part_sentences)
            parts.append({
                "content": part_content,
                "word_count": current_word_count
            })
            
        # Add part numbers
        for i, part in enumerate(parts):
            part["part_number"] = i + 1
            part["total_parts"] = len(parts)
            
        return parts

# Global instance
splitter = TextSplitter()

