import requests
from urllib.parse import urlparse

SERPAPI_ENDPOINT = "https://serpapi.com/search"
LOCATIONS_ENDPOINT = "https://serpapi.com/locations.json"


def normalize_domain_for_match(domain):
    domain = (domain or "").strip().lower()
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.split("/")[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def normalize_text(value):
    return (value or "").strip().lower()


def host_from_url(value):
    if not value or not isinstance(value, str):
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    return ""


def result_matches_target(result, target_domain, merchant_name):
    merchant_name = normalize_text(merchant_name)

    fields_to_check = {
        "source": normalize_text(result.get("source", "")),
        "title": normalize_text(result.get("title", "")),
        "link": normalize_text(result.get("link", "")),
        "product_link": normalize_text(result.get("product_link", "")),
        "snippet": normalize_text(result.get("snippet", "")),
    }

    link_host = host_from_url(result.get("link", ""))
    product_link_host = host_from_url(result.get("product_link", ""))

    if target_domain and link_host and target_domain in link_host:
        return True, "matched link domain"

    if target_domain and product_link_host and target_domain in product_link_host:
        return True, "matched product_link domain"

    if target_domain:
        for field_name, field_value in fields_to_check.items():
            if target_domain in field_value:
                return True, "matched domain in " + field_name

    if merchant_name:
        for field_name, field_value in fields_to_check.items():
            if merchant_name in field_value:
                return True, "matched merchant name in " + field_name

    return False, ""


def get_serpapi_locations(api_key, query, limit=10):
    params = {
        "q": query,
        "limit": limit,
        "api_key": api_key,
    }
    resp = requests.get(LOCATIONS_ENDPOINT, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def run_google_shopping_query(
    api_key,
    query,
    location="",
    gl="us",
    hl="en",
    google_domain="google.com",
    num=30,
):
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "gl": gl.lower(),
        "hl": hl.lower(),
        "google_domain": google_domain,
        "num": num,
    }

    if location.strip():
        params["location"] = location.strip()

    resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def evaluate_shopping_results(results, target_domain, merchant_name):
    found = False
    found_position = None
    found_title = ""
    found_link = ""
    match_reason = ""
    price = ""
    old_price = ""
    rating = None
    reviews = None
    has_price = False
    has_rating = False
    has_reviews = False

    for idx, result in enumerate(results, start=1):
        matched, reason = result_matches_target(result, target_domain, merchant_name)
        if matched:
            found = True
            found_position = result.get("position", idx)
            found_title = result.get("title", "")
            found_link = result.get("link") or result.get("product_link") or ""
            match_reason = reason

            price = result.get("price", "")
            old_price = result.get("old_price", "")
            rating = result.get("rating")
            reviews = result.get("reviews")

            has_price = bool(price or result.get("extracted_price"))
            has_rating = rating is not None
            has_reviews = reviews is not None and reviews != ""
            break

    return {
        "found": found,
        "position": found_position,
        "matched_title": found_title,
        "matched_link": found_link,
        "match_reason": match_reason,
        "price": price,
        "old_price": old_price,
        "rating": rating,
        "reviews": reviews,
        "has_price": has_price,
        "has_rating": has_rating,
        "has_reviews": has_reviews,
        "results_checked": len(results),
    }


def check_visibility_for_keywords(
    domain,
    api_key,
    merchant_name,
    keywords,
    location="",
    gl="us",
    hl="en",
    google_domain="google.com",
):
    target_domain = normalize_domain_for_match(domain)
    rows = []

    for keyword in keywords:
        query = keyword.strip()

        try:
            shopping_data = run_google_shopping_query(
                api_key=api_key,
                query=query,
                location=location,
                gl=gl,
                hl=hl,
                google_domain=google_domain,
            )

            shopping_results = shopping_data.get("shopping_results", [])
            evaluated = evaluate_shopping_results(
                shopping_results,
                target_domain,
                merchant_name
            )

            rows.append({
                "query": query,
                "found_on_shopping_tab": evaluated["found"],
                "position": evaluated["position"],
                "matched_title": evaluated["matched_title"],
                "matched_link": evaluated["matched_link"],
                "match_reason": evaluated["match_reason"],
                "price": evaluated["price"],
                "old_price": evaluated["old_price"],
                "rating": evaluated["rating"],
                "reviews": evaluated["reviews"],
                "has_price": evaluated["has_price"],
                "has_rating": evaluated["has_rating"],
                "has_reviews": evaluated["has_reviews"],
                "results_checked": evaluated["results_checked"],
            })

        except Exception as e:
            rows.append({
                "query": query,
                "found_on_shopping_tab": False,
                "position": None,
                "matched_title": "",
                "matched_link": "",
                "match_reason": "",
                "price": "",
                "old_price": "",
                "rating": None,
                "reviews": None,
                "has_price": False,
                "has_rating": False,
                "has_reviews": False,
                "results_checked": 0,
                "error": str(e),
            })

    found_count = sum(1 for row in rows if row.get("found_on_shopping_tab"))
    price_count = sum(1 for row in rows if row.get("has_price"))
    review_count = sum(1 for row in rows if row.get("has_reviews"))
    total = len(keywords)

    visibility_score = round((found_count / total) * 100) if total else 0
    price_score = round((price_count / total) * 100) if total else 0
    review_score = round((review_count / total) * 100) if total else 0

    return {
        "shopping_tab_score": visibility_score,
        "price_score": price_score,
        "review_score": review_score,
        "shopping_tab_rows": rows,
    }