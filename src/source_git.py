import logging
import os
import pathlib
import subprocess
import sys

from keboola.component.exceptions import UserException

from configuration import GitConfiguration


class GitHandler:
    def __init__(self, cfg: GitConfiguration):
        self.REPO_PATH = "repo_clone"

        # add path for absolute imports to start at the cloned repository root level
        sys.path.append(os.path.join(pathlib.Path(__file__).parent.parent, self.REPO_PATH))

        self.cfg = cfg

    def clone_repository(self):
        """
        Clone a git repository and return the path to the cloned code.

        Returns:
            Path to the main script file to execute
        """
        repo_url = self.cfg.url
        if not repo_url:
            raise UserException("Git repository URL is required")

        branch = self.cfg.branch or "main"

        logging.info("Cloning git repository: %s", repo_url)

        try:
            clone_args = ["git", "clone"]

            if branch:
                clone_args.extend(["--branch", branch])

            if self.cfg.encrypted_ssh_key and self.cfg.encrypted_token:
                self.cfg.encrypted_token = None

            if self.cfg.encrypted_token:
                repo_url = repo_url.replace("https://", f"https://x-token-auth:{self.cfg.encrypted_token}@")

            clone_args.extend([repo_url, self.REPO_PATH])

            env = os.environ.copy()

            ssh_command = [
                "ssh",
                # the following lines could be used to disable strict host key checking, but it is better
                # for security reasons to use the known_hosts file prepared in Dockerfile
                # "-o",
                # "StrictHostKeyChecking=no",
                "-o",
                "BatchMode=yes",  # do not ask for credentials when SSH auth fails
                "-o",
                "ConnectTimeout=30",
                "-o",
                "ServerAliveInterval=60",
            ]

            if self.cfg.encrypted_ssh_key:
                ssh_key_path = os.path.expanduser("~/.ssh/github_private_key")
                with open(ssh_key_path, "wb") as f:
                    for line in self.cfg.encrypted_ssh_key.splitlines():
                        f.write(line.encode() + b"\n")
                # ensure SSH key has correct permissions
                os.chmod(ssh_key_path, 0o600)
                ssh_command.extend(["-i", ssh_key_path])
            elif repo_url.startswith("git@") or repo_url.startswith("ssh://"):
                logging.warning("SSH URL detected but no ssh_key_path provided. Trying default SSH configuration.")

            env["GIT_SSH_COMMAND"] = " ".join(ssh_command)

            process = subprocess.Popen(
                clone_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            _, stderr = process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown git clone error"
                if "Permission denied" in error_msg or "publickey" in error_msg:
                    error_msg += ". Please check SSH key configuration or use HTTPS URL."
                raise UserException(f"Failed to clone git repository: {error_msg}")

            logging.info("Successfully cloned repository")

            source_dir = os.path.join(os.getcwd(), self.REPO_PATH)
            main_script_path = os.path.join(source_dir, self.cfg.filename)
            if not os.path.exists(main_script_path):
                raise UserException(f"Main script file '{self.cfg.filename}' not found in repository")

            return main_script_path

        except Exception as e:
            raise UserException(f"Error processing git repository: {str(e)}") from e

    @staticmethod
    def prepare_script_file(script: str, destination_path: str):
        with open(destination_path, "w+") as file:
            file.write(script)
