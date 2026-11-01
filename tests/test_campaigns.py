import unittest
from app import create_app
from config import TestConfig
from database import get_db

class TestCampaigns(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def _login(self):
        self.client.get('/login')
        with self.client.session_transaction() as sess:
            csrf = sess.get('_csrf_token')
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'PhishGuard2026!',
            'csrf_token': csrf
        })
        with self.client.session_transaction() as sess:
            return sess.get('_csrf_token')

    def test_campaigns_list_view(self):
        self._login()
        res = self.client.get('/dashboard/campaigns')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Active & Historical Drills', res.data)

    def test_create_new_campaign(self):
        csrf = self._login()
        res = self.client.post('/dashboard/campaigns/new', data={
            'name': 'Unit Test Simulation Drill',
            'template_id': '1',
            'department_target': 'Engineering',
            'delivery_mode': 'simulation',
            'csrf_token': csrf
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Unit Test Simulation Drill', res.data)
        self.assertIn(b'Drill Telemetry Funnel', res.data)

if __name__ == '__main__':
    unittest.main()
