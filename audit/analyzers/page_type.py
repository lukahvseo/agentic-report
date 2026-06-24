from urllib.parse import urlparse

from audit.models import PageSignals


def classify_page_type(page: PageSignals) -> str:
    path = urlparse(page.final_url).path.lower()
    schema_types = set(page.schema_types)

    collection_path_markers = [
        "/collections/",
        "/collection/",
        "/category/",
        "/categories/",
        "/shop/",
        "/product-category/",
        "/collections",
        "/category",
        "/shop",
    ]

    product_path_markers = [
        "/products/",
        "/product/",
        "/p/",
        "/products",
        "/product",
    ]

    article_path_markers = [
        "/blog/",
        "/blogs/",
        "/article/",
        "/news/",
        "/blog",
        "/blogs",
        "/article",
        "/news",
    ]

    policy_path_markers = [
        "/shipping",
        "/returns",
        "/refund",
        "/privacy",
        "/terms",
        "/contact",
        "/about",
        "/policy",
        "/policies",
    ]

    if path in ["", "/"]:
        return "homepage"

    if any(marker in path for marker in policy_path_markers):
        return "policy"

    # Important:
    # Collection/category URL patterns must be checked before Product schema.
    # Many ecommerce collection pages include Product schema for listed products.
    if any(marker in path for marker in collection_path_markers):
        return "collection"

    if any(marker in path for marker in product_path_markers):
        return "product"

    if any(marker in path for marker in article_path_markers):
        return "article"

    if "CollectionPage" in schema_types:
        return "collection"

    if "Product" in schema_types:
        return "product"

    if "Article" in schema_types or "BlogPosting" in schema_types:
        return "article"

    return "unknown"


def apply_page_types(pages: list[PageSignals]) -> list[PageSignals]:
    for page in pages:
        page.page_type = classify_page_type(page)

    return pages