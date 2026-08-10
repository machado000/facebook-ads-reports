"""
Retry decorator for handling transient Facebook Marketing API errors.
"""
import logging
import random
import time

from functools import wraps
from requests.exceptions import RequestException
from typing import Any, Callable
from .exceptions import APIError, AuthenticationError

# HTTP statuses worth retrying regardless of the payload's error code.
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Graph API codes documented as temporary: 1 = API Unknown, 2 = API Service.
TRANSIENT_ERROR_CODES = {1, 2}


def retry_on_api_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    rate_limit_delay: float = 60.0
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to retry function calls on transient Facebook Marketing API errors.

    Retries two distinct failure classes:
    - RequestException: connection-level failures (timeouts, resets).
    - APIError: non-200 responses the API reported as throttling or transient.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Exponential backoff factor
        jitter: Add random jitter to prevent thundering herd
        rate_limit_delay: Delay floor for rate-limit errors, in seconds. Applied instead
            of `max_delay` because retrying an app-level limit within a few seconds
            simply burns quota. A `Retry-After` header, when present, wins over both.

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except (APIError, RequestException) as e:
                    last_exception = e

                    # requests only raises RequestException for connection-level problems.
                    # A non-200 response arrives here as the APIError raised by the client.
                    if isinstance(e, APIError):
                        retryable = _is_retryable_api_error(e)
                    else:
                        retryable = _is_retryable_error(e)

                    if not retryable:
                        logging.warning(f"Non-retryable error in {func.__name__}: {e}")
                        if isinstance(e, APIError):
                            raise
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

                    # A few seconds is useless against an app-level limit; wait longer.
                    if isinstance(e, APIError) and e.context.get("is_rate_limit"):
                        delay = max(delay, rate_limit_delay)

                    # The server's own instruction outranks our backoff curve.
                    retry_after = e.context.get("retry_after") if isinstance(e, APIError) else None
                    if retry_after:
                        delay = float(retry_after)

                    logging.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )

                    time.sleep(delay)

                except AuthenticationError as e:
                    # Credentials will not fix themselves; retrying only wastes quota.
                    logging.error(f"Authentication failed in {func.__name__}: {e}")
                    raise

                except Exception as e:
                    # Non-Facebook Marketing API exceptions are not retried
                    logging.error(f"Unexpected error in {func.__name__}: {e}")
                    raise

            # All retries exhausted. Carry the last error's context forward so the
            # raised exception is self-describing without unwrapping original_error.
            logging.error(f"All {max_attempts} attempts failed for {func.__name__}")
            final_context = dict(getattr(last_exception, "context", {}))
            final_context["max_attempts"] = max_attempts
            raise APIError(
                f"Max retries exceeded for {func.__name__}",
                original_error=last_exception,
                **final_context
            ) from last_exception

        return wrapper
    return decorator


def _is_retryable_api_error(error: APIError) -> bool:
    """
    Determine if an APIError raised from a non-200 response is retryable.

    Args:
        error (APIError): The error, carrying response context set by the client.

    Returns:
        bool: True if the request should be retried.
    """
    context = error.context

    # The API told us so directly.
    if context.get("is_transient") or context.get("is_rate_limit"):
        return True

    status_code = context.get("status_code")
    if isinstance(status_code, int) and status_code in RETRYABLE_STATUS_CODES:
        return True

    # Graph "API Unknown" (1) and "API Service" (2) are documented as temporary.
    if context.get("error_code") in TRANSIENT_ERROR_CODES:
        return True

    return False


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
