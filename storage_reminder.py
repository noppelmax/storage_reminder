#!/usr/bin/env python3
"""Email the used storage of a configured directory."""

import argparse
import configparser
import logging
import os
import smtplib
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path


LOGGER = logging.getLogger(__name__)


def load_config(config_path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if not config.read(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    return config


def get_storage_usage(directory: str) -> str:
    result = subprocess.run(
        ["du", "-sh", "--", directory],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.split(maxsplit=1)[0]


def build_message(config: configparser.ConfigParser, usage: str) -> EmailMessage:
    storage = config["storage"]
    email = config["email"]
    directory = storage.get("directory", "/home/i56/mnoppel")
    subject = email.get("subject", "Home directory storage usage")

    message = EmailMessage()
    message["From"] = email["sender"]
    message["To"] = email["recipient"]
    message["Subject"] = subject
    message.set_content(
        f"Storage usage for {directory}: {usage}\n"
    )
    return message


def send_message(config: configparser.ConfigParser, message: EmailMessage) -> None:
    smtp = config["smtp"]
    host = smtp["host"]
    port = smtp.getint("port", fallback=587)
    username = smtp.get("username", "")
    password = os.environ.get("STORAGE_REMINDER_SMTP_PASSWORD", smtp.get("password", ""))

    with smtplib.SMTP(host, port, timeout=30) as server:
        if smtp.getboolean("starttls", fallback=True):
            server.starttls()
        if username:
            server.login(username, password)
        server.send_message(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    try:
        config = load_config(args.config)
        directory = config["storage"].get("directory", "/home/i56/mnoppel")
        usage = get_storage_usage(directory)
        message = build_message(config, usage)
        if args.dry_run:
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
        LOGGER.error("Storage reminder failed: %s", error)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())