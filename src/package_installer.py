import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from subprocess_runner import SubprocessRunner

if TYPE_CHECKING:
    from configuration import PrivatePyPIConfiguration

MSG_OK = "Installation successful."
MSG_ERR = "Installation failed."

PRIVATE_PYPI_INDEX_NAME = "private"


class PackageInstaller:
    @staticmethod
    def _setup_private_pypi_env(private_pypi: "PrivatePyPIConfiguration | None") -> None:
        """
        Set up environment variables for private PyPI repository authentication.

        Args:
            private_pypi: Private PyPI configuration, or None if not configured.
        """
        if private_pypi is None or not private_pypi.enabled or not private_pypi.url:
            return

        logging.info("Configuring private PyPI repository: %s", private_pypi.url)

        os.environ["UV_INDEX"] = f"{PRIVATE_PYPI_INDEX_NAME}={private_pypi.url}"

        if private_pypi.username:
            env_var_name = f"UV_INDEX_{PRIVATE_PYPI_INDEX_NAME.upper()}_USERNAME"
            os.environ[env_var_name] = private_pypi.username

        if private_pypi.encrypted_password:
            env_var_name = f"UV_INDEX_{PRIVATE_PYPI_INDEX_NAME.upper()}_PASSWORD"
            os.environ[env_var_name] = private_pypi.encrypted_password

    @staticmethod
    def install_packages(
        packages: list[str],
        private_pypi: "PrivatePyPIConfiguration | None" = None
    ) -> None:
        PackageInstaller._setup_private_pypi_env(private_pypi)

        for package in packages:
            logging.info("Installing package: %s...", package)
            args = ["uv", "pip", "install", package]
            SubprocessRunner.run(args, MSG_OK, MSG_ERR)

    @staticmethod
    def install_packages_for_repository(
        repository_path: Path,
        private_pypi: "PrivatePyPIConfiguration | None" = None
    ) -> None:
        """
        Install packages based on the given repository path.
        - If there is a pyproject.toml and a uv.lock file, run uv sync.
        - If there is a requirements.txt file, install packages from it using uv.

        Args:
            repository_path: Path to the repository containing requirements.txt.
            private_pypi: Private PyPI configuration, or None if not configured.
        """
        PackageInstaller._setup_private_pypi_env(private_pypi)

        pyproject_file = repository_path / "pyproject.toml"
        uv_lock_file = repository_path / "uv.lock"
        requirements_file = repository_path / "requirements.txt"

        PackageInstaller.install_packages(["keboola.component"], private_pypi)

        args = None
        if pyproject_file.exists() and uv_lock_file.exists():
            logging.info("Running uv sync...")
            os.chdir(repository_path)
            args = ["uv", "sync", "--inexact"]
        elif requirements_file.exists():
            logging.info("Installing packages from requirements.txt...")
            args = ["uv", "pip", "install", "-r", str(requirements_file)]

        if not args:
            logging.info("No dependencies file found")
            return

        SubprocessRunner.run(args, MSG_OK, MSG_ERR)
