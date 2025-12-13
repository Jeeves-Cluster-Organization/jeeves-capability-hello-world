#!/usr/bin/env python3
"""Worker entry point for distributed mode.

Starts a distributed worker process that pulls tasks from Redis queues
and executes them using the WorkerCoordinator.

Usage:
    # Start a worker for all agent queues
    python run_worker.py

    # Start a worker for specific queues
    python run_worker.py --queues "agent:planner,agent:validator"

    # With custom worker ID
    python run_worker.py --worker-id "gpu-node-1"

Environment Variables:
    FEATURE_ENABLE_DISTRIBUTED_MODE=true  # Required
    FEATURE_USE_REDIS_STATE=true          # Required
    REDIS_URL=redis://localhost:6379      # Redis connection URL

Constitutional Reference: Amendment XXIV (Horizontal Scaling Support)
"""

import argparse
import asyncio
import os
import signal
import sys
import uuid
from typing import List, Optional

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Add jeeves-core submodule to Python path for core packages
jeeves_core_path = os.path.join(project_root, "jeeves-core")
if os.path.exists(jeeves_core_path):
    sys.path.insert(0, jeeves_core_path)


async def create_redis_client():
    """Create Redis client from environment configuration."""
    try:
        import redis.asyncio as redis
    except ImportError:
        raise ImportError(
            "redis package not installed. Install with: pip install redis"
        )

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url, decode_responses=True)


async def run_worker(
    worker_id: str,
    queues: List[str],
    max_concurrent_tasks: int = 5,
    heartbeat_interval: int = 30,
) -> None:
    """Run a distributed worker.

    Args:
        worker_id: Unique identifier for this worker
        queues: List of queue patterns to process (e.g., ["agent:*"])
        max_concurrent_tasks: Max tasks to process concurrently
        heartbeat_interval: Seconds between heartbeats
    """
    from jeeves_mission_system.bootstrap import create_app_context
    from jeeves_avionics.distributed import RedisDistributedBus
    from jeeves_mission_system.services.worker_coordinator import (
        WorkerCoordinator,
        WorkerConfig,
    )
    from jeeves_avionics.logging import create_logger

    logger = create_logger("worker")

    # Create app context
    logger.info("creating_app_context")
    app_context = create_app_context()

    # Verify feature flags
    if not app_context.feature_flags.enable_distributed_mode:
        logger.error(
            "distributed_mode_disabled",
            message="Set FEATURE_ENABLE_DISTRIBUTED_MODE=true to enable distributed workers",
        )
        sys.exit(1)

    if not app_context.feature_flags.use_redis_state:
        logger.error(
            "redis_state_disabled",
            message="Set FEATURE_USE_REDIS_STATE=true to enable Redis distributed bus",
        )
        sys.exit(1)

    # Create Redis client and distributed bus
    logger.info("connecting_to_redis", redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))
    try:
        redis_client = await create_redis_client()
        distributed_bus = RedisDistributedBus(redis_client)
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        sys.exit(1)

    # Create worker coordinator
    coordinator = WorkerCoordinator(
        distributed_bus=distributed_bus,
        checkpoint_adapter=None,  # Optional: Add checkpoint adapter for persistence
        runtime=None,  # Workers typically get their own runtime from task context
        logger=logger,
        control_tower=app_context.control_tower,
    )

    # Configure worker
    config = WorkerConfig(
        worker_id=worker_id,
        queues=queues,
        max_concurrent_tasks=max_concurrent_tasks,
        heartbeat_interval_seconds=heartbeat_interval,
    )

    # Set up graceful shutdown
    shutdown_event = asyncio.Event()

    def handle_signal(sig):
        logger.info("shutdown_signal_received", signal=sig)
        shutdown_event.set()

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))

    logger.info(
        "worker_starting",
        worker_id=worker_id,
        queues=queues,
        max_concurrent_tasks=max_concurrent_tasks,
    )

    # Run worker with graceful shutdown
    worker_task = asyncio.create_task(coordinator.run_worker(config))

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Stop worker gracefully
    logger.info("stopping_worker", worker_id=worker_id)
    await coordinator.stop_worker(worker_id)

    # Wait for worker task to complete (with timeout)
    try:
        await asyncio.wait_for(worker_task, timeout=30)
    except asyncio.TimeoutError:
        logger.warning("worker_shutdown_timeout", worker_id=worker_id)
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    # Close Redis connection
    await redis_client.close()

    logger.info("worker_stopped", worker_id=worker_id)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a distributed worker for Jeeves pipeline execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Start a worker for all agent queues
    python run_worker.py

    # Start a worker for specific queues
    python run_worker.py --queues "agent:planner,agent:validator"

    # With custom worker ID and concurrency
    python run_worker.py --worker-id "gpu-node-1" --concurrency 10

Environment Variables:
    FEATURE_ENABLE_DISTRIBUTED_MODE=true
    FEATURE_USE_REDIS_STATE=true
    REDIS_URL=redis://localhost:6379
        """,
    )

    parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="Unique worker identifier (default: auto-generated)",
    )

    parser.add_argument(
        "--queues",
        type=str,
        default="agent:*",
        help="Comma-separated list of queue patterns (default: 'agent:*')",
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent tasks to process (default: 5)",
    )

    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=30,
        help="Seconds between heartbeats (default: 30)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Generate worker ID if not provided
    worker_id = args.worker_id or f"worker-{uuid.uuid4().hex[:8]}"

    # Parse queues
    queues = [q.strip() for q in args.queues.split(",")]

    # Run worker
    asyncio.run(
        run_worker(
            worker_id=worker_id,
            queues=queues,
            max_concurrent_tasks=args.concurrency,
            heartbeat_interval=args.heartbeat_interval,
        )
    )


if __name__ == "__main__":
    main()
