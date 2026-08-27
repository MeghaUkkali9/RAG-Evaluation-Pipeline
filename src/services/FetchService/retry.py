import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

retry_on_transient_error = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    reraise=True,
)
