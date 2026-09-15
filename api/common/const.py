USER_LOGIN_CACHE_KEY = "user_login_cache:{user_id}"
USER_HAS_LOGIN_CACHE_KEY = "user_has_login_cache:{user_id}"

EMBED_ERROR_CACHE = "embed_worker_error:{batch_id}"
EXTRACT_ERROR_CACHE = "extract_worker_error:{batch_id}"

# 重试计数 key：跨 worker/rebalance/重启持久化瞬时错误的重试次数
EXTRACT_RETRY_CACHE = "extract_worker_retry:{batch_id}"
EMBED_RETRY_CACHE = "embed_worker_retry:{batch_id}"
