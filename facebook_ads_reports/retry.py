"""
Retry decorator for handling transient Facebook Marketing API errors.
"""
import logging
import random
import time

from functools import wraps
from requests.exceptions import RequestException
from typing import Any, Callable
from .exceptions import APIError


def retry_on_api_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to retry function calls on transient Facebook Marketing API errors.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Exponential backoff factor
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except RequestException as e:
                    last_exception = e

                    # Check if this is a retryable error
                    if not _is_retryable_error(e):
                        logging.warning(f"Non-retryable error in {func.__name__}: {e}")
                        raise APIError(
                            f"Facebook Ads API error in {func.__name__}",
                            original_error=e,
                            attempt=attempt + 1
                        ) from e

                    # Don't retry on the last attempt
                    if attempt == max_attempts - 1:
                        break

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logging.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )

                    time.sleep(delay)

                except Exception as e:
                    # Non-Facebook Marketing API exceptions are not retried
                    logging.error(f"Unexpected error in {func.__name__}: {e}")
                    raise

            # All retries exhausted
            logging.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise APIError(
                f"Max retries exceeded for {func.__name__}",
                original_error=last_exception,
                max_attempts=max_attempts
            ) from last_exception

        return wrapper
    return decorator


def _is_retryable_error(error: RequestException) -> bool:
    """
    Determine if a RequestException is retryable.

    Args:
        error (RequestException): The RequestException to check

    Returns:
        bool: True if the error should be retried
    """
    # Retry on common transient HTTP status codes
    if hasattr(error, 'response') and error.response is not None:
        if error.response.status_code in {500, 502, 503, 504, 429}:
            return True

    # Retry on common transient error messages
    retryable_messages = [
        'internal error',
        'rate exceeded',
        'quota exceeded',
        'timeout',
        'temporary failure',
        'service unavailable',
        'connection aborted',
        'connection reset',
        'connection refused',
        'connection error',
        'temporarily unavailable',
        'too many requests',
    ]

    error_message = str(error).lower()
    if any(msg in error_message for msg in retryable_messages):
        return True

    return False
