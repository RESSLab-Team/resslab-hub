"""Pure-unit tests for the small helpers in ``resslab_hub.utils.common``."""

import pytest

from resslab_hub.utils.common import strtobool


class TestStrtobool:
    @pytest.mark.parametrize(
        "value", ["y", "yes", "t", "true", "on", "1", "YES", "True"]
    )
    def test_truthy_values_return_1(self, value):
        assert strtobool(value) == 1

    @pytest.mark.parametrize(
        "value", ["n", "no", "f", "false", "off", "0", "NO", "False"]
    )
    def test_falsy_values_return_0(self, value):
        assert strtobool(value) == 0

    @pytest.mark.parametrize("value", ["maybe", "", "2", "yep"])
    def test_invalid_values_raise(self, value):
        with pytest.raises(ValueError):
            strtobool(value)
