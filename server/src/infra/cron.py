import asyncio
import logging
import random

from src.infra.embedding_cache import get_memory_embedding_cache
from src.infra.retrieval_cache import get_memory_json_cache
from src.infra.chroma import cleanup_stale_semantic_collections

logger = logging.getLogger(__name__)

# TTL configurations
EMBEDDING_CACHE_TTL = 3600  # 1 hour
RETRIEVAL_CACHE_TTL = 3600  # 1 hour
SEMANTIC_CACHE_TTL = 86400  # 24 hours

# Loop intervals
MEMORY_CACHE_INTERVAL = 600  # 10 minutes
SEMANTIC_CACHE_INTERVAL = 3600  # 1 hour

_tasks = []


async def _embedding_memory_cron():
    while True:
        try:
            await asyncio.sleep(MEMORY_CACHE_INTERVAL * random.uniform(0.9, 1.1))
            cache = get_memory_embedding_cache()
            count = cache.cleanup_stale(EMBEDDING_CACHE_TTL)
            if count > 0:
                logger.info("cron_embedding_cache_cleanup evicted=%d", count)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("cron_embedding_cache_cleanup_error error=%s", exc)


async def _retrieval_memory_cron():
    while True:
        try:
            await asyncio.sleep(MEMORY_CACHE_INTERVAL * random.uniform(0.9, 1.1))
            cache = get_memory_json_cache()
            count = cache.cleanup_stale(RETRIEVAL_CACHE_TTL)
            if count > 0:
                logger.info("cron_retrieval_cache_cleanup evicted=%d", count)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("cron_retrieval_cache_cleanup_error error=%s", exc)


async def _chroma_semantic_cron():
    while True:
        try:
            await asyncio.sleep(SEMANTIC_CACHE_INTERVAL * random.uniform(0.9, 1.1))
            count = await asyncio.to_thread(cleanup_stale_semantic_collections, SEMANTIC_CACHE_TTL)
            if count > 0:
                logger.info("cron_semantic_cache_cleanup evicted=%d", count)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("cron_semantic_cache_cleanup_error error=%s", exc)


def start_cache_crons():
    """Start background cache cleanup workers."""
    if _tasks:
        return
    logger.info("starting background cache crons")
    loop = asyncio.get_running_loop()
    _tasks.append(loop.create_task(_embedding_memory_cron()))
    _tasks.append(loop.create_task(_retrieval_memory_cron()))
    _tasks.append(loop.create_task(_chroma_semantic_cron()))


async def stop_cache_crons():
    """Stop background cache cleanup workers."""
    if not _tasks:
        return
    logger.info("stopping background cache crons")
    for task in _tasks:
        task.cancel()
    await asyncio.gather(*_tasks, return_exceptions=True)
    _tasks.clear()
