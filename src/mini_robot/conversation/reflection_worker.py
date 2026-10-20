
import threading
import logging

from mini_robot.conversation.reflection import ReflectionEngine


logger = logging.getLogger(__name__)


class ReflectionWorker:

    def __init__(
        self,
        engine: ReflectionEngine,
        conversation_id: int,
        llm_lock: threading.Lock,
        interval: float = 30.0,
    ):
        self.engine = engine
        self.conversation_id = conversation_id
        self.llm_lock = llm_lock
        self.interval = interval

        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join()

    def _run(self):
        while not self._stop_event.wait(self.interval):

            # Never queue reflection ahead of conversation.
            if not self.llm_lock.acquire(blocking=False):
                continue

            try:
                result = self.engine.reflect(self.conversation_id)

                if result is not None:
                    logger.info(
                        "Reflection: %s (%d memories)",
                        result.summary,
                        len(result.memories),
                    )

            except Exception:
                logger.exception("Background reflection failed")

            finally:
                self.llm_lock.release()
