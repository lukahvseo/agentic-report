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


def extract_schema_types(html: str, url: str) -> list[str]:
    data = extract_schema_data(html, url)

    schema_types = []

    for syntax_items in data.values():
        if not isinstance(syntax_items, list):
            continue

        for item in syntax_items:
            item_type = item.get("@type") or item.get("type")

            if isinstance(item_type, list):
                schema_types.extend([str(t) for t in item_type])
            elif item_type:
                schema_types.append(str(item_type))

    return sorted(set(schema_types))