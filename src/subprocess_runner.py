import logging
import subprocess

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
            text=False,
        )

        stdout, stderr = process.communicate()
        if stdout:
            logging.info("Command output:\n%s", stdout.decode())

        process.poll()
        if process.poll() != 0:
            message = stderr.decode() if stderr else "Unknown installation error"
            raise UserException(f"{err_message} Log in event detail.", message)
        elif stderr:
            message = stderr.decode() if stderr else "uv output empty."
            logging.info("%s Full log in detail.", ok_message, extra={"full_message": message})
        else:
            logging.info(ok_message)
