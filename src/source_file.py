import os


class FileHandler:
    @staticmethod
    def prepare_script_file(destination_path: str, script: str) -> str:
        script_filename = os.path.join(destination_path, "script.py")

        with open(script_filename, "w") as file:
            file.write(script)

        return script_filename
