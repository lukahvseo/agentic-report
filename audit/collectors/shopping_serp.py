from urllib.parse import urlparse

import requests


def normalize_domain(value: str) -> str:
    value = value.strip().lower()

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        value = parsed.netloc

    value = value.replace("www.", "")

    return value.rstrip("/")


def result_matches_domain(result: dict, target_domain: str) -> bool:
    target_domain = normalize_domain(target_domain)

    link = result.get("link") or result.get("product_link") or result.get("serpapi_product_api") or ""
    source = result.get("source") or result.get("merchant") or result.get("seller") or ""

    if link:
        parsed = urlparse(link)
        result_domain = parsed.netloc.lower().replace("www.", "")

        if result_domain == target_domain or result_domain.endswith("." + target_domain):
            return True

    if source:
        source_normalized = source.lower().replace("www.", "")
        if target_domain in source_normalized:
            return True

    return False


def result_matches_merchant(result: dict, merchant_name: str) -> bool:
    if not merchant_name:
        return False

    merchant_name = merchant_name.strip().lower()

    possible_fields = [
        result.get("source"),
        result.get("merchant"),
        result.get("seller"),
        result.get("store"),
    ]

    for field in possible_fields:
        if field and merchant_name in str(field).lower():
            return True

    return False


def extract_price(result: dict) -> str | None:
    for key in ["price", "extracted_price"]:
        value = result.get(key)
        if value not in [None, "", []]:
            return str(value)

    return None


def extract_old_price(result: dict) -> str | None:
    for key in ["old_price", "extracted_old_price"]:
        value = result.get(key)
        if value not in [None, "", []]:
            return str(value)

    return None


def extract_rating(result: dict) -> str | None:
    value = result.get("rating")

    if value not in [None, "", []]:
        return str(value)

    return None


def extract_reviews(result: dict) -> str | None:
    for key in ["reviews", "review_count"]:
        value = result.get(key)
        if value not in [None, "", []]:
            return str(value)

    return None


def run_google_shopping_query(
    query: str,
    api_key: str,
    location: str = "",
    gl: str = "us",
    hl: str = "en",
    google_domain: str = "google.com",
) -> dict:
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "gl": gl,
        "hl": hl,
        "google_domain": google_domain,
    }

    if location:
        params["location"] = location

    response = requests.get(
        "https://serpapi.com/search.json",
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def get_shopping_results(serp_response: dict) -> list[dict]:
    shopping_results = serp_response.get("shopping_results")

    if isinstance(shopping_results, list):
        return shopping_results

    inline_results = serp_response.get("inline_shopping_results")

    if isinstance(inline_results, list):
        return inline_results

    return []


def check_visibility_for_keywords(
    domain: str,
    api_key: str,
    merchant_name: str,
    keywords: list[str],
    location: str = "",
    gl: str = "us",
    hl: str = "en",
    google_domain: str = "google.com",
) -> dict:
    rows = []

    total_keywords = len(keywords)
    found_count = 0
    price_count = 0
    review_count = 0

    for keyword in keywords:
        serp_response = run_google_shopping_query(
            query=keyword,
            api_key=api_key,
            location=location,
            gl=gl,
            hl=hl,
            google_domain=google_domain,
        )

        shopping_results = get_shopping_results(serp_response)

        matched_result = None
        matched_position = None
        match_reason = None

        for index, result in enumerate(shopping_results, start=1):
            if result_matches_domain(result, domain):
                matched_result = result
                matched_position = index
                match_reason = "domain"
                break

            if merchant_name and result_matches_merchant(result, merchant_name):
                matched_result = result
                matched_position = index
                match_reason = "merchant_name"
                break

        if matched_result:
            found_count += 1

            price = extract_price(matched_result)
            old_price = extract_old_price(matched_result)
            rating = extract_rating(matched_result)
            reviews = extract_reviews(matched_result)

            has_price = bool(price)
            has_reviews = bool(reviews)

            if has_price:
                price_count += 1

            if has_reviews:
                review_count += 1

            rows.append(
                {
                    "query": keyword,
                    "found_on_shopping_tab": True,
                    "position": matched_position,
                    "match_reason": match_reason,
                    "matched_title": matched_result.get("title"),
                    "matched_link": matched_result.get("link") or matched_result.get("product_link"),
                    "merchant": matched_result.get("source")
                    or matched_result.get("merchant")
                    or matched_result.get("seller"),
                    "price": price,
                    "old_price": old_price,
                    "rating": rating,
                    "reviews": reviews,
                    "has_price": has_price,
                    "has_reviews": has_reviews,
                    "results_checked": len(shopping_results),
                }
            )

        else:
            rows.append(
                {
                    "query": keyword,
                    "found_on_shopping_tab": False,
                    "position": None,
                    "match_reason": None,
                    "matched_title": None,
                    "matched_link": None,
                    "merchant": None,
                    "price": None,
                    "old_price": None,
                    "rating": None,
                    "reviews": None,
                    "has_price": False,
                    "has_reviews": False,
                    "results_checked": len(shopping_results),
                }
            )

    shopping_tab_score = round((found_count / total_keywords) * 100, 1) if total_keywords else 0
    price_coverage_score = round((price_count / found_count) * 100, 1) if found_count else 0
    review_coverage_score = round((review_count / found_count) * 100, 1) if found_count else 0

    return {
        "shopping_tab_score": shopping_tab_score,
        "price_coverage_score": price_coverage_score,
        "review_coverage_score": review_coverage_score,
        "shopping_tab_rows": rows,
    }