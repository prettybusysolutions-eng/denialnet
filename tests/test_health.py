import unittest

from routes import health


class HealthTest(unittest.TestCase):
    def test_health_contract(self):
        response = health()
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["service"], "DenialNet™")
        self.assertIn("version", response)


if __name__ == "__main__":
    unittest.main()
