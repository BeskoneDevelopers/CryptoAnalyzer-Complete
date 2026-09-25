from prometheus_client import Counter

crypto_cache_total = Counter("crypto_cache_total", "Cache lookups", labelnames=["key_prefix", "result"])
