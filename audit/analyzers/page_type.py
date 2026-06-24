from urllib.parse import urlparse
from audit.models import PageSignals


def classify_page_type(page: PageSignals) -> str:
    url = page.final_url.lower()
    path = urlparse(page.final_url).path.lower()

    schema_types = set(page.schema_types)

    if "Product" in schema_types:
        return "product"

    if "CollectionPage" in schema_types:
        return "collection"

    if "Article" in schema_types or "BlogPosting" in schema_types:
        return "article"

    if any(marker in path for marker in ["/products/", "/product/", "/p/"]):
        return "product"

    if any(marker in path for marker in ["/collections/", "/collection/", "/category/", "/categories/", "/shop/"]):
        return "collection"

    if any(marker in path for marker in ["/blog/", "/blogs/", "/article/", "/news/"]):
        return "article"

    if any(marker in path for marker in ["/shipping", "/returns", "/refund", "/privacy", "/terms", "/contact", "/about"]):
        return "policy"

    if path in ["", "/"]:
        return "homepage"

    return "unknown"


def apply_page_types(pages: list[PageSignals]) -> list[PageSignals]:
    for page in pages:
        page.page_type = classify_page_type(page)

    return pages