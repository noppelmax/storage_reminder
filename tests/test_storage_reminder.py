import configparser
import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).parents[1]))

import storage_reminder


def make_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read_dict(
        {
            "storage": {"directory": "/home/test-user"},
            "email": {
                "sender": "sender@example.com",
                "recipient": "recipient@example.com",
                "subject": "Storage report",
            },
            "smtp": {
                "host": "smtp.example.com",
                "port": "587",
                "starttls": "true",
                "username": "sender@example.com",
                "password": "config-password",
            },
        }
    )
    return config


class StorageReminderTests(unittest.TestCase):
    def test_version_flag(self) -> None:
        output = io.StringIO()
        with patch.object(sys, "argv", ["storage_reminder.py", "--version"]):
            with self.assertRaises(SystemExit) as exit_result:
                with contextlib.redirect_stdout(output):
                    storage_reminder.parse_args()

        self.assertEqual(exit_result.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), "storage_reminder.py 1.0.0")

    @patch("storage_reminder.subprocess.run")
    def test_get_storage_usage_returns_size(self, run: Mock) -> None:
        run.return_value.stdout = "42G\t/home/test-user\n"

        usage = storage_reminder.get_storage_usage("/home/test-user")

        self.assertEqual(usage, "42G")
        run.assert_called_once_with(
            ["du", "-sh", "--", "/home/test-user"],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("storage_reminder.subprocess.run", side_effect=subprocess.CalledProcessError(1, "du"))
    def test_get_storage_usage_propagates_du_failure(self, run: Mock) -> None:
        with self.assertRaises(subprocess.CalledProcessError):
            storage_reminder.get_storage_usage("/missing")

    def test_build_message_contains_usage(self) -> None:
        message = storage_reminder.build_message(make_config(), "42G")

        self.assertEqual(message["From"], "sender@example.com")
        self.assertEqual(message["To"], "recipient@example.com")
        self.assertEqual(message["Subject"], "Storage report")
        self.assertIn("Storage usage for /home/test-user: 42G", message.get_content())

    @patch("storage_reminder.smtplib.SMTP")
    @patch.dict("storage_reminder.os.environ", {"STORAGE_REMINDER_SMTP_PASSWORD": "environment-password"})
    def test_send_message_uses_environment_password(self, smtp_class: Mock) -> None:
        server = smtp_class.return_value.__enter__.return_value
        message = storage_reminder.build_message(make_config(), "42G")

        storage_reminder.send_message(make_config(), message)

        smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=30)
        server.starttls.assert_called_once_with()
        server.login.assert_called_once_with("sender@example.com", "environment-password")
        server.send_message.assert_called_once_with(message)


if __name__ == "__main__":
    unittest.main()