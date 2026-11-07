EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def normalize_email(value: object) -> object:
    """Trim and lowercase emails so login and uniqueness checks ignore case."""
    if isinstance(value, str):
        return value.strip().lower()
    return value
