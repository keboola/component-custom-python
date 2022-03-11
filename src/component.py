"""
Template Component main class.

"""
import json
import logging
import os
import runpy
import sys
from traceback import TracebackException

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException

# configuration variables
KEY_API_TOKEN = '#api_token'
KEY_PRINT_HELLO = 'print_hello'

# list of mandatory parameters => if some is missing,
# component will fail with readable message on initialization.
REQUIRED_PARAMETERS = [KEY_PRINT_HELLO]
REQUIRED_IMAGE_PARS = []


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

    def run(self):
        parameters = self.configuration.parameters

        script_path = os.path.join(self.data_folder_path, 'script.py')
        self.prepare_script_file(script_path)

        self._merge_user_parameters()

        # install packages
        self.install_packages(parameters.get('packages', []))

        self.execute_script_file(script_path)

    def prepare_script_file(self, destination_path: str):
        script = self.configuration.parameters['code']
        with open(destination_path, 'w+') as file:
            logging.info('Processing script "%s"' % (self.script_excerpt(script)))
            file.write(script)

    def execute_script_file(self, file_path):
        import traceback

        # Change current working directory so that relative paths work
        os.chdir(self.data_folder_path)
        sys.path.append(self.data_folder_path)

        try:
            with open(file_path, 'r') as file:
                script = file.read()
            logging.info('Execute script "%s"' % (self.script_excerpt(script)))
            runpy.run_path(file_path)
            logging.info('Script finished')
        except Exception as err:
            _, _, tb = sys.exc_info()
            stack_len = len(traceback.extract_tb(tb)[4:])
            # print(err, file=sys.stderr)

            stack_trace_records = self._get_stack_trace_records(*sys.exc_info(), -stack_len, chain=True)
            stack_cropped = "\n".join(stack_trace_records)

            raise UserException(f'Script failed. {err}. Detail: {stack_cropped}') from err

    @staticmethod
    def _get_stack_trace_records(etype, value, tb, limit=None, chain=True):
        stack_trace_records = []
        for line in TracebackException(type(value), value, tb, limit=limit).format(chain=chain):
            stack_trace_records.append(line)
        return stack_trace_records

    @staticmethod
    def script_excerpt(script):
        if len(script) > 1000:
            return script[0: 500] + '\n...\n' + script[-500]
        else:
            return script

    @staticmethod
    def install_packages(packages):
        import subprocess
        import sys
        for package in packages:
            args = [
                sys.executable,
                '-m', 'pip', 'install',
                '--disable-pip-version-check',
                '--no-cache-dir',
                '--no-warn-script-location',  # ignore error: installed in '/var/www/.local/bin' which is not on PATH.
                '--force-reinstall',
                package
            ]
            if subprocess.call(args) != 0:
                raise UserException('Failed to install package: ' + package)

    def _merge_user_parameters(self):
        """
        INPLACE Merges user paramters into config.json->parameters property. Rebuilds the physical config.json file
        Returns:

        """
        # remove code
        config_data = self.configuration.config_data

        parameters = self.configuration.parameters
        parameters.pop('code', {})

        parameters = {**parameters,
                      **parameters.get('user_parameters', {})}

        # pop user_params
        parameters.pop('user_parameters', {})

        # build config data and overwrite for the user script
        config_data.pop('parameters', {})
        config_data['parameters'] = parameters
        with open(os.path.join(self.data_folder_path, 'config.json'), 'w+') as inp:
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
        detail = ''
        if len(exc.args) > 1:
            detail = exc.args[1]
        logging.exception(exc, extra={"full_message": detail})
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
