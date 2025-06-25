import logging
import os
import pathlib
import subprocess
import sys

from keboola.component.exceptions import UserException

from configuration import AuthEnum, GitConfiguration


class GitHandler:
    REPO_PATH = "repo_clone"

    def __init__(self, git_cfg: GitConfiguration):
        # add path for absolute imports to start at the cloned repository root level
        sys.path.append(os.path.join(pathlib.Path(__file__).parent.parent, GitHandler.REPO_PATH))

        self.env = os.environ.copy()
        self.git_cfg = git_cfg
        self.repo_auth_url = None  # ‼️ NEVER EVER INCLUDE THIS VARIABLE IN LOGGING OUTPUT ‼️

        if not self.git_cfg.url:
            raise UserException("Git repository URL is required")

        if self.git_cfg.auth == AuthEnum.PAT:
            self._set_up_token_auth()

        repo_url = self.git_cfg.url
        if repo_url.startswith("git@") or repo_url.startswith("ssh://"):
            self._set_up_ssh_command()

        # do not ask for credentials when git authentication fails
        self.env["GIT_TERMINAL_PROMPT"] = "0"

    def _set_up_token_auth(self) -> None:
        if not self.git_cfg.encrypted_token:
            raise UserException("No personal access token provided")

        if not self.git_cfg.url.startswith("https://"):
            raise UserException("PAT authentication is only supported for HTTPS URLs")

        self.repo_auth_url = self.git_cfg.url.replace(
            "https://", f"https://x-token-auth:{self.git_cfg.encrypted_token}@"
        )
        logging.info("Git token authentication set up for HTTPS URL.")

    def _set_up_ssh_command(self) -> None:
        if not self.git_cfg.ssh_keys.keys.encrypted_private:
            if self.git_cfg.auth == AuthEnum.SSH:
                raise UserException("SSH key is required for SSH authentication")
            elif self.git_cfg.auth == AuthEnum.NONE:
                logging.warning("SSH URL detected but no SSH private key provided. Trying default SSH configuration.")

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

        if self.git_cfg.ssh_keys.keys.encrypted_private:
            ssh_key_path = os.path.expanduser("~/.ssh/github_private_key")
            with open(ssh_key_path, "wb") as f:
                for line in self.git_cfg.ssh_keys.keys.encrypted_private.splitlines():
                    f.write(line.encode() + b"\n")
            # ensure SSH key has correct permissions
            os.chmod(ssh_key_path, 0o600)
            ssh_command.extend(["-i", ssh_key_path])

        self.env["GIT_SSH_COMMAND"] = " ".join(ssh_command)

    def clone_repository(self, sync_action=False):
        """
        Clone a git repository and return the path to the cloned code.

        Returns:
            Path to the main script file to execute
        """

        branch = self.git_cfg.branch or "main"
        logging.info("Cloning git repository: %s", self.git_cfg.url)

        try:
            clone_args = ["git", "clone"]

            if branch:
                clone_args.extend(["--branch", branch])

            clone_args.extend([self.repo_auth_url or self.git_cfg.url, GitHandler.REPO_PATH])

            process = subprocess.Popen(
                clone_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
            )
            _, stderr = process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown git clone error"
                if "Permission denied" in error_msg or "publickey" in error_msg:
                    error_msg += ". Please check SSH key configuration or use HTTPS URL."
                raise UserException(f"Failed to clone git repository: {error_msg}")

            logging.info("Successfully cloned repository")

            # when cloning for the "list files" sync action, checking for the script file presence doesn't make sense
            # and could cause problems in cases the repository changed for any reason
            if sync_action:
                return None

            source_dir = os.path.join(os.getcwd(), GitHandler.REPO_PATH)
            main_script_path = os.path.join(source_dir, self.git_cfg.filename)
            if not os.path.exists(main_script_path):
                raise UserException(f"Main script file '{self.git_cfg.filename}' not found in repository")

            return main_script_path

        except Exception as e:
            raise UserException(f"Error processing git repository: {str(e)}") from e

    def get_repository_branches(self):
        """
        Get a list of branches in the git repository.

        Returns:
            List of branch names
        """
        try:
            branches_args = ["git", "ls-remote", "--heads"]

            branches_args.append(self.repo_auth_url or self.git_cfg.url)

            process = subprocess.Popen(
                branches_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise UserException(f"Failed to get branches: {stderr.decode()}")

            branches = [line.strip().split("refs/heads/")[-1] for line in stdout.decode().splitlines() if line.strip()]
            return [{"value": b, "label": b} for b in branches]

        except Exception as e:
            raise UserException(f"Error getting repository branches: {str(e)}") from e

    def get_repository_files(self):
        _ = self.clone_repository(sync_action=True)

        files = []
        for dirpath, _, filenames in os.walk(GitHandler.REPO_PATH):
            if dirpath.startswith(f"{GitHandler.REPO_PATH}/.git"):
                continue
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(dirpath, filename)
                # strip the repository path prefix
                files.append(path[len(GitHandler.REPO_PATH) + 1 :])

        return [{"value": f, "label": f} for f in files]
