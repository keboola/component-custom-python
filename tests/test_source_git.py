import json
import os
import subprocess
import tempfile
import unittest

import mock
from keboola.component.exceptions import UserException

from component import Component
from configuration import AuthEnum, GitConfiguration
from source_git import GITHUB_APP_TOKEN_ENV, GitHandler

REPO_URL = "https://example.ghe.com/org/repo.git"
TOKEN = "ghs_installation-token"


def _popen_mock(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> mock.MagicMock:
    process = mock.MagicMock()
    process.returncode = returncode
    process.communicate.return_value = (stdout, stderr)
    return mock.MagicMock(return_value=process)


class TestGitHubAppAuthSetUp(unittest.TestCase):
    def test_missing_token_raises_user_exception(self):
        for token in (None, ""):
            with self.subTest(token=token), self.assertRaises(UserException) as context:
                GitHandler(GitConfiguration(url=REPO_URL, auth=AuthEnum.GITHUB_APP), token)
            self.assertIn("GitHub App credentials are missing", str(context.exception))

    def test_non_https_url_raises_user_exception(self):
        for url in ("http://example.ghe.com/org/repo.git", "git@example.ghe.com:org/repo.git"):
            with self.subTest(url=url), self.assertRaises(UserException) as context:
                GitHandler(GitConfiguration(url=url, auth=AuthEnum.GITHUB_APP), TOKEN)
            self.assertIn("only supported for HTTPS URLs without credentials", str(context.exception))

    def test_url_with_credentials_raises_user_exception(self):
        for userinfo in ("user:pass@", "user@", "@", ":@"):
            url = f"https://{userinfo}example.ghe.com/org/repo.git"
            with self.subTest(url=url), self.assertRaises(UserException) as context:
                GitHandler(GitConfiguration(url=url, auth=AuthEnum.GITHUB_APP), TOKEN)
            self.assertIn("only supported for HTTPS URLs without credentials", str(context.exception))

    def test_token_is_ignored_for_other_auth_methods(self):
        handler = GitHandler(GitConfiguration(url=REPO_URL, auth=AuthEnum.NONE), TOKEN)
        self.assertIsNone(handler.github_app_token)
        self.assertEqual(handler._git_command("clone"), ["git", "clone"])
        with handler._git_env() as env:
            self.assertIs(env, handler.env)
            self.assertNotIn("GIT_ASKPASS", env)


class TestGitHubAppAskpass(unittest.TestCase):
    def setUp(self):
        self.handler = GitHandler(GitConfiguration(url=REPO_URL, auth=AuthEnum.GITHUB_APP), TOKEN)

    def test_askpass_answers_username_and_password(self):
        with self.handler._git_env() as env:
            askpass = env["GIT_ASKPASS"]
            self.assertEqual(os.stat(askpass).st_mode & 0o777, 0o700)
            with open(askpass) as f:
                self.assertNotIn(TOKEN, f.read())

            def ask(prompt: str) -> str:
                return subprocess.run([askpass, prompt], env=env, capture_output=True, text=True).stdout.strip()

            self.assertEqual(ask(f"Username for '{REPO_URL}': "), "x-access-token")
            self.assertEqual(ask(f"Password for 'https://x-access-token@example.ghe.com': "), TOKEN)
        self.assertFalse(os.path.exists(askpass))

    def test_token_is_not_in_the_handler_environment(self):
        self.assertNotIn(GITHUB_APP_TOKEN_ENV, self.handler.env)
        self.assertNotIn(GITHUB_APP_TOKEN_ENV, os.environ)

    def test_clone_passes_token_only_through_environment(self):
        popen = _popen_mock()
        with mock.patch("source_git.subprocess.Popen", popen):
            self.handler.clone_repository(sync_action=True)

        args = popen.call_args.args[0]
        env = popen.call_args.kwargs["env"]
        self.assertEqual(args[:4], ["git", "-c", "credential.helper=", "clone"])
        self.assertIn(REPO_URL, args)
        self.assertFalse(any(TOKEN in arg for arg in args))
        self.assertEqual(env[GITHUB_APP_TOKEN_ENV], TOKEN)
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
        self.assertFalse(os.path.exists(env["GIT_ASKPASS"]))

    def test_failed_clone_adds_hint_and_removes_askpass(self):
        popen = _popen_mock(returncode=128, stderr=b"remote: Repository not found.\nfatal: repository not found\n")
        with mock.patch("source_git.subprocess.Popen", popen), self.assertRaises(UserException) as context:
            self.handler.clone_repository(sync_action=True)

        self.assertIn("Check that the GitHub App is installed for this repository", str(context.exception))
        self.assertNotIn(TOKEN, str(context.exception))
        self.assertNotIn("\n.", str(context.exception))
        self.assertFalse(os.path.exists(popen.call_args.kwargs["env"]["GIT_ASKPASS"]))

    def test_list_branches_uses_askpass(self):
        popen = _popen_mock(stdout=b"abc123\trefs/heads/main\ndef456\trefs/heads/dev\n")
        with mock.patch("source_git.subprocess.Popen", popen):
            branches = self.handler.get_repository_branches()

        self.assertEqual([b["value"] for b in branches], ["main", "dev"])
        args = popen.call_args.args[0]
        self.assertEqual(args, ["git", "-c", "credential.helper=", "ls-remote", "--heads", REPO_URL])
        self.assertEqual(popen.call_args.kwargs["env"][GITHUB_APP_TOKEN_ENV], TOKEN)

    def test_failed_list_branches_adds_hint(self):
        popen = _popen_mock(returncode=128, stderr=b"remote: Repository not found.\n")
        with mock.patch("source_git.subprocess.Popen", popen), self.assertRaises(UserException) as context:
            self.handler.get_repository_branches()

        self.assertIn("Check that the GitHub App is installed for this repository", str(context.exception))
        self.assertNotIn("\n.", str(context.exception))
        self.assertFalse(os.path.exists(popen.call_args.kwargs["env"]["GIT_ASKPASS"]))


class TestPatAuthUnchanged(unittest.TestCase):
    def test_pat_clone_arguments_are_unchanged(self):
        with mock.patch.object(GitHandler, "_set_up_netrc"):
            handler = GitHandler(GitConfiguration(url=REPO_URL, auth=AuthEnum.PAT, encrypted_token="pat"))
        popen = _popen_mock()
        with mock.patch("source_git.subprocess.Popen", popen):
            handler.clone_repository(sync_action=True)

        self.assertEqual(
            popen.call_args.args[0],
            ["git", "clone", "--branch", "main", "https://x-token-auth:pat@example.ghe.com/org/repo.git", "repo_clone"],
        )
        self.assertIs(popen.call_args.kwargs["env"], handler.env)


class TestComponentGitHubAppToken(unittest.TestCase):
    PARAMETERS = {
        "source": "git",
        "user_properties": {"key": "value"},
        "git": {"url": REPO_URL, "auth": "githubApp"},
    }

    def _build_component(self, config: dict) -> tuple[Component, str]:
        datadir = tempfile.TemporaryDirectory()
        self.addCleanup(datadir.cleanup)
        with open(os.path.join(datadir.name, "config.json"), "w") as config_file:
            json.dump(config, config_file, indent=4)
        with mock.patch.dict(os.environ, {"KBC_DATADIR": datadir.name}):
            return Component(), datadir.name

    def test_github_app_auth_is_parsed(self):
        component, _ = self._build_component({"parameters": self.PARAMETERS})
        self.assertEqual(component.parameters.git.auth, AuthEnum.GITHUB_APP)

    def test_token_is_read_from_authorization(self):
        cases = {
            "injected": ({"githubApp": {"#token": TOKEN, "expiresAt": "2026-10-12T12:00:00+00:00"}}, TOKEN),
            "missing authorization": (None, None),
            "missing githubApp": ({"workspace": {}}, None),
            "githubApp not an object": ({"githubApp": "x"}, None),
            "token not a string": ({"githubApp": {"#token": 1}}, None),
        }
        for name, (authorization, expected) in cases.items():
            with self.subTest(name):
                config = {"parameters": self.PARAMETERS}
                if authorization is not None:
                    config["authorization"] = authorization
                component, _ = self._build_component(config)
                self.assertEqual(component._get_github_app_token(), expected)

    def test_user_script_config_has_no_github_app_token(self):
        component, datadir = self._build_component(
            {
                "parameters": self.PARAMETERS,
                "authorization": {"githubApp": {"#token": TOKEN}, "workspace": {"host": "h"}},
            }
        )
        component._merge_user_parameters()

        with open(os.path.join(datadir, "config.json")) as config_file:
            written = json.load(config_file)
        self.assertEqual(written["parameters"], {"key": "value"})
        self.assertEqual(written["authorization"], {"workspace": {"host": "h"}})

    def test_user_script_config_without_github_app_is_unchanged(self):
        component, datadir = self._build_component(
            {"parameters": self.PARAMETERS, "authorization": {"workspace": {"host": "h"}}}
        )
        component._merge_user_parameters()

        with open(os.path.join(datadir, "config.json")) as config_file:
            written = json.load(config_file)
        self.assertEqual(written["authorization"], {"workspace": {"host": "h"}})

    def test_token_is_removed_from_config_file_before_packages_are_installed(self):
        component, datadir = self._build_component(
            {
                "parameters": self.PARAMETERS,
                "authorization": {"githubApp": {"#token": TOKEN}, "workspace": {"host": "h"}},
            }
        )
        config_during_install = {}

        def read_config(_):
            with open(os.path.join(datadir, "config.json")) as config_file:
                config_during_install.update(json.load(config_file))

        with (
            mock.patch("component.GitHandler.clone_repository", return_value="main.py"),
            mock.patch("component.PackageInstaller.install_packages_for_repository", side_effect=read_config),
            mock.patch.object(Component, "execute_script_file"),
        ):
            component.run()

        self.assertEqual(config_during_install["authorization"], {"workspace": {"host": "h"}})
        self.assertEqual(config_during_install["parameters"], self.PARAMETERS)

    def test_token_is_removed_from_config_file_for_code_source(self):
        component, datadir = self._build_component(
            {
                "parameters": {**self.PARAMETERS, "source": "code", "code": "print(1)", "packages": ["pandas"]},
                "authorization": {"githubApp": {"#token": TOKEN}},
            }
        )
        config_during_install = {}

        def read_config(_):
            with open(os.path.join(datadir, "config.json")) as config_file:
                config_during_install.update(json.load(config_file))

        with (
            mock.patch("component.PackageInstaller.install_packages", side_effect=read_config),
            mock.patch.object(Component, "execute_script_file"),
        ):
            component.run()

        self.assertEqual(config_during_install["authorization"], {})

    def test_config_file_without_github_app_is_not_rewritten(self):
        component, datadir = self._build_component(
            {"parameters": self.PARAMETERS, "authorization": {"workspace": {"host": "h"}}}
        )
        config_path = os.path.join(datadir, "config.json")
        with open(config_path) as config_file:
            original = config_file.read()

        component._remove_github_app_token_from_config_file()

        with open(config_path) as config_file:
            self.assertEqual(config_file.read(), original)


if __name__ == "__main__":
    unittest.main()
