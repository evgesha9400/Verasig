import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = BACKEND_ROOT / "src" / "verasig"

REMOVED_DIRECTORIES = (
    SOURCE_ROOT / "api",
    SOURCE_ROOT / "services",
)

REMOVED_FOUNDATION_WRAPPERS = (
    SOURCE_ROOT / "foundation" / "anthropic_runner.py",
    SOURCE_ROOT / "foundation" / "bybit_account.py",
    SOURCE_ROOT / "foundation" / "bybit_market_data.py",
    SOURCE_ROOT / "foundation" / "db.py",
    SOURCE_ROOT / "foundation" / "static_exchange.py",
    SOURCE_ROOT / "foundation" / "telegram_session.py",
    SOURCE_ROOT / "foundation" / "telethon_source.py",
)

REMOVED_STORAGE_WRAPPERS = (SOURCE_ROOT / "storage" / "repositories.py",)
REMOVED_DOMAIN_WRAPPERS = (SOURCE_ROOT / "domain" / "protocols.py",)

COMPATIBILITY_MARKERS = tuple(
    f"Compatibility {suffix}" for suffix in ("wrapper", "shims", "facade", "catalog")
)

BANNED_IMPORT_PATTERNS = (
    re.compile(r"\bverasig\.services(?:\.|\b)"),
    re.compile(r"\bverasig\.api\.(app|routers|schemas|deps|errors|sse)\b"),
    re.compile(r"from verasig\.storage import \("),
    re.compile(r"from verasig\.storage import .*repository"),
    re.compile(r"\bverasig\.storage\.repositories\b"),
    re.compile(r"\bverasig\.domain\.protocols\b"),
    re.compile(r"\bverasig\.storage\.[a-z_]+_repository\b"),
    re.compile(
        r"\bverasig\.foundation\."
        r"(db|anthropic_runner|bybit_account|bybit_market_data|"
        r"static_exchange|telegram_session|telethon_source)\b"
    ),
    re.compile(r"from verasig\.foundation\.security import\b"),
)


def _python_files_under(path: Path) -> list[Path]:
    return [file for file in path.rglob("*.py") if "__pycache__" not in file.parts]


def test_removed_compatibility_directories_do_not_exist():
    assert [path for path in REMOVED_DIRECTORIES if path.exists()] == []


def test_removed_compatibility_modules_do_not_exist():
    storage_wrappers = sorted((SOURCE_ROOT / "storage").glob("*_repository.py"))
    storage_facades = [path for path in REMOVED_STORAGE_WRAPPERS if path.exists()]
    domain_facades = [path for path in REMOVED_DOMAIN_WRAPPERS if path.exists()]
    foundation_wrappers = [
        path for path in REMOVED_FOUNDATION_WRAPPERS if path.exists()
    ]

    assert storage_wrappers == []
    assert storage_facades == []
    assert domain_facades == []
    assert foundation_wrappers == []


def test_source_files_do_not_contain_compatibility_wrapper_markers():
    offenders = [
        file
        for file in _python_files_under(SOURCE_ROOT)
        if any(marker in file.read_text() for marker in COMPATIBILITY_MARKERS)
    ]

    assert offenders == []


def test_backend_python_imports_use_canonical_modules():
    offenders: list[tuple[Path, str]] = []
    for file in _python_files_under(BACKEND_ROOT / "src") + _python_files_under(
        BACKEND_ROOT / "tests"
    ):
        text = file.read_text()
        for pattern in BANNED_IMPORT_PATTERNS:
            if pattern.search(text):
                offenders.append((file.relative_to(BACKEND_ROOT), pattern.pattern))

    assert offenders == []
