from pathlib import Path

from configuration import PyEnum
from subprocess_runner import SubprocessRunner


class VenvManager:
    @staticmethod
    def prepare_venv(py_version: PyEnum, base_path: Path) -> Path:
        """
        Prepare venv for the main script file given. The venv is always created in the same directory
        as the main script file.

        Args:
            main_script_file (str): Path to the main script file.
        """
        venv_path = base_path / ".venv"
        args = ["uv", "venv", "-p", py_version.value, str(venv_path)]

        SubprocessRunner.run(args, "Environment created successfully.", "Environment creation failed.")

        return venv_path
