import logging
import os
import subprocess

from keboola.component.exceptions import UserException


class PackageInstaller:
    @staticmethod
    def install_packages(packages: list[str]):
        for package in packages:
            logging.info("Installing package: %s...", package)
            args = ["uv", "add", package]
            PackageInstaller._run_installation_in_subprocess(args)

    @staticmethod
    def install_packages_for_repository(repository_path: str):
        """
        Install packages based on the given repository path.
        - If there is a pyproject.toml and a uv.lock file, run uv sync.
        - If there is a requirements.txt file, install packages from it using uv.

        Args:
            repository_path (str): Path to the repository containing requirements.txt.
        """
        pyproject_file = os.path.join(repository_path, "pyproject.toml")
        uv_lock_file = f"{repository_path}/uv.lock"
        requirements_file = f"{repository_path}/requirements.txt"

        args = None
        if os.path.exists(pyproject_file) and os.path.exists(uv_lock_file):
            logging.info("Running uv sync...")
            args = ["uv", "sync", "--inexact"]
        elif os.path.exists(requirements_file):
            logging.info("Installing packages from requirements.txt...")
            args = ["uv", "pip", "install", "-r", requirements_file]

        if not args:
            logging.info("No dependencies file found")
            return

        PackageInstaller._run_installation_in_subprocess(args)

        logging.info("Package installation completed for repository: %s", repository_path)

    @staticmethod
    def _run_installation_in_subprocess(args: list[str]):
        logging.debug("Running command: %s", " ".join(args))
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        process.poll()
        if process.poll() != 0:
            message = stderr.decode() if stderr else "Unknown installation error"
            raise UserException("Installation failed. Log in event detail.", message)
        elif stderr:
            message = stderr.decode() if stderr else "uv output empty."
            logging.info("Installation finished. Full log in detail.", extra={"full_message": message})
