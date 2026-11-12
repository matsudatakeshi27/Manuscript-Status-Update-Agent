# Manuscript Status Update Agent

An experimental local application that monitors manuscript submission statuses and sends email notifications when a manuscript's status changes.

The application uses **OpenClaw for browser automation** and **Ollama for locally hosted AI models**. It is designed to run on users' own computers without requiring a paid AI API subscription.

## Overview

The application helps researchers avoid manually checking manuscript submission websites.

Features:
- Retrieves manuscript information from submission websites using OpenClaw.
- Uses a locally hosted AI model through Ollama.
- Tracks manuscript IDs, titles, and statuses.
- Detects changes in manuscript status.
- Sends email notifications when an existing manuscript's status changes.
- Allows users to configure their own monitoring interval.
- Stores credentials and monitoring data locally.

## Current Status

This is an experimental prototype.

Currently supported:
- Operating system: macOS
- Manuscript platform: ScholarOne
- Browser automation: OpenClaw
- Local AI models: Ollama
- Tested model: Qwen3 8B (`qwen3:8b`)
- Email notifications: Gmail SMTP
- Scheduling: macOS LaunchAgent

The application has not yet been fully tested on another computer.

## Requirements

Users need to install:

1. **Python** — runs the monitoring application.
2. **OpenClaw** — controls the browser and retrieves manuscript information.
3. **Ollama** — runs the AI model locally.
4. **A supported browser** — used to access the manuscript submission website.
5. **A Gmail account** — used to send email notifications.

No paid AI API subscription is required when using Ollama.

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

### 3. Install Ollama

Download Ollama:

https://ollama.com/download

Install and open Ollama.

Download the default model:

```bash
ollama pull qwen3:8b
```

Test the model:

```bash
ollama run qwen3:8b
```

If the model responds successfully, Ollama is working.

The default model is Qwen3 8B. Users may need a smaller model depending on their computer's available memory.

### 4. Install and configure OpenClaw

Install OpenClaw following its official instructions:

https://docs.openclaw.ai/

Configure OpenClaw to use the local Ollama model:

```text
ollama/qwen3:8b
```

Make sure OpenClaw can access and control a supported browser.

### 5. Log into ScholarOne

Open the browser controlled by OpenClaw and log into your own ScholarOne account.

The application uses your existing browser session. Do not put your ScholarOne password in the project files.

### 6. Configure private email settings

The application uses Gmail SMTP to send manuscript status notifications.

You will need:
- A Gmail account.
- A Google App Password (16 characters), not your regular Gmail password.

#### Step 1. Enable 2-Step Verification

Google requires 2-Step Verification before you can generate an App Password.

1. Visit https://myaccount.google.com/security
2. Find **How you sign in to Google**.
3. Enable **2-Step Verification** if it is not already enabled.

#### Step 2. Generate a Google App Password

1. Visit https://myaccount.google.com/apppasswords
2. Sign in to your Google account.
3. Enter an app name, such as `Manuscript Monitor`.
4. Click **Create**.
5. Google will generate a 16-character App Password.
6. Copy this password and keep it private.

Google may display the password with spaces for readability. Enter it without spaces in your configuration file.

Note: App Passwords may be unavailable for some Google accounts, including accounts managed by organizations with certain security policies.

#### Step 3. Create your private email configuration

Create the private configuration directory:

```bash
mkdir -p ~/.scholarone-monitor/logs
```

Copy the example configuration:

```bash
cp .env.example ~/.scholarone-monitor/.env
```

Edit the file:

```bash
nano ~/.scholarone-monitor/.env
```

Enter your own information:

```text
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
NOTIFICATION_EMAIL=recipient@example.com
```

Explanation:
- `GMAIL_ADDRESS`: Your Gmail address used to send notifications.
- `GMAIL_APP_PASSWORD`: The 16-character Google App Password generated in Step 2. Do not use your regular Gmail password.
- `NOTIFICATION_EMAIL`: The email address that should receive manuscript status notifications. It can be the same as your Gmail address.

Save the file and restrict access:

```bash
chmod 600 ~/.scholarone-monitor/.env
```

**Security:** Never share your App Password, commit your `.env` file, or upload it to GitHub. Each user must generate and configure their own App Password.

### 7. Configure monitoring frequency

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

Users can change the monitoring interval to their preferred frequency.

### 8. Run a manual test

From the project directory:

```bash
python3 src/monitor.py
```

The application should retrieve the manuscript dashboard and check for status changes.

The first time a manuscript is recorded, it becomes the baseline. Notifications are sent for subsequent status changes.

### 9. Configure automatic monitoring

Automatic scheduling uses a macOS LaunchAgent.

The scheduling setup is currently being tested and will be documented after the installation workflow is validated.

## Data and Privacy

Each user maintains their own:
- OpenClaw browser session
- Ollama model
- Email credentials
- Monitoring configuration
- Manuscript database
- Monitoring logs

Private data is stored locally in:

```text
~/.scholarone-monitor/
```

No manuscript data or email credentials should be uploaded to GitHub.

## Future Development

Planned improvements:
- Support for Editorial Manager and additional manuscript platforms.
- Support for Chrome and other browsers.
- A user-friendly installation and configuration interface.
- Support for additional local AI models.
- Easier installation and distribution.
- Update to use with other browsers.
