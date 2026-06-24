import extruct
from w3lib.html import get_base_url


def extract_schema_data(html: str, url: str) -> dict:
    if not html:
        return {}

    try:
        base_url = get_base_url(html, url)

        return extruct.extract(
            html,
            base_url=base_url,
            syntaxes=["json-ld", "microdata", "rdfa"],
            uniform=True,
        )

    except Exception:
        return {}


def normalize_schema_type(schema_type) -> list[str]:
    if not schema_type:
        return []

    if isinstance(schema_type, list):
        normalized = []
        for item in schema_type:
            normalized.extend(normalize_schema_type(item))
        return normalized

    schema_type = str(schema_type).strip()

    if not schema_type:
        return []

    if schema_type.startswith("http://schema.org/"):
        schema_type = schema_type.replace("http://schema.org/", "")

    if schema_type.startswith("https://schema.org/"):
        schema_type = schema_type.replace("https://schema.org/", "")

    return [schema_type]


def collect_schema_types_from_item(item) -> list[str]:
    schema_types = []

    if isinstance(item, list):
        for child in item:
            schema_types.extend(collect_schema_types_from_item(child))

        return schema_types

    if not isinstance(item, dict):
        return schema_types

    direct_type = (
        item.get("@type")
        or item.get("type")
        or item.get("rdf:type")
    )

    schema_types.extend(normalize_schema_type(direct_type))

    nested_keys = [
        "@graph",
        "graph",
        "mainEntity",
        "mainEntityOfPage",
        "itemListElement",
        "item",
        "offers",
        "brand",
        "manufacturer",
        "aggregateRating",
        "review",
        "breadcrumb",
        "about",
        "isPartOf",
        "hasPart",
        "publisher",
        "author",
        "image",
        "potentialAction",
        "acceptedAnswer",
    ]

    for key in nested_keys:
        if key in item:
            schema_types.extend(collect_schema_types_from_item(item.get(key)))

    for value in item.values():
        if isinstance(value, (dict, list)):
            schema_types.extend(collect_schema_types_from_item(value))

    return schema_types


def extract_schema_types(html: str, url: str) -> list[str]:
    data = extract_schema_data(html, url)

    schema_types = []

    for syntax_items in data.values():
        if isinstance(syntax_items, list):
            for item in syntax_items:
                schema_types.extend(collect_schema_types_from_item(item))

        elif isinstance(syntax_items, dict):
            schema_types.extend(collect_schema_types_from_item(syntax_items))

    cleaned_types = []

    for schema_type in schema_types:
        if not schema_type:
            continue

        schema_type = str(schema_type).strip()

        if not schema_type:
            continue

        cleaned_types.append(schema_type)

    return sorted(set(cleaned_types))