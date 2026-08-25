from pathlib import Path

import yaml


def test_frontend_compose_proxy_uses_healthy_web_service():
    """Using localhost in the frontend container would proxy API calls back to Vite itself."""
    compose_file = Path(__file__).resolve().parents[2] / "compose.yaml"
    frontend = yaml.safe_load(compose_file.read_text(encoding="utf-8"))["services"]["frontend"]

    assert frontend["environment"]["VITE_API_TARGET"] == "http://web:8000"
    assert frontend["depends_on"]["web"]["condition"] == "service_healthy"
