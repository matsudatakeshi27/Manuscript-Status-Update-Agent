# Manuscript Status Update Agent

An experimental local application that monitors manuscript submission statuses on ScholarOne and sends email notifications when a manuscript's status changes.

## Overview

The goal of this project is to help researchers avoid manually checking manuscript submission websites.

The application:
- Retrieves manuscript information from a submission website using an OpenClaw browser session.
- Tracks manuscript IDs, titles, and statuses.
- Detects changes in manuscript status.
- Sends email notifications when an existing manuscript's status changes.
- Allows users to configure their own monitoring interval.
- Stores monitoring data and credentials locally on their computers.

## Current Status

This is an experimental prototype.

Currently supported:
- Operating system: macOS
- Manuscript platform: ScholarOne
- Browser automation: OpenClaw
- Email notifications: Gmail SMTP
- Scheduling: macOS LaunchAgent

The application has not yet been fully tested on another computer.

## Requirements

- macOS
- Python (version 3.14 has been tested)
- OpenClaw installed and configured
- A working OpenClaw browser session logged into ScholarOne
- A Gmail account with an app password for email notifications

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/matsudatakeshi27/Manuscript-Status-Update-Agent.git

cd Manuscript-Status-Update-Agent
```

### 2. Install Python dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 3. Configure private settings

The application stores private settings outside the project directory.

Create the private configuration directory:

```bash
mkdir -p ~/.scholarone-monitor/logs
```

Create your private email configuration:

```bash
cp .env.example ~/.scholarone-monitor/.env
```

Edit the file:

```bash
nano ~/.scholarone-monitor/.env
```

Enter your own Gmail settings:

```text
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
NOTIFICATION_EMAIL=recipient@example.com
```

Save the file and protect it:

```bash
chmod 600 ~/.scholarone-monitor/.env
```

Never share your `.env` file or upload it to GitHub.

### 4. Configure monitoring frequency

Copy the example configuration:

```bash
cp config.example.json ~/.scholarone-monitor/config.json
```

Edit:

```bash
nano ~/.scholarone-monitor/config.json
```

Example:

```json
{
    "monitoring_interval_hours": 6,
    "notification_enabled": true
}
```

Change the interval to your preferred number of hours.

### 5. Log into ScholarOne

Open your OpenClaw browser and log into your ScholarOne account.

The application uses your existing browser session. Do not put your ScholarOne password in the project files.

### 6. Run a manual test

From the project directory:

```bash
python3 src/monitor.py
```

The application should retrieve the manuscript dashboard and check for status changes.

The first time a manuscript is recorded, it becomes the baseline. Notifications are sent for subsequent status changes.

### 7. Configure automatic monitoring

Automatic scheduling is being tested and will be documented after the installation workflow is validated.

## Data and Privacy

Each user maintains their own:
- Email credentials
- Monitoring configuration
- Manuscript database
- Browser session
- Monitoring logs

These are stored locally in:

```text
~/.scholarone-monitor/
```

Private data should never be committed to the GitHub repository.

## Future Development

Planned improvements:
- Support for Editorial Manager and additional manuscript platforms.
- A user-friendly installation and configuration interface.
- Support for different AI agents and browser automation tools.
- More email providers.
- Easier installation and distribution.
- Update for other browsers
