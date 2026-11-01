import unittest
from app import create_app
from config import TestConfig
from database import get_db

class TestSimulationFlow(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        # Grab a seeded tracking token
        with self.app.app_context():
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT tracking_token FROM campaign_targets LIMIT 1")
            self.token = cursor.fetchone()[0]

    def test_email_preview_page(self):
        res = self.client.get(f'/simulate/preview/{self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Enterprise Webmail', res.data)
        self.assertIn(b'Report Phishing', res.data)

    def test_link_click_intercept(self):
        res = self.client.get(f'/simulate/click/{self.token}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Take a breath", res.data)
        self.assertIn(b"3-Minute Micro-Quiz", res.data)

    def test_report_phishing_action(self):
        res = self.client.post(f'/simulate/report/{self.token}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Outstanding Reflexes', res.data)

    def test_quiz_grading_and_certificate(self):
        res = self.client.post(f'/training/quiz-submit/{self.token}', data={
            'q1': '1',
            'q2': '2',
            'q3': '0'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Human Resilience Verified', res.data)
        self.assertIn(b'100%', res.data)

if __name__ == '__main__':
    unittest.main()
