import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import install_email_service, list_email_providers
from runtime import runtime


class TestEmailServiceTools(unittest.TestCase):
    def setUp(self):
        runtime.reset()
        # Remove email_service if exists
        if hasattr(runtime, 'email_service'):
            delattr(runtime, 'email_service')

    def test_install_email_service_basic(self):
        """install_email_service should register a provider"""
        result = install_email_service(
            domain="example.com",
            asn=100,
            ip="10.100.0.10",
            gateway="10.100.0.254"
        )
        
        self.assertIn("mail.example.com", result)
        self.assertIn("AS100", result)
        self.assertTrue(hasattr(runtime, 'email_service'))
        
    def test_install_email_service_custom_hostname(self):
        """install_email_service should accept custom hostname"""
        result = install_email_service(
            domain="corp.local",
            asn=200,
            ip="10.200.0.5",
            gateway="10.200.0.1",
            hostname="smtp"
        )
        
        self.assertIn("smtp.corp.local", result)
        
    def test_install_multiple_providers(self):
        """Should be able to install multiple email providers"""
        install_email_service("domain1.com", 100, "10.100.0.10", "10.100.0.254")
        install_email_service("domain2.com", 200, "10.200.0.10", "10.200.0.254")
        
        providers = runtime.email_service.get_providers()
        self.assertEqual(len(providers), 2)
        
    def test_list_email_providers_empty(self):
        """list_email_providers should return message when no providers"""
        result = list_email_providers()
        self.assertIn("no email", result.lower())
        
    def test_list_email_providers(self):
        """list_email_providers should return JSON of providers"""
        install_email_service("test.com", 100, "10.100.0.10", "10.100.0.254")
        
        result = list_email_providers()
        self.assertIn("test.com", result)
        self.assertIn("10.100.0.10", result)
        
    def test_email_service_mode(self):
        """install_email_service should respect mode parameter"""
        install_email_service(
            domain="dns-mode.com",
            asn=100,
            ip="10.100.0.10",
            gateway="10.100.0.254",
            mode="dns"
        )
        
        self.assertEqual(runtime.email_service._mode, "dns")


if __name__ == '__main__':
    unittest.main()
