import json
import os
import tempfile
import unittest

import mock
from freezegun import freeze_time
from keboola.component.exceptions import UserException

from component import Component
from configuration import Configuration, SourceEnum, VenvEnum


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


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
