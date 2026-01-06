import os
import unittest

import mock
from freezegun import freeze_time
from keboola.component.exceptions import UserException

from component import Component
from configuration import Configuration


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


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
