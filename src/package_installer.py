import logging
import os
from pathlib import Path

from subprocess_runner import SubprocessRunner

MSG_OK = "Installation successful."
MSG_ERR = "Installation failed."


class PackageInstaller:
    @staticmethod
    def install_packages(packages: list[str]):
        for package in packages:
            logging.info("Installing package: %s...", package)
            args = ["uv", "pip", "install", package]
            SubprocessRunner.run(args, MSG_OK, MSG_ERR)

    @staticmethod
    def install_packages_for_repository(repository_path: Path):
        """
        Install packages based on the given repository path.
        - If there is a pyproject.toml and a uv.lock file, run uv sync.
        - If there is a requirements.txt file, install packages from it using uv.

        Args:
            repository_path (str): Path to the repository containing requirements.txt.
        """
        pyproject_file = repository_path / "pyproject.toml"
        uv_lock_file = repository_path / "uv.lock"
        requirements_file = repository_path / "requirements.txt"

        # Explicitly install keboola.component in case user didn't include in their dependencies file
        PackageInstaller.install_packages(["keboola.component"])

        args = None
        if pyproject_file.exists() and uv_lock_file.exists():
            logging.info("Running uv sync...")
            os.chdir(repository_path)  # it is currently impossible to pass custom uv.lock path
            args = ["uv", "sync", "--inexact"]
        elif requirements_file.exists():
            logging.info("Installing packages from requirements.txt...")
            args = ["uv", "pip", "install", "-r", str(requirements_file)]

        if not args:
            logging.info("No dependencies file found")
            return

        SubprocessRunner.run(args, MSG_OK, MSG_ERR)
