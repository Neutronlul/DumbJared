import pytest
from django.core.exceptions import ValidationError

from core.validators import validate_not_empty_string


class TestValidateNotEmptyString:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(" ", id="space"),
            pytest.param("   ", id="multiple spaces"),
            pytest.param("\t", id="tab"),
            pytest.param("\n", id="newline"),
            pytest.param("valid string", id="valid"),
            pytest.param("0", id="numeric char"),
        ],
    )
    def test_valid_string(self, value: str) -> None:
        validate_not_empty_string(value)

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("", id="empty string"),
        ],
    )
    def test_invalid_string(self, value: str) -> None:
        with pytest.raises(ValidationError, match=r"This field cannot be blank."):
            validate_not_empty_string(value)
