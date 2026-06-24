import asyncio
import sys
from audit.runner import run_audit


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 25

    result = await run_audit(url, max_pages=max_pages)

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())