"""In-process single-worker job queue.

Reconstruction is heavy (CPU, ~2-3 GB RAM). One background worker processes a
FIFO queue so concurrent uploads queue instead of running in parallel and
exhausting RAM. State lives in memory; this is a single-user local tool.
"""

from __future__ import annotations

import logging
import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Optional

from image_to_3d.api.schemas import JobState
from image_to_3d.core import ReconstructionOptions, reconstruct
from image_to_3d.core.errors import ReconstructionError

logger = logging.getLogger(__name__)


@dataclass
class Job:
    job_id: str
    image_bytes: bytes
    options: ReconstructionOptions
    state: JobState = JobState.QUEUED
    error: Optional[str] = None
    result: object = None  # core.ReconstructionResult once DONE
    _done: threading.Event = field(default_factory=threading.Event)

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until the job finishes. Used by tests."""
        return self._done.wait(timeout)


class JobQueue:
    """FIFO queue with one worker thread."""

    def __init__(self) -> None:
        self._queue: "queue.Queue[Job]" = queue.Queue()
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._worker = threading.Thread(
            target=self._run, name="reconstruct-worker", daemon=True
        )
        self._worker.start()

    def submit(self, image_bytes: bytes, options: ReconstructionOptions) -> Job:
        job = Job(uuid.uuid4().hex, image_bytes, options)
        with self._lock:
            self._jobs[job.job_id] = job
        self._queue.put(job)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def _run(self) -> None:
        while True:
            job = self._queue.get()
            job.state = JobState.RUNNING
            try:
                job.result = reconstruct(
                    job.image_bytes, job.options, job_id=job.job_id
                )
                job.state = JobState.DONE
            except ReconstructionError as exc:
                job.state = JobState.ERROR
                job.error = str(exc)
            except Exception:  # noqa: BLE001 - boundary: never kill the worker
                logger.exception("Unexpected failure in job %s", job.job_id)
                job.state = JobState.ERROR
                job.error = "Internal error during reconstruction."
            finally:
                job._done.set()
                self._queue.task_done()
