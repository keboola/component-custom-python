"""
Template Component main class.
"""

import json
import logging
import os
import runpy
import subprocess
import sys
import traceback
from traceback import TracebackException

import dacite
from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

import source_file
import source_git
from configuration import Configuration, SourceEnum, encrypted_keys


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
            config=dacite.Config(cast=[SourceEnum], convert_key=encrypted_keys),
        )

    def run(self):
        if self.parameters.source == SourceEnum.CODE:
            script_path = source_file.FileHandler.prepare_script_file(self.data_folder_path, self.parameters.code)
        else:
            git_handler = source_git.GitHandler(self.parameters.git)
            script_path = git_handler.clone_repository()

        self._merge_user_parameters()

        self.install_packages(self.parameters.packages)

        self.execute_script_file(script_path)

    def execute_script_file(self, file_path):
        # Change current working directory so that relative paths work
        os.chdir(self.data_folder_path)
        sys.path.append(self.data_folder_path)

        try:
            with open(file_path) as file:
                script = file.read()
            logging.debug('Executing script "%s"', self.script_excerpt(script))
            runpy.run_path(file_path)
            logging.info("Script finished")
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
        if len(script) > 1000:
            return script[0:500] + "\n...\n" + script[-500]
        else:
            return script

    @staticmethod
    def install_packages(packages):
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

    def _set_init_logging_handler(self):
        for h in logging.getLogger().handlers:
            h.setFormatter(logging.Formatter("[Non-script message]: %(message)s"))

    def _merge_user_parameters(self):
        """
        INPLACE Merges user parameters into config.json->parameters property. Rebuilds the physical config.json file
        Returns:

        """
        # remove code
        config_data = self.configuration.config_data.copy()

        # build config data and overwrite for the user script
        config_data["parameters"] = self.parameters.user_properties
        with open(os.path.join(self.data_folder_path, "config.json"), "w+") as inp:
            json.dump(config_data, inp)


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
