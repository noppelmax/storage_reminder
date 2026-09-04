#!/usr/bin/env python3
"""Email the used storage of a configured directory."""

import argparse
import configparser
import logging
from logging.handlers import RotatingFileHandler
import os
import smtplib
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path


LOGGER = logging.getLogger(__name__)
__version__ = "1.0.1"


def configure_logging(log_file: Path | None = None, verbose: bool = False) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        handlers.append(
            RotatingFileHandler(
                log_file,
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
            )
        )

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        handlers=handlers,
        force=True,
    )


def load_config(config_path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if not config.read(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    LOGGER.info("Loaded configuration from %s", config_path)
    return config


def get_storage_usage(directory: str) -> str:
    LOGGER.info("Checking storage usage for %s", directory)
    result = subprocess.run(
        ["du", "-sh", "--", directory],
        check=True,
        capture_output=True,
        text=True,
    )
    usage = result.stdout.split(maxsplit=1)[0]
    LOGGER.info("Storage usage for %s is %s", directory, usage)
    return usage


def build_message(config: configparser.ConfigParser, usage: str) -> EmailMessage:
    storage = config["storage"]
    email = config["email"]
    directory = storage.get("directory", "/path/to/directory")
    subject = email.get("subject", "Home directory storage usage")

    message = EmailMessage()
    message["From"] = email["sender"]
    message["To"] = email["recipient"]
    message["Subject"] = subject
    message.set_content(
        f"Storage usage for {directory}: {usage}\n"
    )
    return message


def build_test_message(config: configparser.ConfigParser) -> EmailMessage:
    email = config["email"]

    message = EmailMessage()
    message["From"] = email["sender"]
    message["To"] = email["recipient"]
    message["Subject"] = f"Test: {email.get('subject', 'Storage reminder')}"
    message.set_content("This is a test email from the storage reminder.")
    return message


def send_message(config: configparser.ConfigParser, message: EmailMessage) -> None:
    smtp = config["smtp"]
    host = smtp["host"]
    port = smtp.getint("port", fallback=587)
    username = smtp.get("username", "")
    password = os.environ.get("STORAGE_REMINDER_SMTP_PASSWORD", smtp.get("password", ""))

    LOGGER.info("Connecting to SMTP server %s:%s", host, port)
    with smtplib.SMTP(host, port, timeout=30) as server:
        if smtp.getboolean("starttls", fallback=True):
            LOGGER.debug("Starting SMTP TLS")
            server.starttls()
        if username:
            LOGGER.debug("Authenticating to SMTP server as %s", username)
            server.login(username, password)
        LOGGER.info("Sending email to %s with subject %r", message["To"], message["Subject"])
        server.send_message(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("config.ini"),
        help="path to the configuration file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the email instead of sending it",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="send a test email without checking storage usage",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="write rotating logs to this file in addition to stderr",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.log_file, args.verbose)
    LOGGER.info("Starting storage reminder")

    try:
        config = load_config(args.config)
        if args.test_email:
            send_message(config, build_test_message(config))
            LOGGER.info("Test email sent to %s", config["email"]["recipient"])
            return 0

        directory = config["storage"].get("directory", "/path/to/directory")
        usage = get_storage_usage(directory)
        message = build_message(config, usage)
        if args.dry_run:
            LOGGER.info("Dry run requested; email was not sent")
            print(message)
        else:
            send_message(config, message)
            LOGGER.info("Storage reminder sent to %s", message["To"])
    except (
        configparser.Error,
        KeyError,
        FileNotFoundError,
        OSError,
        subprocess.SubprocessError,
        ValueError,
    ) as error:
        LOGGER.exception("Storage reminder failed: %s", error)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())