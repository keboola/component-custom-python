from pathlib import Path


class FileHandler:
    @staticmethod
    def prepare_script_file(destination_path: str, script: str) -> Path:
        script_filename = Path(destination_path) / "script.py"

        with open(script_filename, "w") as file:
            file.write(script)

        return script_filename
