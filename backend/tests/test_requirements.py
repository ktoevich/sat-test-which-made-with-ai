"""The deployed requirements file must stay in step with the backend one.

Vercel's parser rejects "-r" includes, so the root requirements.txt repeats the
backend pins instead of importing them. These tests catch the drift that
duplication invites.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_REQUIREMENTS = REPO_ROOT / "backend" / "requirements.txt"
DEPLOY_REQUIREMENTS = REPO_ROOT / "requirements.txt"


def pins(path: Path) -> dict[str, str]:
    """Map package name to its full pinned spec, ignoring comments."""
    found: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name = line.split("==", 1)[0].split("[", 1)[0].strip().lower()
        found[name] = line
    return found


def test_both_requirements_files_exist():
    assert BACKEND_REQUIREMENTS.is_file()
    assert DEPLOY_REQUIREMENTS.is_file()


def test_the_deployment_file_has_no_include_directives():
    """"-r" and "-c" lines are what broke the Vercel build."""
    for raw in DEPLOY_REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        assert not line.startswith(("-r", "--requirement", "-c", "--constraint")), (
            f"{line!r}: Vercel cannot parse include directives; repeat the pin instead"
        )


def test_every_backend_pin_is_repeated_for_deployment():
    backend, deploy = pins(BACKEND_REQUIREMENTS), pins(DEPLOY_REQUIREMENTS)

    missing = sorted(set(backend) - set(deploy))
    assert not missing, f"missing from the deployment requirements: {missing}"

    mismatched = {
        name: (backend[name], deploy[name])
        for name in backend
        if backend[name] != deploy[name]
    }
    assert not mismatched, f"version drift between the two files: {mismatched}"


def test_the_postgres_driver_is_only_needed_for_deployment():
    """Local development runs on SQLite, so psycopg belongs to the deploy file."""
    assert "psycopg" in pins(DEPLOY_REQUIREMENTS)
    assert "psycopg" not in pins(BACKEND_REQUIREMENTS)


def test_a_serverless_production_host_does_not_get_debug_mode(monkeypatch):
    """FLASK_ENV is easy to forget; the platform already knows the answer."""
    from app.config import DevelopmentConfig, ProductionConfig, get_config

    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("VERCEL_ENV", "production")
    assert get_config() is ProductionConfig

    monkeypatch.setenv("VERCEL_ENV", "preview")
    assert get_config() is DevelopmentConfig

    monkeypatch.delenv("VERCEL_ENV", raising=False)
    assert get_config() is DevelopmentConfig

    # An explicit setting always wins.
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("FLASK_ENV", "development")
    assert get_config() is DevelopmentConfig
