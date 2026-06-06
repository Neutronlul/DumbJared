from django.core.exceptions import ValidationError


def validate_not_empty_string(value: str) -> None:
    """Ensure a string value is not empty."""
    if value == "":
        msg = "This field cannot be blank."
        raise ValidationError(msg)
