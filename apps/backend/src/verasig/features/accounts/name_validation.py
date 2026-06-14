from unicodedata import category

MAX_ACCOUNT_NAME_LENGTH = 80
VALID_NAME_CHARACTERS = {" ", "-", "'", "."}


def normalize_account_name(value: str) -> str:
    return " ".join(value.strip().split())


def _contains_letter(value: str) -> bool:
    return any(category(char).startswith("L") for char in value)


def _is_allowed_name_character(char: str) -> bool:
    return category(char).startswith("L") or char in VALID_NAME_CHARACTERS


def validate_account_name(value: str, *, field_name: str) -> str:
    normalized = normalize_account_name(value)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    if len(normalized) > MAX_ACCOUNT_NAME_LENGTH:
        raise ValueError(
            f"{field_name} must not exceed {MAX_ACCOUNT_NAME_LENGTH} characters."
        )
    if not _contains_letter(normalized):
        raise ValueError(f"{field_name} must contain at least one letter.")
    if not all(_is_allowed_name_character(char) for char in normalized):
        raise ValueError(
            f"{field_name} can only contain letters, spaces, apostrophes, "
            "hyphens, and periods."
        )
    return normalized


def validate_account_name_pair(first_name: str, last_name: str) -> tuple[str, str]:
    normalized_first = validate_account_name(first_name, field_name="first_name")
    normalized_last = validate_account_name(last_name, field_name="last_name")
    if normalized_first.casefold() == normalized_last.casefold():
        raise ValueError("first_name and last_name must be different.")
    return normalized_first, normalized_last
