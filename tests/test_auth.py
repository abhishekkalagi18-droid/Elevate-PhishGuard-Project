import unittest
from app import create_app
from config import TestConfig
from database import init_db

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def test_login_page_renders(self):
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Administrator Authentication', res.data)

    def test_dashboard_requires_auth(self):
        res = self.client.get('/dashboard/', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

    def test_valid_login(self):
        with self.client:
            # Fetch CSRF token
            self.client.get('/login')
            with self.client.session_transaction() as sess:
                csrf = sess.get('_csrf_token')

            res = self.client.post('/login', data={
                'username': 'admin',
                'password': 'PhishGuard2026!',
                'csrf_token': csrf
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Security Resilience Overview', res.data)

    def test_invalid_login(self):
        with self.client:
            self.client.get('/login')
            with self.client.session_transaction() as sess:
                csrf = sess.get('_csrf_token')

            res = self.client.post('/login', data={
                'username': 'admin',
                'password': 'WrongPassword123!',
                'csrf_token': csrf
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Invalid credentials', res.data)

if __name__ == '__main__':
    unittest.main()
