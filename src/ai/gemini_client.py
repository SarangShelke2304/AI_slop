
import json
import asyncio
from typing import List, Optional

from groq import AsyncGroq
from openai import AsyncOpenAI
import google.generativeai as genai

from src.config import settings
from src.utils.logger import logger
from src.utils.retry import retry_gemini # Generic retry logic
from src.ai import prompts

class AIClient:
    def __init__(self):
        self.provider = "none"
        self.client = None
        self.model = None

        # 1. Try Groq (Free Tier Priority)
        if settings.GROQ_API_KEY:
            logger.info("Using Groq AI (Free Tier)")
            self.provider = "groq"
            self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            self.model = "llama-3.3-70b-versatile"
            
        # 2. Try OpenAI (Fallback)
        elif settings.OPENAI_API_KEY:
            logger.info("Using OpenAI AI")
            self.provider = "openai"
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "gpt-3.5-turbo"
            
        # 3. Try Gemini (Legacy Fallback)
        elif settings.GEMINI_API_KEY:
            logger.info("Using Gemini AI")
            self.provider = "gemini"
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = "gemini-1.5-flash"
            
        else:
            logger.warning("No AI API keys set. Processing will fail.")

    @retry_gemini
    async def generate_text(self, prompt: str) -> str:
        """
        Generate text using available provider.
        """
        if not self.provider or self.provider == "none":
            raise ValueError("No AI Provider configured (Missing API Keys)")

        try:
            if self.provider == "groq":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a viral storytelling expert for social media."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
                
            elif self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a creative storytelling assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
                
            elif self.provider == "gemini":
                # Gemini blocking call in executor
                model = genai.GenerativeModel(self.model)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: model.generate_content(prompt)
                )
                return response.text.strip()
                
        except Exception as e:
            logger.error(f"{self.provider} generation failed: {e}")
            raise

    async def modify_story(self, original_content: str, original_title: str) -> str:
        """
        Rewrite story with intro, middle, outro and extension.
        """
        prompt = prompts.STORY_MODIFICATION_PROMPT.format(original_content=original_content)
        return await self.generate_text(prompt)

    async def generate_title(self, original_title: str) -> str:
        """
        Generate viral title.
        """
        prompt = prompts.TITLE_GENERATION_PROMPT.format(original_title=original_title)
        title = await self.generate_text(prompt)
        return title.strip('"\'')

    async def generate_hashtags(self, original_title: str) -> List[str]:
        """
        Generate viral hashtags.
        """
        prompt = prompts.HASHTAG_GENERATION_PROMPT.format(original_title=original_title)
        text = await self.generate_text(prompt)
        tags = [tag.strip() for tag in text.split() if tag.startswith('#')]
        return tags[:10]

    async def generate_cuss_word_list(self) -> List[str]:
        """
        Generate list of cuss words for filtering.
        """
        try:
            text = await self.generate_text(prompts.CUSS_WORD_LIST_PROMPT)
            text = text.replace("```json", "").replace("```", "").strip()
            try:
                data = json.loads(text)
                return data if isinstance(data, list) else []
            except:
                return [w.strip() for w in text.splitlines() if w.strip() and len(w) < 20]
        except Exception as e:
            logger.error(f"Failed to parse cuss word list: {e}")
            return []

# Global instance
gemini_client = AIClient() 
