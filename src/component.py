"""
Template Component main class.
"""

import json
import logging
import os
import sys
import traceback
from pathlib import Path
from traceback import TracebackException

import dacite
from keboola.component.base import ComponentBase, sync_action
from keboola.component.exceptions import UserException

from configuration import AuthEnum, Configuration, SourceEnum, VenvEnum, encrypted_keys
from package_installer import PackageInstaller
from source_file import FileHandler
from source_git import GitHandler
from subprocess_runner import SubprocessRunner
from venv_manager import VenvManager


class Component(ComponentBase):
    """
    Extends base class for general Python components. Initializes the CommonInterface
    and performs configuration validation.

    For easier debugging the data folder is picked up by default from `../data` path,
    relative to working directory.

    If `debug` parameter is present in the `config.json`, the default logger is set to verbose DEBUG mode.
    """

    def __init__(self):
        super().__init__()
        self._set_init_logging_handler()
        self.parameters = dacite.from_dict(
            Configuration,
            self.configuration.parameters,
            config=dacite.Config(
                cast=[AuthEnum, SourceEnum, VenvEnum],
                convert_key=encrypted_keys,
            ),
        )

    def run(self):
        if self.parameters.source == SourceEnum.CODE:
            base_path = Path(self.data_folder_path)
            script_filename = FileHandler.prepare_script_file(self.data_folder_path, self.parameters.code)
        else:
            base_path = Path(GitHandler.REPO_PATH).absolute()
            git_handler = GitHandler(self.parameters.git)
            script_filename = git_handler.clone_repository()

        if self.parameters.venv == VenvEnum.BASE:
            logging.info("Using base image environment")
        else:
            logging.info("Creating new Python %s virtual environment", self.parameters.venv.value)
            venv_path = VenvManager.prepare_venv(self.parameters.venv.value, base_path)
            logging.info("Virtual environment created at %s", venv_path)
            os.environ["UV_PROJECT_ENVIRONMENT"] = str(venv_path)
            os.environ["VIRTUAL_ENV"] = str(venv_path)

        if self.parameters.source == SourceEnum.CODE:
            if "keboola.component" not in self.parameters.packages:
                self.parameters.packages.insert(0, "keboola.component")
            PackageInstaller.install_packages(self.parameters.packages)
        else:
            PackageInstaller.install_packages_for_repository(base_path)

        self._merge_user_parameters()

        self.execute_script_file(script_filename)

    def execute_script_file(self, file_path: Path):
        # Change current working directory so that relative paths work
        os.chdir(self.data_folder_path)
        sys.path.append(self.data_folder_path)

        try:
            with open(file_path) as file:
                script = file.read()
            logging.info("Executing script:\n%s", self.script_excerpt(script))
            args = ["uv", "run", str(file_path)]
            SubprocessRunner.run(args, "Script executed successfully.", "Script execution failed.")
        except Exception as err:
            _, _, tb = sys.exc_info()
            stack_len = len(traceback.extract_tb(tb)[4:])
            stack_trace_records = self._get_stack_trace_records(*sys.exc_info(), -stack_len, chain=True)
            stack_cropped = "\n".join(stack_trace_records)

            raise UserException(f"Script failed. {err}. Detail: {stack_cropped}") from err

    @staticmethod
    def _get_stack_trace_records(etype, value, tb, limit=None, chain=True):
        stack_trace_records = []
        for line in TracebackException(type(value), value, tb, limit=limit).format(chain=chain):
            stack_trace_records.append(line)
        return stack_trace_records

    @staticmethod
    def script_excerpt(script):
        if len(script) > 640:
            return script[:256] + "\n...\n" + script[-256:]
        else:
            return script

    def _set_init_logging_handler(self):
        for h in logging.getLogger().handlers:
            h.setFormatter(
                logging.Formatter(
                    fmt="[%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )

    def _merge_user_parameters(self):
        """
        INPLACE Merges user parameters into config.json->parameters property. Rebuilds the physical config.json file
        Returns:

        """
        # remove code
        config_data = self.configuration.config_data.copy()

        # build config data and overwrite for the user script
        config_data["parameters"] = self.parameters.user_properties
        with open(Path(self.data_folder_path) / "config.json", "w+") as inp:
            json.dump(config_data, inp)

    @sync_action("listBranches")
    def get_repository_branches(self):
        """
        Returns a list of branches in the git repository.
        This method is used to populate the branches dropdown in the UI.
        """
        git_handler = GitHandler(self.parameters.git)
        return git_handler.get_repository_branches()

    @sync_action("listFiles")
    def get_repository_files(self):
        """
        Returns a list of branches in the git repository.
        This method is used to populate the branches dropdown in the UI.
        """
        git_handler = GitHandler(self.parameters.git)
        return git_handler.get_repository_files()


"""
Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        # this triggers the run method by default and is controlled by the configuration.action parameter
        comp.execute_action()
    except UserException as exc:
        detail = ""
        if len(exc.args) > 1:
            detail = exc.args[1]
        logging.exception(exc, extra={"full_message": detail})
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
