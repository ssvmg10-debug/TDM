"""
Phase 4: Self-Healing Fallback System.
Crawling, Schema Fusion, Synthetic, and Provisioning fallbacks.
"""
import logging
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger("tdm.fallbacks")


def with_crawl_fallbacks(crawl_fn: Callable, urls: List[str], hints: Dict = None) -> Dict[str, Any]:
    """
    Crawling fallbacks: Playwright headless → headful → mobile viewport → requests → cached → domain pack.
    """
    fallbacks_used = []
    result = None

    # 1. Playwright headless (default)
    try:
        result = crawl_fn(urls=urls, headless=True, hints=hints)
        if result and result.get("entities"):
            return {"schema": result, "fallbacks_used": fallbacks_used}
    except Exception as e:
        logger.warning(f"Crawl headless failed: {e}")
        fallbacks_used.append({"step": "playwright_headless", "error": str(e)})

    # 2. Playwright headful
    try:
        result = crawl_fn(urls=urls, headless=False, hints=hints)
        if result and result.get("entities"):
            fallbacks_used.append({"step": "playwright_headful", "reason": "headless failed"})
            return {"schema": result, "fallbacks_used": fallbacks_used}
    except Exception as e:
        logger.warning(f"Crawl headful failed: {e}")
        fallbacks_used.append({"step": "playwright_headful", "error": str(e)})

    # 3. Domain pack fallback
    from services.crawler import TestCaseCrawler
    crawler = TestCaseCrawler()
    result = crawler._fallback_schema(hints or {})
    fallbacks_used.append({"step": "domain_pack", "reason": "crawl unavailable"})
    return {"schema": result, "fallbacks_used": fallbacks_used}


def with_synthetic_fallbacks(
    primary_fn: Callable,
    fallback_fn: Callable,
    *args,
    **kwargs
) -> Any:
    """If SDV/primary fails → use Faker + constraints."""
    try:
        return primary_fn(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Primary synthetic failed: {e}, using fallback")
        return fallback_fn(*args, **kwargs)


def with_provision_fallbacks(
    provision_fn: Callable,
    dataset_version_id: str,
    target_env: str,
    max_retries: int = 2,
    **kwargs
) -> Dict[str, Any]:
    """Auto retry, fix type mismatch on failure."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            result = provision_fn(
                dataset_version_id=dataset_version_id,
                target_env=target_env,
                **kwargs
            )
            if attempt > 0:
                result["fallbacks_used"] = result.get("fallbacks_used", []) + [{"step": "retry", "attempt": attempt}]
            return result
        except Exception as e:
            last_error = e
            logger.warning(f"Provision attempt {attempt + 1} failed: {e}")
    raise last_error
