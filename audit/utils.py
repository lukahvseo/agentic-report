from urllib.parse import urlparse, urlunparse, urldefrag


def normalize_url(url: str) -> str:
    """
    Normalize URLs for crawl deduplication without changing meaningful path structure.

    Important:
    - Keeps trailing slash because some sites canonicalize with trailing slashes.
    - Removes fragments.
    - Lowercases scheme and host.
    """
    url, _fragment = urldefrag(url)
    parsed = urlparse(url)

    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()

    path = parsed.path or "/"

    normalized = urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            parsed.query,
            "",
        )
    )

    return normalized

def ensure_url_scheme(url: str) -> str:
    clean = url.strip()

    if clean.startswith("http://") or clean.startswith("https://"):
        return clean

    return f"https://{clean}"

def get_origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def same_domain(url_a: str, url_b: str) -> bool:
    a = urlparse(url_a).netloc.lower().replace("www.", "")
    b = urlparse(url_b).netloc.lower().replace("www.", "")
    return a == b


def looks_like_html_page(url: str) -> bool:
    """
    Skip obvious files/assets.
    """
    path = urlparse(url).path.lower()

    blocked_extensions = (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        ".pdf", ".zip", ".rar", ".7z",
        ".css", ".js", ".json", ".xml",
        ".mp4", ".mov", ".avi",
        ".woff", ".woff2", ".ttf", ".eot",
    )

    return not path.endswith(blocked_extensions)