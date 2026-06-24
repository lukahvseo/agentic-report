from typing import Any

from audit.models import AuditFinding, Evidence, PageSignals


PRODUCT_IDENTIFIER_FIELDS = {
    "sku",
    "gtin",
    "gtin8",
    "gtin12",
    "gtin13",
    "gtin14",
    "mpn",
}


def flatten_schema_items(schema_data: dict) -> list[dict]:
    items = []

    def walk(value: Any):
        if isinstance(value, dict):
            items.append(value)

            for child_value in value.values():
                walk(child_value)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    for syntax_items in schema_data.values():
        walk(syntax_items)

    return items


def get_schema_type(item: dict) -> list[str]:
    item_type = item.get("@type") or item.get("type")

    if not item_type:
        return []

    if isinstance(item_type, list):
        return [str(t) for t in item_type]

    return [str(item_type)]


def find_items_by_type(schema_data: dict, schema_type: str) -> list[dict]:
    all_items = flatten_schema_items(schema_data)

    return [
        item for item in all_items
        if schema_type in get_schema_type(item)
    ]


def has_any_field(item: dict, fields: set[str]) -> bool:
    return any(field in item and item.get(field) not in [None, "", []] for field in fields)


def get_offers(product_item: dict) -> list[dict]:
    offers = product_item.get("offers")

    if not offers:
        return []

    if isinstance(offers, dict):
        return [offers]

    if isinstance(offers, list):
        return [offer for offer in offers if isinstance(offer, dict)]

    return []


def offer_has_field(offers: list[dict], field: str) -> bool:
    return any(
        field in offer and offer.get(field) not in [None, "", []]
        for offer in offers
    )


def product_has_nested_field(product_item: dict, field: str) -> bool:
    if field in product_item and product_item.get(field) not in [None, "", []]:
        return True

    offers = get_offers(product_item)

    return offer_has_field(offers, field)


def analyze_product_schema_completeness(pages: list[PageSignals]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    product_pages = [
        page for page in pages
        if page.status_code == 200 and page.page_type == "product"
    ]

    product_pages_missing_schema = []
    product_pages_with_incomplete_schema = []
    product_pages_with_good_schema = []

    for page in product_pages:
        product_items = find_items_by_type(page.schema_data, "Product")

        if not product_items:
            product_pages_missing_schema.append(page)
            continue

        product = product_items[0]
        offers = get_offers(product)

        missing_fields = []

        if not product.get("name"):
            missing_fields.append("name")

        if not product.get("image"):
            missing_fields.append("image")

        if not product.get("description"):
            missing_fields.append("description")

        if not offers:
            missing_fields.append("offers")

        if offers and not offer_has_field(offers, "price"):
            missing_fields.append("offers.price")

        if offers and not offer_has_field(offers, "priceCurrency"):
            missing_fields.append("offers.priceCurrency")

        if offers and not offer_has_field(offers, "availability"):
            missing_fields.append("offers.availability")

        if not product.get("brand"):
            missing_fields.append("brand")

        if not has_any_field(product, PRODUCT_IDENTIFIER_FIELDS):
            missing_fields.append("sku / gtin / mpn")

        if not product.get("aggregateRating"):
            missing_fields.append("aggregateRating")

        if not product.get("review"):
            missing_fields.append("review")

        if not product_has_nested_field(product, "shippingDetails"):
            missing_fields.append("shippingDetails")

        if not product_has_nested_field(product, "hasMerchantReturnPolicy"):
            missing_fields.append("hasMerchantReturnPolicy")

        if missing_fields:
            product_pages_with_incomplete_schema.append((page, missing_fields))
        else:
            product_pages_with_good_schema.append(page)

    if product_pages_missing_schema:
        findings.append(
            AuditFinding(
                check_id="product_schema_missing",
                category="Ecommerce Schema",
                title="Product pages are missing Product schema",
                status="fail",
                severity="high",
                confidence="high",
                affected_urls_count=len(product_pages_missing_schema),
                evidence=[
                    Evidence(
                        url=page.final_url,
                        signal="Product page without Product schema",
                        details=f"Detected schema: {', '.join(page.schema_types) or 'none'}",
                    )
                    for page in product_pages_missing_schema[:10]
                ],
                recommendation="Add Product structured data to product pages, including Offer, price, currency, availability, brand, image, and product identifiers where available.",
                business_impact="Product schema helps search engines understand product details and can support product-rich search experiences.",
                priority_score=8.5,
            )
        )

    if product_pages_with_incomplete_schema:
        findings.append(
            AuditFinding(
                check_id="product_schema_incomplete",
                category="Ecommerce Schema",
                title="Product schema is missing recommended ecommerce fields",
                status="warning",
                severity="medium",
                confidence="high",
                affected_urls_count=len(product_pages_with_incomplete_schema),
                evidence=[
                    Evidence(
                        url=page.final_url,
                        signal="Incomplete Product schema",
                        details="Missing: " + ", ".join(missing_fields),
                    )
                    for page, missing_fields in product_pages_with_incomplete_schema[:10]
                ],
                recommendation="Improve Product schema completeness by adding missing product, offer, review, shipping, and return policy fields where they are visible and accurate on the page.",
                business_impact="More complete Product schema improves product understanding and can support richer ecommerce eligibility signals.",
                priority_score=6.5,
            )
        )

    if product_pages_with_good_schema:
        findings.append(
            AuditFinding(
                check_id="product_schema_complete",
                category="Ecommerce Schema",
                title="Product schema includes key ecommerce fields",
                status="pass",
                severity="low",
                confidence="high",
                affected_urls_count=len(product_pages_with_good_schema),
                evidence=[
                    Evidence(
                        url=page.final_url,
                        signal="Product schema detected with key fields",
                    )
                    for page in product_pages_with_good_schema[:10]
                ],
                recommendation="No immediate action required. Continue validating that structured data matches visible page content.",
                business_impact="Complete Product schema helps search engines understand product details clearly.",
                priority_score=1.0,
            )
        )

    return findings