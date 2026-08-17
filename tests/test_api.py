"""Tests for the REST API (optional bearer auth + new endpoints)."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestApiAuth(unittest.TestCase):
    def _make_app(self):
        from web.api import create_api

        return create_api()

    def setUp(self):
        os.environ["API_KEY"] = "sekret"
        self.app = self._make_app()
        self.client = self.app.test_client()

    def tearDown(self):
        os.environ.pop("API_KEY", None)

    def test_health_is_public(self):
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

    def test_root_is_public_and_lists_endpoints(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("/api/v1/build", res.get_json()["endpoints"])
        self.assertEqual(res.get_json()["auth"], "required")

    def test_generate_requires_key(self):
        res = self.client.post("/api/v1/generate", json={"prompt": "hello"})
        self.assertEqual(res.status_code, 401)

    def test_generate_rejects_wrong_key(self):
        res = self.client.post(
            "/api/v1/generate",
            json={"prompt": "hello"},
            headers={"X-API-Key": "wrong"},
        )
        self.assertEqual(res.status_code, 401)

    def test_generate_accepts_bearer_key(self):
        with patch("web.api.get_model") as get_model:
            model = get_model.return_value
            model.process_request.return_value = {"intent": "general", "ok": True}
            res = self.client.post(
                "/api/v1/generate",
                json={"prompt": "hello"},
                headers={"Authorization": "Bearer sekret"},
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["intent"], "general")

    def test_build_requires_key(self):
        res = self.client.post("/api/v1/build", json={"prompt": "an app"})
        self.assertEqual(res.status_code, 401)

    def test_plugins_requires_key(self):
        res = self.client.get("/api/v1/plugins")
        self.assertEqual(res.status_code, 401)


class TestApiAuthDisabled(unittest.TestCase):
    def test_no_key_means_open(self):
        os.environ.pop("API_KEY", None)
        from web.api import create_api

        app = create_api()
        client = app.test_client()
        with patch("web.api.get_model") as get_model:
            model = get_model.return_value
            model.process_request.return_value = {"ok": True}
            res = client.post("/api/v1/generate", json={"prompt": "hi"})
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
