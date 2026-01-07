
import time
import functools
from typing import Type, Tuple, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.utils.logger import logger

def log_retry_attempt(retry_state):
    """Log retry attempts."""
    logger.warning(
        f"Retrying {retry_state.fn.__name__} due to {retry_state.outcome.exception()} "
        f"- Attempt {retry_state.attempt_number}"
    )

def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=log_retry_attempt,
        reraise=True
    )

# Pre-configured decorators for common services

# Reddit API Retry (Rate limits, network)
retry_reddit = with_retry(
    max_attempts=3, 
    min_wait=30.0, 
    max_wait=60.0
)

# Gemini API Retry
retry_gemini = with_retry(
    max_attempts=3, 
    min_wait=5.0, 
    max_wait=30.0
)

# Google Drive/YouTube Retry
retry_google_api = with_retry(
    max_attempts=3, 
    min_wait=10.0, 
    max_wait=60.0
)

# Database Retry
retry_db = with_retry(
    max_attempts=5, 
    min_wait=1.0, 
    max_wait=10.0
)
