
import logging
import threading

from mini_robot.conversation.user_profile_curator import UserProfileCurator

logger = logging.getLogger(__name__)


class ProfileWorker:
    """Periodically curate one user's long-term profile."""

    def __init__(
        self,
        curator: UserProfileCurator,
        user_id: int,
        llm_lock: threading.Lock,
        interval: float = 300.0,
    ):
        self.curator = curator
        self.user_id = user_id
        self.llm_lock = llm_lock
        self.interval = interval

        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Start the background worker once."""

        if self._thread is not None:
            raise RuntimeError("ProfileWorker has already been started")

        self._thread = threading.Thread(
            target=self._run,
            name=f"ProfileWorker-{self.user_id}",
            daemon=True,
        )
        self._thread.start()

        logger.info(
            "Started profile worker for user %s (interval %.0fs)",
            self.user_id,
            self.interval,
        )

    def stop(self):
        """Stop the worker and wait for its thread to finish."""

        self._stop_event.set()

        if self._thread is not None:
            self._thread.join()
            self._thread = None

        logger.info("Stopped profile worker for user %s", self.user_id)

    def _run(self):
        """Background worker loop."""

        # Run once immediately, then repeat at the configured interval.
        while not self._stop_event.is_set():

            try:
                if self.curator.needs_update(self.user_id):

                    # Do not wait behind a conversation or reflection.
                    acquired = self.llm_lock.acquire(blocking=False)

                    if acquired:
                        try:
                            if self._stop_event.is_set():
                                break

                            logger.info(
                                "Curating profile for user %s",
                                self.user_id,
                            )

                            profile = self.curator.curate(self.user_id)

                            if profile is not None:
                                logger.info(
                                    "Profile updated for user %s",
                                    self.user_id,
                                )
                        finally:
                            self.llm_lock.release()

                    else:
                        logger.debug(
                            "LLM busy; skipping profile update for user %s",
                            self.user_id,
                        )

            except Exception:
                logger.exception(
                    "Background profile curation failed for user %s",
                    self.user_id,
                )

            # Wait until the next run, or wake immediately on stop.
            if self._stop_event.wait(self.interval):
                break
