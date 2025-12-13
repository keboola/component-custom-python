import logging
import subprocess
import threading
import time
from collections import deque

from keboola.component.exceptions import UserException

BUFFER_FLUSH_INTERVAL = 0.5
MAX_BUFFER_SIZE = 50000
MAX_STDERR_LINES = 1000


class LogBuffer:
    """Thread-safe buffer for batching log messages."""

    def __init__(self, prefix: str = "", flush_interval: float = BUFFER_FLUSH_INTERVAL):
        self._buffer: list[str] = []
        self._buffer_size = 0
        self._lock = threading.Lock()
        self._prefix = prefix
        self._flush_interval = flush_interval
        self._last_flush = time.time()

    def add_line(self, line: str) -> None:
        """Add a line to the buffer, flushing if needed."""
        with self._lock:
            self._buffer.append(line)
            self._buffer_size += len(line) + 1
            if self._should_flush():
                self._flush_unlocked()

    def _should_flush(self) -> bool:
        """Check if buffer should be flushed based on size or time."""
        if self._buffer_size >= MAX_BUFFER_SIZE:
            return True
        if time.time() - self._last_flush >= self._flush_interval:
            return True
        return False

    def _flush_unlocked(self) -> None:
        """Flush buffer to log (must hold lock)."""
        if not self._buffer:
            return
        content = "\n".join(self._buffer)
        if self._prefix:
            logging.info("%s:\n%s", self._prefix, content)
        else:
            logging.info(content)
        self._buffer = []
        self._buffer_size = 0
        self._last_flush = time.time()

    def flush(self) -> None:
        """Flush any remaining content in the buffer."""
        with self._lock:
            self._flush_unlocked()


class SubprocessRunner:
    @staticmethod
    def run(
        args: list[str],
        ok_message: str = "Command finished successfully.",
        err_message: str = "Command failed.",
    ):
        logging.debug("Running command: %s", " ".join(args))
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stderr_output: deque[str] = deque(maxlen=MAX_STDERR_LINES)
        stdout_buffer = LogBuffer()
        stderr_buffer = LogBuffer(prefix="Command stderr")

        def read_stderr():
            if process.stderr:
                for line in iter(process.stderr.readline, ""):
                    stripped = line.strip()
                    stderr_output.append(stripped)
                    stderr_buffer.add_line(stripped)
                process.stderr.close()
            stderr_buffer.flush()

        stderr_thread = threading.Thread(target=read_stderr)
        stderr_thread.start()

        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                stdout_buffer.add_line(line.strip())
            process.stdout.close()
        stdout_buffer.flush()
        stderr_thread.join()

        process.wait()
        stderr_str = "\n".join(stderr_output) if stderr_output else "Unknown error."
        if process.returncode != 0:
            raise UserException(f"{err_message} Log in event detail.", stderr_str)
        elif stderr_output:
            logging.info("%s Full log in detail.", ok_message, extra={"full_message": stderr_str})
        else:
            logging.info(ok_message)
