import asyncio
import logging

from redis.asyncio import Redis

from app.core.config import get_settings
from app.services.pipeline_runner import AtlasPipelineRunner
from app.services.redis_job_manager import RedisPipelineJobs

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is required to run the pipeline worker")

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    jobs = RedisPipelineJobs(
        redis,
        queue_name=settings.pipeline_queue_name,
        ttl_seconds=settings.pipeline_job_ttl_seconds,
    )
    runner = AtlasPipelineRunner(settings)
    recovered = await jobs.requeue_interrupted()
    logger.info("pipeline worker ready", extra={"recovered_jobs": recovered})
    try:
        while True:
            await jobs.run_next(runner)
    finally:
        await jobs.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
