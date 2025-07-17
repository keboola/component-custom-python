import logging
import subprocess
import threading

from keboola.component.exceptions import UserException


class SubprocessRunner:
    @staticmethod
    def run(
        args: list[str],
        ok_message: str = "Command finished sucessfully.",
        err_message: str = "Command failed.",
    ):
        logging.debug("Running command: %s", " ".join(args))
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stderr_output = []

        def read_stderr():
            if process.stderr:
                for line in iter(process.stderr.readline, ""):
                    stderr_output.append(line.strip())
                    logging.info("Command stderr: %s", line.strip())
                process.stderr.close()

        # Start stderr reader thread
        stderr_thread = threading.Thread(target=read_stderr)
        stderr_thread.start()

        # Read stdout in main thread
        stdout_lines = []
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                stdout_lines.append(line.strip())
                logging.info("Command output: %s", line.strip())
            process.stdout.close()
        stderr_thread.join()

        process.wait()
        stderr_str = "\n".join(stderr_output) if stderr_output else "Unknown error."
        if process.returncode != 0:
            raise UserException(f"{err_message} Log in event detail.", stderr_str)
        elif stderr_str:
            logging.info("%s Full log in detail.", ok_message, extra={"full_message": stderr_str})
        else:
            logging.info(ok_message)
