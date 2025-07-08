import logging
from pathlib import Path

from subprocess_runner import SubprocessRunner


class PackageInstaller:
    @staticmethod
    def install_packages(packages: list[str]):
        for package in packages:
            logging.info("Installing package: %s...", package)
            args = ["uv", "add", package]
            SubprocessRunner.run(args, "Installation successful.", "Installation failed.")

    @staticmethod
    def install_packages_for_repository(repository_path: str):
        """
        Install packages based on the given repository path.
        - If there is a pyproject.toml and a uv.lock file, run uv sync.
        - If there is a requirements.txt file, install packages from it using uv.

        Args:
            repository_path (str): Path to the repository containing requirements.txt.
        """
        pyproject_file = Path(repository_path) / "pyproject.toml"
        uv_lock_file = Path(repository_path) / "uv.lock"
        requirements_file = Path(repository_path) / "requirements.txt"

        args = None
        if pyproject_file.exists() and uv_lock_file.exists():
            logging.info("Running uv sync...")
            args = ["uv", "sync", "--inexact"]
        elif requirements_file.exists():
            logging.info("Installing packages from requirements.txt...")
            args = ["uv", "pip", "install", "-r", str(requirements_file)]

        if not args:
            logging.info("No dependencies file found")
            return

        SubprocessRunner.run(args, "Installation successful.", "Installation failed.")
