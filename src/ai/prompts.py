
"""
Prompt templates for Gemini AI.
"""

# Story modification prompt (rewrite, add sections)
STORY_MODIFICATION_PROMPT = """
You are a professional storyteller. Your task is to modify a Reddit story for a viral video.
Make it engaging, spoken-word friendly, and slightly dramatic.

STORY:
{original_content}

TASKS:
1. Add a short 2-3 sentence introduction (hook the listener).
2. Insert 2-3 sentences in the middle to build tension or add detail (at approx 50% point).
3. Add a 2-3 sentence outro (climax or reflection).
4. If story is under 300 words, extend it creatively while keeping the original plot.
5. Lightly reword the rest to flow better as spoken audio.
6. REMOVE any Reddit-specific jargon (e.g., "EDITS:","Thanks for the silver","tl;dr").
7. Ensure the final tone matches the genre (Scary -> Spooky, AITA -> Conversational).

OUTPUT FORMAT:
Return ONLY the modified story text. Do not include "Introduction:", "Middle:", etc. just the flowing story.
"""

# Cuss word censoring prompt
CUSS_WORD_DETECTION_PROMPT = """
Analyze the provided text and identify all profanity, cuss words, and slurs that should be censored for a PG-13 audience.
Return a JSON list of words found.

TEXT:
{text}
"""

# Cuss word list generation prompt (for session start)
CUSS_WORD_LIST_PROMPT = """
Generate a list of 50 common English cuss words, profanities, and slurs that should be censored on social media (Instagram/YouTube).
Include variations (e.g., f*ck, f**k, shit, s**t).
Return ONLY a Python list of strings, e.g. ["word1", "word2"...]
"""

# Title generation prompt
TITLE_GENERATION_PROMPT = """
Generate a short, viral, clickbait-style title for this story.
Max 60 characters.
Do not use quotes.
Examples: "My Stalker Returned...", "I Refused to Pay...", "The Noise in the Basement"

STORY SUMMARY/TITLE:
{original_title}
"""

# Hashtag generation prompt
HASHTAG_GENERATION_PROMPT = """
Generate 5-7 viral hashtags for this story for Instagram Reels / YouTube Shorts.
Include general tags like #redditstories #fyp and genre specific ones.
Return as a space-separated string. e.g. #reddit #viral #scary
"""
