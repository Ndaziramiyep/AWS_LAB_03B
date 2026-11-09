"""Unit tests run by GitHub Actions before any image is built."""

import sys                                                 # Adjust the import path
from pathlib import Path                                   # Path handling

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))  # Make app/ importable

import main                                                # noqa: E402  The Flask app
import settings                                            # noqa: E402  Release settings

client = main.app.test_client()                            # In-process HTTP client


def test_home_shows_name_and_lab():
    """The page must show the full name and the lab name (lab requirement R4)."""
    body = client.get("/").get_data(as_text=True)          # Fetch the home page
    assert settings.STUDENT_NAME in body                   # Name present
    assert settings.LAB_NAME in body                       # Lab name present


def test_health_matches_release_switch():
    """/health is 200 normally, 500 only when the bad-release demo switch is on."""
    expected = 500 if settings.FORCE_UNHEALTHY else 200    # Demo builds must still pass CI
    assert client.get("/health").status_code == expected   # Health matches the switch


def test_create_order_json():
    """Orders API accepts JSON and returns 201."""
    resp = client.post("/orders", json={"item": "Pallet", "quantity": 3})  # Create an order
    assert resp.status_code == 201                         # Created
    assert resp.get_json()["item"] == "Pallet"             # Echoes the item


def test_create_order_validation():
    """Invalid orders are rejected."""
    assert client.post("/orders", json={"item": ""}).status_code == 400  # Missing item


def test_version_endpoint():
    """/version reports the build version."""
    assert "version" in client.get("/version").get_json()  # Key present
