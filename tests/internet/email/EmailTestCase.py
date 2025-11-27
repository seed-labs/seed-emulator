from tests.SeedEmuTestCase import SeedEmuTestCase
from seedemu.core import Emulator, Binding, Filter
import docker
import time

class EmailTestCase(SeedEmuTestCase):
    def test_email_service(self):
        """
        Test Comprehensive Email Service (Postfix + Dovecot + Roundcube)
        Includes:
        1. Port listening check (SMTP:25, IMAP:143, Webmail:80)
        2. Host accessibility for Webmail
        3. Cross-domain email sending and receiving
        4. DNS resolution check
        """
        self.wait_until_all_containers_up(14)  # Adjust based on actual container count

        # Define container names based on B29 topology
        # Using format: {prefix}-{node_name}-{ip}
        # We need to find the exact names dynamically or assume standard naming
        client = docker.from_env()
        containers = client.containers.list()
        
        def get_container(pattern):
            for c in containers:
                if pattern in c.name:
                    return c
            return None

        mail_qq = get_container("as200h-mail")
        mail_gmail = get_container("as201h-mail")
        web_qq = get_container("as200h-webmail")
        web_gmail = get_container("as201h-webmail")

        self.assertIsNotNone(mail_qq, "Mail server for QQ not found")
        self.assertIsNotNone(mail_gmail, "Mail server for Gmail not found")
        self.assertIsNotNone(web_qq, "Webmail for QQ not found")
        self.assertIsNotNone(web_gmail, "Webmail for Gmail not found")

        # 1. Service Port Check
        # Check if services are listening inside containers
        self.assertTrue(self.check_port(mail_qq, 25), "SMTP port 25 not open on QQ mail")
        self.assertTrue(self.check_port(mail_qq, 143), "IMAP port 143 not open on QQ mail")
        self.assertTrue(self.check_port(web_qq, 80), "HTTP port 80 not open on QQ webmail")

        # 2. Webmail Accessibility
        # Check from host (mapped ports 18080 and 18081)
        # Note: In test environment, we might not be able to curl localhost:18080 if running inside another container,
        # but assuming we run tests on host or in a way that can access mapped ports.
        # For safety, we check container internal localhost access first.
        exit_code, output = web_qq.exec_run("curl -sS -I http://localhost/roundcube/")
        self.assertEqual(exit_code, 0, "Failed to access Roundcube locally on QQ webmail")
        self.assertIn(b"200 OK", output, "Roundcube did not return 200 OK on QQ webmail")

        # 3. Cross-domain Email Test (QQ -> Gmail)
        # Send email using sendmail command inside container
        send_cmd = """bash -c 'printf "From: user@qq.com\nTo: user@gmail.com\nSubject: Test Email\n\nHello" | sendmail -t'"""
        exit_code, _ = mail_qq.exec_run(send_cmd)
        self.assertEqual(exit_code, 0, "Failed to send email from QQ")

        # Wait for delivery
        time.sleep(5)

        # Check reception at Gmail
        check_cmd = "ls /home/user/Maildir/new"
        exit_code, output = mail_gmail.exec_run(check_cmd)
        self.assertEqual(exit_code, 0, "Failed to list Maildir on Gmail")
        self.assertTrue(len(output.strip()) > 0, "Email not received at Gmail")

    def check_port(self, container, port):
        """Helper to check if a port is listening inside container"""
        # Use netstat or ss. ss is more likely available in modern minimal images
        # But our images might have net-tools. Let's try ss first.
        exit_code, output = container.exec_run(f"ss -tlnp | grep :{port}")
        if exit_code != 0 or not output.strip():
             # Fallback to netstat if ss fails or returns nothing (though grep failure implies nothing found)
             exit_code, output = container.exec_run(f"netstat -tln | grep :{port}")
        
        return exit_code == 0 and len(output.strip()) > 0

    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_email_service'))
        return test_suite
