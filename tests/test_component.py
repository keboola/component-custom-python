import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path

import mock
from freezegun import freeze_time
from keboola.component.exceptions import UserException

from component import Component
from configuration import AuthEnum, Configuration, GitConfiguration, SourceEnum, VenvEnum
from github_api import GitHubApi
from package_installer import PackageInstaller
from source_git import GitHandler


def api_response(payload: dict):
    """A urlopen context manager yielding the given payload as a JSON body."""
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
    return response


class TestComponent(unittest.TestCase):

    # set global time to 2010-10-10 - affects functions like datetime.now()
    @freeze_time("2010-10-10")
    # set KBC_DATADIR env to non-existing dir
    @mock.patch.dict(os.environ, {'KBC_DATADIR': './non-existing-dir'})
    def test_run_no_cfg_fails(self):
        with self.assertRaises(ValueError):
            comp = Component()
            comp.run()


class TestConfigurationUserProperties(unittest.TestCase):
    """Test cases for user_properties handling in Configuration dataclass.

    These tests verify the fix for the 'eternal KBC bug' where the Keboola platform
    converts empty JSON objects {} to empty arrays [] in configuration parameters.
    """

    def test_empty_list_converted_to_empty_dict(self):
        """Empty list [] should be converted to empty dict {} via __post_init__."""
        config = Configuration(user_properties=[])
        self.assertEqual(config.user_properties, {})
        self.assertIsInstance(config.user_properties, dict)

    def test_non_empty_list_raises_user_exception(self):
        """Non-empty list should raise UserException."""
        with self.assertRaises(UserException) as context:
            Configuration(user_properties=["item1", "item2"])
        self.assertIn("non-empty list not supported", str(context.exception))

    def test_dict_unchanged(self):
        """Normal dict input should remain unchanged."""
        test_dict = {"key1": "value1", "key2": 123}
        config = Configuration(user_properties=test_dict)
        self.assertEqual(config.user_properties, test_dict)
        self.assertIsInstance(config.user_properties, dict)

    def test_empty_dict_unchanged(self):
        """Empty dict input should remain unchanged."""
        config = Configuration(user_properties={})
        self.assertEqual(config.user_properties, {})
        self.assertIsInstance(config.user_properties, dict)

    def test_default_user_properties_is_empty_dict(self):
        """Default user_properties should be an empty dict."""
        config = Configuration()
        self.assertEqual(config.user_properties, {})
        self.assertIsInstance(config.user_properties, dict)


class TestConfigurationParsingErrors(unittest.TestCase):
    """Configuration parsing errors must surface as UserException, not as an internal error.

    A configuration field with an unexpected type used to escape ``dacite.from_dict`` as a raw
    ``DaciteFieldError``, which the entrypoint caught as a generic exception and turned into an
    opaque internal error (exit 2). Such input is a user problem, so it must exit 1 with a message
    naming the offending field.
    """

    @staticmethod
    def _datadir(parameters: dict):
        """Create a temporary data folder holding a config.json with the given parameters."""
        datadir = tempfile.TemporaryDirectory()
        with open(os.path.join(datadir.name, "config.json"), "w") as config_file:
            json.dump({"parameters": parameters}, config_file)
        return datadir

    def _build_component(self, parameters: dict) -> Component:
        datadir = self._datadir(parameters)
        self.addCleanup(datadir.cleanup)
        with mock.patch.dict(os.environ, {"KBC_DATADIR": datadir.name}):
            return Component()

    def test_string_user_properties_raises_user_exception(self):
        """A string in user_properties must raise UserException naming the field, not exit 2."""
        with self.assertRaises(UserException) as context:
            self._build_component({"source": "code", "venv": "base", "user_properties": '{"key": "value"}'})
        self.assertIn("Invalid component configuration", str(context.exception))
        self.assertIn("user_properties", str(context.exception))

    def test_wrong_type_in_other_field_raises_user_exception(self):
        """Any field of an unexpected type is reported the same way."""
        with self.assertRaises(UserException) as context:
            self._build_component(
                {"source": "code", "venv": "base", "user_properties": {}, "packages": "pandas"}
            )
        self.assertIn("Invalid component configuration", str(context.exception))
        self.assertIn("packages", str(context.exception))

    def test_post_init_user_exception_is_not_rewrapped(self):
        """UserException raised in Configuration.__post_init__ keeps its original message."""
        with self.assertRaises(UserException) as context:
            self._build_component(
                {"source": "code", "venv": "base", "user_properties": ["item1", "item2"]}
            )
        self.assertIn("non-empty list not supported", str(context.exception))
        self.assertNotIn("Invalid component configuration", str(context.exception))

    def test_valid_configuration_is_parsed_unchanged(self):
        """A valid configuration still parses into the expected Configuration values."""
        component = self._build_component(
            {
                "source": "code",
                "venv": "3.13",
                "user_properties": {"debug": False},
                "packages": ["pandas"],
                "code": "print('hello')",
            }
        )
        self.assertEqual(component.parameters.source, SourceEnum.CODE)
        self.assertEqual(component.parameters.venv, VenvEnum.PY_3_13)
        self.assertEqual(component.parameters.user_properties, {"debug": False})
        self.assertEqual(component.parameters.packages, ["pandas"])
        self.assertEqual(component.parameters.code, "print('hello')")


class TestOAuthAuthentication(unittest.TestCase):
    """The OAuth access token must reach git without ever appearing in the command line.

    The component executes arbitrary user code, so the token is passed through an askpass helper that
    reads it from the environment of the git subprocess only.
    """

    def setUp(self):
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        home_patch = mock.patch.dict(os.environ, {"HOME": home.name})
        home_patch.start()
        self.addCleanup(home_patch.stop)

    @staticmethod
    def _git_cfg(url: str = "https://github.com/keboola/example.git") -> GitConfiguration:
        return GitConfiguration(url_oauth=url, auth=AuthEnum.OAUTH)

    def test_missing_repository_asks_for_a_selection(self):
        """The repository is picked from a dropdown here, so asking for a URL would be confusing."""
        with self.assertRaises(UserException) as context:
            GitHandler(GitConfiguration(auth=AuthEnum.OAUTH), "secret-token")
        self.assertIn("select a repository", str(context.exception))

    def test_missing_url_still_asks_for_a_url(self):
        """The wording for the other authentication methods is unchanged."""
        with self.assertRaises(UserException) as context:
            GitHandler(GitConfiguration(auth=AuthEnum.PAT))
        self.assertIn("URL is required", str(context.exception))

    def test_missing_token_raises_user_exception(self):
        """An unauthorized configuration must fail with an actionable message, not with a git error."""
        with self.assertRaises(UserException) as context:
            GitHandler(self._git_cfg(), None)
        self.assertIn("GitHub authorization is missing", str(context.exception))

    def test_non_github_url_raises_user_exception(self):
        """The token is only valid for github.com, other hosts must be rejected up front."""
        with self.assertRaises(UserException) as context:
            GitHandler(self._git_cfg("https://gitlab.com/keboola/example.git"), "secret-token")
        self.assertIn("github.com", str(context.exception))

    def test_token_is_not_part_of_the_clone_url(self):
        """The clone URL carries the username only, so the token cannot leak via argv or .git/config."""
        handler = GitHandler(self._git_cfg(), "secret-token")
        self.assertEqual(handler.repo_auth_url, "https://x-access-token@github.com/keboola/example.git")

    def test_token_is_passed_through_the_askpass_helper(self):
        """The helper is executable and reads the token from the environment instead of embedding it."""
        handler = GitHandler(self._git_cfg(), "secret-token")
        self.assertEqual(handler.git_env["GIT_OAUTH_TOKEN"], "secret-token")

        askpass_path = Path(handler.git_env["GIT_ASKPASS"])
        self.assertTrue(os.access(askpass_path, os.X_OK))
        self.assertNotIn("secret-token", askpass_path.read_text())

    def test_missing_installation_is_explained(self):
        """GitHub reports an unreachable repository as "not found", which hides the real cause."""
        handler = GitHandler(self._git_cfg(), "secret-token")
        explained = handler._explain_error("remote: Repository not found.")
        self.assertIn("Keboola GitHub App", explained)
        self.assertIn("repository selection", explained)

    def test_unrelated_errors_are_not_annotated(self):
        handler = GitHandler(self._git_cfg(), "secret-token")
        self.assertEqual(handler._explain_error("fatal: could not read from remote"), "fatal: could not read from remote")

    def test_token_stays_out_of_the_process_environment(self):
        """The executed user script inherits os.environ, so the token must never be put there."""
        handler = GitHandler(self._git_cfg(), "secret-token")
        self.assertNotIn("GIT_OAUTH_TOKEN", os.environ)
        self.assertEqual(handler.subprocess_env()["GIT_OAUTH_TOKEN"], "secret-token")

    def test_subprocess_env_reflects_later_environment_changes(self):
        """The virtual environment is chosen after the clone, so the env cannot be a stale snapshot."""
        handler = GitHandler(self._git_cfg(), "secret-token")
        with mock.patch.dict(os.environ, {"UV_PROJECT_ENVIRONMENT": "/code/repo_clone/.venv"}):
            env = handler.subprocess_env()
        self.assertEqual(env["UV_PROJECT_ENVIRONMENT"], "/code/repo_clone/.venv")
        self.assertEqual(env["GIT_OAUTH_TOKEN"], "secret-token")

    def test_other_auth_methods_are_untouched(self):
        """A configuration that does not use OAuth must not gain any OAuth environment."""
        handler = GitHandler(GitConfiguration(url="https://github.com/keboola/example.git"))
        self.assertIsNone(handler.repo_auth_url)
        self.assertNotIn("GIT_ASKPASS", handler.git_env)
        self.assertNotIn("GIT_OAUTH_TOKEN", handler.git_env)

    def test_ssh_hint_is_preserved(self):
        """The pre-existing hint for SSH failures must keep working for non-OAuth configurations."""
        handler = GitHandler(GitConfiguration(url="git@github.com:keboola/example.git", auth=AuthEnum.NONE))
        self.assertIn("SSH key configuration", handler._explain_error("Permission denied (publickey)."))


class TestAuthorizationSectionIsNotExposed(unittest.TestCase):
    """The config.json handed to the user script must not contain the decrypted OAuth credentials.

    Besides the user's own access token, the authorization section also carries the shared application
    secret of the Keboola GitHub App, which must never be readable by the executed script.
    """

    CONFIG_DATA = {
        "parameters": {"source": "code", "venv": "base", "user_properties": {"debug": True}},
        "authorization": {
            "oauth_api": {
                "credentials": {
                    "id": "main",
                    "#data": '{"access_token": "secret-token"}',
                    "appKey": "client-id",
                    "#appSecret": "app-secret",
                }
            }
        },
    }

    def setUp(self):
        datadir = tempfile.TemporaryDirectory()
        self.addCleanup(datadir.cleanup)
        self.config_path = Path(datadir.name) / "config.json"
        self.config_path.write_text(json.dumps(self.CONFIG_DATA))
        with mock.patch.dict(os.environ, {"KBC_DATADIR": datadir.name}):
            self.component = Component()

    def test_access_token_is_read_from_the_authorization_section(self):
        self.assertEqual(self.component.oauth_token, "secret-token")

    def test_unreadable_credentials_raise_user_exception(self):
        """Broker credentials that are not valid JSON must not surface as an internal error."""
        datadir = tempfile.TemporaryDirectory()
        self.addCleanup(datadir.cleanup)
        config_data = dict(self.CONFIG_DATA)
        config_data["authorization"] = {"oauth_api": {"credentials": {"id": "main", "#data": "access_token=abc"}}}
        (Path(datadir.name) / "config.json").write_text(json.dumps(config_data))

        with mock.patch.dict(os.environ, {"KBC_DATADIR": datadir.name}):
            with self.assertRaises(UserException) as context:
                Component()
        self.assertIn("could not be read", str(context.exception))

    def test_authorization_is_stripped_from_the_script_config(self):
        self.component._merge_user_parameters()

        written = self.config_path.read_text()
        self.assertNotIn("authorization", json.loads(written))
        self.assertNotIn("secret-token", written)
        self.assertNotIn("app-secret", written)

    def test_user_properties_are_still_written(self):
        """Stripping the credentials must not disturb what the script actually needs."""
        self.component._merge_user_parameters()

        self.assertEqual(json.loads(self.config_path.read_text())["parameters"], {"debug": True})


class TestGitHubApi(unittest.TestCase):
    """Listing repositories has to work across several installations and several pages."""

    def test_repositories_from_all_installations_are_listed(self):
        responses = [
            api_response({"total_count": 2, "installations": [{"id": 1}, {"id": 2}]}),
            api_response(
                {"total_count": 1, "repositories": [{"full_name": "acme/first", "clone_url": "https://gh/first.git"}]}
            ),
            api_response(
                {"total_count": 1, "repositories": [{"full_name": "acme/second", "clone_url": "https://gh/second.git"}]}
            ),
        ]
        with mock.patch("github_api.urllib.request.urlopen", side_effect=responses):
            options = GitHubApi("secret-token").list_installation_repositories()

        self.assertEqual(
            options,
            [
                {"value": "https://gh/first.git", "label": "https://gh/first.git"},
                {"value": "https://gh/second.git", "label": "https://gh/second.git"},
            ],
        )

    def test_value_and_label_are_identical(self):
        """The options are only loaded on demand, so a label the form cannot resolve on reopen would
        leave the user looking at the bare value instead of what they picked."""
        responses = [
            api_response({"total_count": 1, "installations": [{"id": 1}]}),
            api_response(
                {"total_count": 1, "repositories": [{"full_name": "acme/first", "clone_url": "https://gh/first.git"}]}
            ),
        ]
        with mock.patch("github_api.urllib.request.urlopen", side_effect=responses):
            options = GitHubApi("secret-token").list_installation_repositories()

        self.assertEqual(options, [{"value": "https://gh/first.git", "label": "https://gh/first.git"}])

    def test_paginated_results_are_collected(self):
        first_page = [{"full_name": f"acme/repo-{i}", "clone_url": f"https://gh/repo-{i}.git"} for i in range(100)]
        responses = [
            api_response({"total_count": 1, "installations": [{"id": 1}]}),
            api_response({"total_count": 101, "repositories": first_page}),
            api_response({"total_count": 101, "repositories": [{"full_name": "acme/last", "clone_url": "https://gh/l"}]}),
        ]
        with mock.patch("github_api.urllib.request.urlopen", side_effect=responses):
            options = GitHubApi("secret-token").list_installation_repositories()

        self.assertEqual(len(options), 101)
        self.assertEqual(options[-1]["label"], "https://gh/l")

    def test_request_is_authenticated(self):
        response = api_response({"total_count": 0, "installations": []})
        with mock.patch("github_api.urllib.request.urlopen", side_effect=[response]) as urlopen:
            GitHubApi("secret-token").list_installation_repositories()

        headers = {key.lower(): value for key, value in urlopen.call_args.args[0].header_items()}
        self.assertEqual(headers["authorization"], "Bearer secret-token")
        self.assertIn("user-agent", headers)

    def test_read_timeout_is_reported_as_a_user_error(self):
        """A read timeout arrives as a bare TimeoutError, which is not a URLError and would otherwise
        escape both handlers and end the job as an internal error."""
        with mock.patch("github_api.urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(UserException) as context:
                GitHubApi("secret-token").list_installation_repositories()

        self.assertIn("Could not reach the GitHub API", str(context.exception))

    def test_connection_failure_keeps_reporting_its_reason(self):
        with mock.patch("github_api.urllib.request.urlopen", side_effect=urllib.error.URLError("no such host")):
            with self.assertRaises(UserException) as context:
                GitHubApi("secret-token").list_installation_repositories()

        self.assertIn("no such host", str(context.exception))

    def test_revoked_authorization_is_explained(self):
        """A revoked authorization must tell the user to re-authorize, not show a bare HTTP 401."""
        error = urllib.error.HTTPError("https://api.github.com/user/installations", 401, "Unauthorized", {}, None)
        with mock.patch("github_api.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(UserException) as context:
                GitHubApi("secret-token").list_installation_repositories()

        self.assertIn("authorize the component again", str(context.exception))


class TestListRepositoriesAction(unittest.TestCase):
    """The dropdown is where a missing app installation shows up before a job is ever run."""

    def _component(self, authorized: bool) -> Component:
        datadir = tempfile.TemporaryDirectory()
        self.addCleanup(datadir.cleanup)
        # "run" keeps the sync_action decorator from swallowing exceptions into exit(1)
        config_data = {"action": "run", "parameters": {"source": "git", "venv": "base", "user_properties": {}}}
        if authorized:
            credentials = {"id": "main", "#data": '{"access_token": "secret-token"}'}
            config_data["authorization"] = {"oauth_api": {"credentials": credentials}}
        (Path(datadir.name) / "config.json").write_text(json.dumps(config_data))

        with mock.patch.dict(os.environ, {"KBC_DATADIR": datadir.name}):
            return Component()

    def test_unauthorized_configuration_is_reported(self):
        with self.assertRaises(UserException) as context:
            self._component(authorized=False).get_oauth_repositories()
        self.assertIn("GitHub authorization is missing", str(context.exception))

    def test_missing_installation_is_reported(self):
        component = self._component(authorized=True)
        response = api_response({"total_count": 0, "installations": []})
        with mock.patch("github_api.urllib.request.urlopen", side_effect=[response]):
            with self.assertRaises(UserException) as context:
                component.get_oauth_repositories()

        self.assertIn("No repositories are available", str(context.exception))


class TestRepositoryUrlResolution(unittest.TestCase):
    """OAuth configurations carry the repository in "url_oauth", the other methods in "url"."""

    def test_oauth_uses_the_selected_repository(self):
        cfg = GitConfiguration(url="https://github.com/acme/typed.git", auth=AuthEnum.OAUTH,
                               url_oauth="https://github.com/acme/picked.git")
        self.assertEqual(cfg.repository_url, "https://github.com/acme/picked.git")

    def test_other_methods_use_the_typed_url(self):
        cfg = GitConfiguration(url="https://github.com/acme/typed.git", auth=AuthEnum.PAT,
                               url_oauth="https://github.com/acme/picked.git")
        self.assertEqual(cfg.repository_url, "https://github.com/acme/typed.git")


class TestDependencyInstallationCredentials(unittest.TestCase):
    """A repository's private git dependencies must authenticate with the credentials of the clone.

    `uv sync` shells out to git, which offers no credentials of its own, so without an explicit
    environment the fetch fails with "could not read Username for https://github.com".
    """

    def _repository(self, *files: str) -> Path:
        repo = tempfile.TemporaryDirectory()
        self.addCleanup(repo.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        repo_path = Path(repo.name)
        for name in files:
            (repo_path / name).write_text("")
        return repo_path

    def test_environment_is_forwarded_to_uv_sync(self):
        repo_path = self._repository("pyproject.toml", "uv.lock")

        with mock.patch("package_installer.SubprocessRunner.run") as run:
            PackageInstaller.install_packages_for_repository(repo_path, {"GIT_OAUTH_TOKEN": "secret-token"})

        args = run.call_args.args
        self.assertEqual(args[0], ["uv", "sync", "--inexact"])
        self.assertEqual(args[3], {"GIT_OAUTH_TOKEN": "secret-token"})

    def test_environment_is_forwarded_to_requirements_install(self):
        """requirements.txt can reference private git URLs just as pyproject.toml can."""
        repo_path = self._repository("requirements.txt")

        with mock.patch("package_installer.SubprocessRunner.run") as run:
            PackageInstaller.install_packages_for_repository(repo_path, {"GIT_OAUTH_TOKEN": "secret-token"})

        self.assertEqual(run.call_args.args[3], {"GIT_OAUTH_TOKEN": "secret-token"})

    def test_installation_without_credentials_still_works(self):
        """Configurations that need no credentials must keep inheriting the process environment."""
        repo_path = self._repository("pyproject.toml", "uv.lock")

        with mock.patch("package_installer.SubprocessRunner.run") as run:
            PackageInstaller.install_packages_for_repository(repo_path)

        self.assertIsNone(run.call_args.args[3])


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
