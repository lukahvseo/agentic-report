import httpx
from audit.models import PageFetchResult


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


async def fetch_url(url: str, timeout: int = 20) -> PageFetchResult:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=DEFAULT_HEADERS,
        ) as client:
            response = await client.get(url)

            redirect_chain = [str(r.url) for r in response.history]
            content_type = response.headers.get("content-type", "")

            html = None
            if "text/html" in content_type.lower():
                html = response.text

            return PageFetchResult(
                url=url,
                final_url=str(response.url),
                status_code=response.status_code,
                redirect_chain=redirect_chain,
                html=html,
                content_type=content_type,
                response_length=len(response.content or b""),
                server=response.headers.get("server"),
                x_robots_tag=response.headers.get("x-robots-tag"),
            )

    except Exception as e:
        return PageFetchResult(
            url=url,
            final_url=url,
            status_code=None,
            error=str(e),
        )