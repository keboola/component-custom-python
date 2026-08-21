import logging
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from keboola.component.exceptions import UserException

from configuration import AuthEnum, GitConfiguration

GITHUB_HOSTS = ("github.com", "www.github.com")
OAUTH_GIT_USERNAME = "x-access-token"
OAUTH_TOKEN_ENV = "GIT_OAUTH_TOKEN"
# git runs this helper whenever it needs a password. Reading the token from the environment keeps it out
# of the command line, out of the cloned repository's .git/config and out of the user script's environment.
ASKPASS_SCRIPT = f'#!/bin/sh\nprintf "%s" "${OAUTH_TOKEN_ENV}"\n'


class GitHandler:
    REPO_PATH = "repo_clone"

    def __init__(self, git_cfg: GitConfiguration, oauth_token: str | None = None):
        # add path for absolute imports to start at the cloned repository root level
        sys.path.append(str(Path(__file__).parent.parent / GitHandler.REPO_PATH))

        # only the git-specific overrides; the full environment is resolved at call time so that
        # changes made after the clone (the virtual environment selection) are not lost
        self.git_env: dict[str, str] = {}
        self.git_cfg = git_cfg
        self.repo_url = git_cfg.repository_url
        self.repo_auth_url = None  # ‼️ NEVER EVER INCLUDE THIS VARIABLE IN LOGGING OUTPUT ‼️

        if not self.repo_url:
            raise UserException(
                "Please select a repository" if git_cfg.auth == AuthEnum.OAUTH else "Git repository URL is required"
            )

        if self.git_cfg.auth == AuthEnum.PAT:
            self._set_up_token_auth()
        elif self.git_cfg.auth == AuthEnum.OAUTH:
            self._set_up_oauth_auth(oauth_token)

        if self.repo_url.startswith("git@") or self.repo_url.startswith("ssh://"):
            self._set_up_ssh_command()

        # do not ask for credentials when git authentication fails
        self.git_env["GIT_TERMINAL_PROMPT"] = "0"

    def _set_up_token_auth(self) -> None:
        if not self.git_cfg.encrypted_token:
            raise UserException("No personal access token provided")

        if not self.repo_url.startswith("https://"):
            raise UserException("PAT authentication is only supported for HTTPS URLs")

        self.repo_auth_url = self.repo_url.replace("https://", f"https://x-token-auth:{self.git_cfg.encrypted_token}@")
        self._set_up_netrc(self.repo_url, self.git_cfg.encrypted_token)
        logging.info("Git token authentication set up for HTTPS URL.")

    @staticmethod
    def _set_up_netrc(repo_url: str, token: str) -> None:
        parsed = urlparse(repo_url)
        if not parsed.hostname:
            return
        netrc_path = Path.home() / ".netrc"
        entry = f"machine {parsed.hostname}\nlogin x-token-auth\npassword {token}\n"
        with open(netrc_path, "w") as f:
            f.write(entry)
        os.chmod(netrc_path, 0o600)

    def _set_up_oauth_auth(self, oauth_token: str | None) -> None:
        if not oauth_token:
            raise UserException(
                "GitHub authorization is missing. Please authorize the component in the Authorization "
                "section of the configuration."
            )

        parsed = urlparse(self.repo_url)
        if parsed.scheme != "https" or parsed.hostname not in GITHUB_HOSTS:
            raise UserException("GitHub authorization is only supported for https://github.com repository URLs")

        # only the username goes into the URL, the token itself is supplied by the askpass helper
        self.repo_auth_url = self.repo_url.replace("https://", f"https://{OAUTH_GIT_USERNAME}@")
        self.git_env[OAUTH_TOKEN_ENV] = oauth_token
        self.git_env["GIT_ASKPASS"] = str(self._write_askpass_helper())
        logging.info("Git OAuth authentication set up for GitHub URL.")

    @staticmethod
    def _write_askpass_helper() -> Path:
        askpass_path = Path("~/.git_askpass.sh").expanduser()
        askpass_path.write_text(ASKPASS_SCRIPT)
        os.chmod(askpass_path, 0o700)
        return askpass_path

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
            ssh_key_path = Path("~/.ssh/github_private_key").expanduser()
            with open(ssh_key_path, "wb") as f:
                for line in self.git_cfg.ssh_keys.keys.encrypted_private.splitlines():
                    f.write(line.encode() + b"\n")
            # ensure SSH key has correct permissions
            os.chmod(ssh_key_path, 0o600)
            ssh_command.extend(["-i", str(ssh_key_path)])

        self.git_env["GIT_SSH_COMMAND"] = " ".join(ssh_command)

    def _explain_error(self, error_msg: str) -> str:
        """Append an actionable hint to git errors whose raw wording does not point at the actual cause."""
        if "Permission denied" in error_msg or "publickey" in error_msg:
            return f"{error_msg}. Please check SSH key configuration or use HTTPS URL."

        # GitHub answers with "not found" for repositories the app cannot see, so that it does not
        # disclose their existence. The usual cause is a missing or incomplete app installation.
        if self.git_cfg.auth == AuthEnum.OAUTH and "not found" in error_msg.lower():
            return (
                f"{error_msg}. The repository is not available to the Keboola GitHub App. Make sure the app "
                "is installed on the account owning the repository and that this repository is included in "
                "the app's repository selection."
            )

        return error_msg

    def subprocess_env(self) -> dict[str, str]:
        """Environment for a subprocess that needs to reach the repository, credentials included.

        Also used for the dependency installation, so that private git dependencies declared in the
        repository authenticate with the same credentials as the clone itself.
        """
        return {**os.environ, **self.git_env}

    def clone_repository(self, sync_action=False) -> Path:
        """
        Clone a git repository and return the path to the cloned code.

        Returns:
            Path to the main script file to execute
        """

        branch = self.git_cfg.branch or "main"
        logging.info("Cloning git repository: %s", self.repo_url)

        try:
            clone_args = ["git", "clone"]

            if branch:
                clone_args.extend(["--branch", branch])

            clone_args.extend([self.repo_auth_url or self.repo_url, GitHandler.REPO_PATH])

            process = subprocess.Popen(
                clone_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.subprocess_env(),
            )
            _, stderr = process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown git clone error"
                raise UserException(f"Failed to clone git repository: {self._explain_error(error_msg)}")

            logging.info("Successfully cloned repository")

            # when cloning for the "list files" sync action, checking for the script file presence doesn't make sense
            # and could cause problems in cases the repository changed for any reason
            if sync_action:
                return Path()

            source_dir = Path.cwd() / GitHandler.REPO_PATH
            main_script_path = Path(source_dir) / self.git_cfg.filename
            if not main_script_path.is_file():
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

            branches_args.append(self.repo_auth_url or self.repo_url)

            process = subprocess.Popen(
                branches_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.subprocess_env(),
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise UserException(f"Failed to get branches: {self._explain_error(stderr.decode())}")

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
                path = str(Path(dirpath) / filename)
                # strip the repository path prefix
                files.append(path[len(GitHandler.REPO_PATH) + 1 :])

        return [{"value": f, "label": f} for f in files]
