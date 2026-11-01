import unittest
from app import create_app
from config import TestConfig
from services.security import is_domain_allowed, is_valid_email

class TestSecurityServices(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)

    def test_email_validation(self):
        self.assertTrue(is_valid_email("user@company.internal"))
        self.assertTrue(is_valid_email("test.employee+tag@domain.org"))
        self.assertFalse(is_valid_email("invalid-address"))
        self.assertFalse(is_valid_email("@domain.com"))
        self.assertFalse(is_valid_email(""))

    def test_domain_allowlist_enforcement(self):
        with self.app.app_context():
            # Approved domains seeded: company.internal, example.com, phishguard.test, demo.local
            self.assertTrue(is_domain_allowed("sarah.jenkins@company.internal"))
            self.assertTrue(is_domain_allowed("tester@example.com"))
            self.assertTrue(is_domain_allowed("lab@phishguard.test"))

            # Unapproved external domains must be blocked
            self.assertFalse(is_domain_allowed("victim@unauthorized-external-victim.com"))
            self.assertFalse(is_domain_allowed("random@gmail.com"))
            self.assertFalse(is_domain_allowed("target@yahoo.com"))

if __name__ == '__main__':
    unittest.main()
