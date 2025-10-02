import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from web_interface import app  # noqa: E402


class WebInterfaceTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"57", response.data)

    def test_dashboard_page(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("工具细节", html)

    def test_api_status(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("services", data)
        self.assertIsInstance(data["services"], list)
        self.assertIn("external_details", data)
        self.assertIsInstance(data["external_details"], list)

    def test_docs_endpoint(self):
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)

    def test_config_download(self):
        response = self.client.get("/config/seed_network_overlay.yaml")
        self.assertEqual(response.status_code, 200)
        response.close()


if __name__ == "__main__":
    unittest.main()
