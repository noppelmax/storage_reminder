# Weekly Storage Reminder

[![CI](https://github.com/noppelmax/storage_reminder/actions/workflows/ci.yml/badge.svg)](https://github.com/noppelmax/storage_reminder/actions/workflows/ci.yml) [![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/noppelmax/storage_reminder/releases)

This script runs `du -sh` for a configured directory and emails the resulting human-readable storage usage.

The current version is `1.0.0`. Check it with:

```bash
./storage_reminder.py --version
```

## Setup

1. Copy `config.example.ini` to `config.ini`, then edit it with the directory, sender, recipient, and SMTP server details:

   ```bash
   cp config.example.ini config.ini
   ```

2. Set the SMTP password. The `STORAGE_REMINDER_SMTP_PASSWORD` environment variable takes precedence over the value in `config.ini`.
3. Restrict access to the configuration file because it may contain SMTP credentials:

   ```bash
   chmod 600 config.ini
   ```

4. Test without sending an email:

   ```bash
   ./storage_reminder.py --dry-run
   ```

5. Send a test email to verify the SMTP settings:

   ```bash
   ./storage_reminder.py --test-email
   ```

## Tests

Run the unit tests locally with:

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions runs the tests and Python syntax checks on pushes and pull requests.

## Cron

Find the absolute paths first:

```bash
pwd
which python3
```

Edit the user crontab with `crontab -e` and add this example, replacing the paths with the values from your system:

```cron
0 9 * * 1 /usr/bin/env STORAGE_REMINDER_SMTP_PASSWORD='your-password' /usr/bin/python3 /path/to/cron_storage_reminder/storage_reminder.py --config /path/to/cron_storage_reminder/config.ini >> /path/to/cron_storage_reminder/storage_reminder.log 2>&1
```

This runs every Monday at 09:00 in the server's local timezone. For better secret handling, use a protected wrapper script or the cron service's environment configuration instead of putting the password directly in the crontab.

To install the entry from a shell without opening an editor, run this from the project directory. It removes an older copy of this same entry before adding the current one:

```bash
CRON_LINE="0 9 * * 1 /usr/bin/python3 $(pwd)/storage_reminder.py --config $(pwd)/config.ini >> $(pwd)/storage_reminder.log 2>&1"
(crontab -l 2>/dev/null | grep -vF "storage_reminder.py --config"; echo "$CRON_LINE") | crontab -
```

Check the installed entry with:

```bash
crontab -l
```

The script exits with status `1` and logs an error if the configuration, `du`, SMTP connection, authentication, or email delivery fails.