import logging
import os
import subprocess

from keboola.component.exceptions import UserException


class PackageInstaller:
    @staticmethod
    def install_packages(packages: list[str]):
        for package in packages:
            logging.info("Installing package: %s...", package)
            args = [
                "uv",
                "add",
                package,
            ]
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            process.poll()
            logging.info("Installation finished: %s. Full log in detail.", package, extra={"full_message": stdout})
            if process.poll() != 0:
                raise UserException(f"Failed to install package: {package}. Log in event detail.", stderr)
            elif stderr:
                logging.warning(stderr)

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

        if os.path.exists(pyproject_file) and os.path.exists(uv_lock_file):
            logging.info("Running uv sync")
            args = ["uv", "sync", "--inexact"]
            process = subprocess.Popen(args, cwd=repository_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            process.poll()
            logging.info("uv sync finished. Full log in detail.", extra={"full_message": stdout})
            if process.poll() != 0:
                raise UserException("Failed to perform uv sync. Log in event detail.", stderr)
            elif stderr:
                logging.warning(stderr)
        elif os.path.exists(requirements_file):
            logging.info("Installing packages from requirements.txt")
            args = ["uv", "pip", "install", "-r", requirements_file]
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            process.poll()
            logging.info("Installation finished. Full log in detail.", extra={"full_message": stdout})
            if process.poll() != 0:
                raise UserException("Failed to install packages. Log in event detail.", stderr)
            elif stderr:
                logging.warning(stderr)
        else:
            logging.info("No dependencies file found")

        logging.info("Package installation completed for repository: %s", repository_path)
