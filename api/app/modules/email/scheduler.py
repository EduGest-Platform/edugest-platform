"""Standalone email scheduler: python -m app.modules.email.scheduler."""
import logging
import signal
from datetime import timedelta
from threading import Event

from app.core.config import Settings, settings
from app.core.db import SessionLocal, utcnow
from app.modules.email.queue import recover_interrupted
from app.modules.email.worker import process_one

logger = logging.getLogger(__name__)


def run_cycle(config: Settings, *, batch_size: int = 20) -> int:
    if not 1 <= batch_size <= 100:
        raise ValueError("Invalid batch size")
    if not config.email_enabled:
        return 0
    # Conservative quarantine window; never requeue an abandoned SMTP claim.
    cutoff = utcnow() - timedelta(seconds=max(3600, 20 * config.email_timeout_seconds))
    with SessionLocal.begin() as db:
        recover_interrupted(db, cutoff=cutoff, limit=batch_size)
    processed = 0
    while processed < batch_size and process_one(config):
        processed += 1
    return processed


def main() -> None:
    if not settings.email_enabled:
        return
    stop = Event()

    def request_stop(signum, frame):
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    while not stop.is_set():
        try:
            run_cycle(settings)
        except Exception:
            # Do not log exception payloads containing recipient or message data.
            logger.error("Email scheduler cycle failed")
        stop.wait(15)


if __name__ == "__main__":
    main()
