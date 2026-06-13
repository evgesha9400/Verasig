import re
import subprocess
from pathlib import Path


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docker-compose.yml").exists():
            return parent
    raise AssertionError("Could not locate project root")


def read_compose_file() -> str:
    return (project_root() / "docker-compose.yml").read_text(encoding="utf-8")


def service_block(compose_text: str, service_name: str) -> str:
    marker = f"  {service_name}:\n"
    start = compose_text.index(marker)
    remainder = compose_text[start + len(marker) :]
    next_service = re.search(r"^  [a-zA-Z0-9_-]+:\s*$", remainder, re.MULTILINE)
    end = (
        start + len(marker) + next_service.start()
        if next_service
        else len(compose_text)
    )
    return compose_text[start:end]


def test_compose_orders_db_migration_backend_and_frontend() -> None:
    compose_text = read_compose_file()

    assert compose_text.index("  db:\n") < compose_text.index("  migrate:\n")
    assert compose_text.index("  migrate:\n") < compose_text.index("  app:\n")
    assert compose_text.index("  app:\n") < compose_text.index("  frontend:\n")

    app_block = service_block(compose_text, "app")
    frontend_block = service_block(compose_text, "frontend")

    assert "db:\n        condition: service_healthy" in app_block
    assert "migrate:\n        condition: service_completed_successfully" in app_block
    assert "healthcheck:" in app_block
    assert "app:\n        condition: service_healthy" in frontend_block
    assert '"5173:5173"' in frontend_block
    assert "npm run dev --workspace verasig-web -- --host 0.0.0.0" in frontend_block


def test_make_up_starts_full_stack_from_frontend_entrypoint() -> None:
    result = subprocess.run(
        ["make", "-n", "up"],
        cwd=project_root(),
        check=True,
        capture_output=True,
        text=True,
    )

    dry_run = result.stdout

    assert "docker compose --env-file apps/backend/.env up --build frontend" in dry_run
