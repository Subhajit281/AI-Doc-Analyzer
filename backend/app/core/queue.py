import asyncio
import os
import uuid
from typing import Callable, Any, Awaitable
from app.core.memory import optimize_memory


# Free tier has 512MB RAM and limited vCPU, so serialize heavy ingestion tasks
MAX_CONCURRENT_INGESTIONS = int(os.getenv("MAX_CONCURRENT_INGESTIONS", "1"))


class IngestionQueue:
    """
    Asynchronous concurrency limiter and queue for memory-intensive document
    processing tasks. Ensures that uploads and parsing jobs execute sequentially
    or within strict concurrency bounds, preventing burst memory spikes on
    free-tier platforms.
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_INGESTIONS):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks = 0
        self.waiting_tasks = 0

    async def execute(
        self,
        task_fn: Callable[[], Awaitable[Any]],
        task_name: str = "document_task",
    ) -> Any:
        task_id = str(uuid.uuid4())[:8]
        self.waiting_tasks += 1

        print(
            f"[QUEUE] Task {task_name} ({task_id}) queued. "
            f"Waiting: {self.waiting_tasks}, Active: {self.active_tasks}"
        )

        async with self.semaphore:
            self.waiting_tasks -= 1
            self.active_tasks += 1
            print(
                f"[QUEUE] Task {task_name} ({task_id}) started execution. "
                f"Active: {self.active_tasks}"
            )
            try:
                result = await task_fn()
                return result
            finally:
                self.active_tasks -= 1
                print(
                    f"[QUEUE] Task {task_name} ({task_id}) finished. "
                    f"Active: {self.active_tasks}, Waiting: {self.waiting_tasks}"
                )
                # Free memory immediately after task finishes
                optimize_memory(tag=f"QueueTask-{task_id}")


# Global queue singleton
ingestion_queue = IngestionQueue()

