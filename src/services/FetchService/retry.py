import asyncio
import email.utils
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

_MAX_ATTEMPTS = 3
_MIN_WAIT_SECONDS = 1.0
_MAX_WAIT_SECONDS = 10.0

T = TypeVar("T")


class RateLimiter:
    def __init__(self, min_interval_seconds: float):
        self._min_interval_seconds = min_interval_seconds
        self._lock = asyncio.Lock()
        self._last_request_time: float | None = None

    async def wait(self) -> None:
        async with self._lock:
            if self._last_request_time is not None:
                elapsed = time.monotonic() - self._last_request_time
                remaining = self._min_interval_seconds - elapsed

                if remaining > 0:
                    await asyncio.sleep(remaining)

            self._last_request_time = time.monotonic()


def _is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or status_code >= 500

    return False


def _parse_retry_after(header_value: str | None) -> float | None:
    if not header_value:
        return None

    if header_value.isdigit():
        return float(header_value)

    try:
        retry_at = email.utils.parsedate_to_datetime(header_value)
    except (TypeError, ValueError):
        return None

    return max(retry_at.timestamp() - time.time(), 0)


def _backoff_wait(attempt: int) -> float:
    return min(max(2 ** (attempt - 1), _MIN_WAIT_SECONDS), _MAX_WAIT_SECONDS)


def _wait_seconds(exc: BaseException, attempt: int) -> float:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        retry_after = _parse_retry_after(exc.response.headers.get("Retry-After"))
        if retry_after is not None:
            return retry_after

    return _backoff_wait(attempt)


async def retry_request(send_request: Callable[[], Awaitable[T]]) -> T:
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return await send_request()
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if not _is_retryable_error(exc) or attempt == _MAX_ATTEMPTS:
                raise

            await asyncio.sleep(_wait_seconds(exc, attempt))

    raise AssertionError("unreachable")
