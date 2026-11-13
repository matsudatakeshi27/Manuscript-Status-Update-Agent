# Manuscript Status Update Agent

An experimental local application that monitors manuscript submission statuses and sends email notifications when a manuscript's status changes.

The application uses **OpenClaw for browser automation**, **Playwright for browser interaction**, and **Ollama for locally hosted AI models**. It is designed to run on users' own computers without requiring a paid AI API subscription.

## Overview

The application helps researchers avoid manually checking manuscript submission websites.

Features:

- Automatically starts and connects to the OpenClaw-controlled browser.
- Opens the relevant ScholarOne websites.
- Automatically logs into ScholarOne using credentials stored securely in macOS Keychain.
- Supports multiple journals, each with its own login credentials.
- Navigates to the Author Dashboard.
- Retrieves manuscripts from multiple available dashboard queues.
- Tracks manuscript IDs, titles, journals, and statuses.
- Detects changes in manuscript status.
- Sends email notifications when an existing manuscript's status changes.
- Allows users to configure their own monitoring interval.
- Runs automatically in the background using macOS LaunchAgent.
- Stores credentials and monitoring data locally.

## Current Status

This is an experimental prototype.

Currently supported:

- Operating system: macOS
- Manuscript platform: ScholarOne
- Supported journals:
  - Marketing Science
  - Journal of Marketing Research
- Browser automation: OpenClaw
- Browser interaction: Playwright
- Local AI models: Ollama
- Tested model: Qwen3 8B (`qwen3:8b`)
- Browser: Brave on macOS
- Email notifications: Gmail SMTP
- Scheduling: macOS LaunchAgent

The application has been tested with two ScholarOne journals on the developer's computer. It has not yet been fully tested on another computer.

## Supported Journals and Manuscript Queues

| Journal | ScholarOne URL |
|---|---|
| Marketing Science | https://mc.manuscriptcentral.com/mksc |
| Journal of Marketing Research | https://mc.manuscriptcentral.com/ama_jmr |

For each journal, the application checks the following Author Dashboard queues:

1. **Manuscripts with Decisions** — required queue.
2. **Submitted Manuscripts** — checked when available.
3. **Manuscripts I Have Co-Authored** — checked when available.

Optional queues are skipped if they are not available in a particular journal account.

Manuscripts are deduplicated by manuscript ID within each journal. The same manuscript ID in different journals is treated as a separate record.

The application currently does not monitor **Unsubmitted and Manuscripts in Draft**.

## Requirements

Users need to install:

1. **Python** — runs the monitoring application.
2. **OpenClaw** — manages the browser.
3. **Playwright** — interacts with the browser.
4. **Ollama** — runs the AI model locally when required by the OpenClaw configuration.
5. **A supported browser** — currently tested with Brave on macOS.
6. **A Gmail account** — used to send email notifications.

No paid AI API subscription is required when using Ollama.

Note: The manuscript scraping and status-comparison workflow is implemented in Python. Ollama is used as the locally hosted model configured for OpenClaw; the monitoring script does not need to invoke an AI model for every status comparison.

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

Make sure OpenClaw's browser functionality is enabled.

The application connects to the OpenClaw-controlled browser through its Chrome DevTools Protocol (CDP) endpoint:

```text
http://127.0.0.1:18800
```

Check browser status:

```bash
openclaw browser status
```

The monitoring application can start the OpenClaw browser automatically. Users should not need to open Brave manually before running the monitor.

### 5. Configure ScholarOne login credentials

The application stores ScholarOne credentials in macOS Keychain rather than in project files.

From the project directory, run:

```bash
python3 src/setup_credentials.py
```

Follow the prompts to enter the username and password for each supported journal.

The current implementation uses separate Keychain services:

| Journal | Keychain service |
|---|---|
| Marketing Science | `marketingscience-monitor` |
| Journal of Marketing Research | `jmr-monitor` |

The password is entered interactively and is not stored in the project directory.

**Important:** Each user must configure their own ScholarOne credentials for every journal they want to monitor. Never share credentials or commit them to GitHub.

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
- `GMAIL_APP_PASSWORD`: The 16-character Google App Password generated above. Do not use your regular Gmail password.
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
python3 -u src/monitor.py
```

The application automatically:

1. Connects to the OpenClaw-controlled browser.
2. Starts the browser if necessary.
3. Opens the relevant ScholarOne journal websites.
4. Checks whether the user is already logged in.
5. Logs in using credentials stored in macOS Keychain if necessary.
6. Navigates to each journal's Author Dashboard.
7. Retrieves available manuscript queues.
8. Combines and deduplicates the manuscript records.
9. Compares current statuses against previously recorded statuses.
10. Sends an email notification if an existing manuscript's status has changed.

The monitor processes both journals before updating the manuscript database. If retrieving results from either journal fails, it should not proceed with a partial two-journal update.

The first time a manuscript is recorded, it becomes the baseline. No notification is sent for a newly discovered manuscript. Notifications are sent for subsequent status changes.

**Note:** If ScholarOne requires CAPTCHA, multi-factor authentication, or additional verification, the user may need to complete that step manually.

#### Test automatic login separately

Users can also test browser startup and login functionality independently:

```bash
python3 src/auto_login.py
```

The login automation supports the two configured journals. The monitoring workflow invokes it separately for each journal.

### 9. Configure automatic monitoring

Automatic scheduling uses a macOS LaunchAgent.

The current local implementation is configured to run the monitoring script every six hours.

A LaunchAgent runs the monitoring script periodically while the Mac is powered on and available. The OpenClaw browser must also be accessible.

To check whether the scheduled job is loaded:

```bash
launchctl list | grep -i scholarone
```

To run the monitor manually at any time:

```bash
python3 -u src/monitor.py
```

**Important:** The LaunchAgent setup has been tested on the developer's Mac. Automatic LaunchAgent installation and configuration for new users still need further development and testing.

## Data and Privacy

Each user maintains their own:

- OpenClaw browser session
- ScholarOne login credentials
- Ollama model
- Email credentials
- Monitoring configuration
- Manuscript database
- Browser results
- Monitoring logs

Private data is stored locally in:

```text
~/.scholarone-monitor/
```

Typical files include:

```text
~/.scholarone-monitor/
├── .env
├── config.json
├── manuscripts.json
├── browser_results.json
└── logs/
```

ScholarOne credentials are stored in macOS Keychain.

Email credentials are stored in a private `.env` file.

Manuscript records and monitoring results are stored locally.

No manuscript data, login credentials, or email credentials should be uploaded to GitHub.

## Troubleshooting

### OpenClaw browser is unavailable

Check the browser status:

```bash
openclaw browser status
```

Start the browser:

```bash
openclaw browser start
```

### Login fails

Check that the correct credentials have been configured in macOS Keychain for each journal. Complete any required CAPTCHA or additional verification manually.

### Email notifications are not received

Check the following:

- Gmail address is correct.
- Google App Password is correct.
- Recipient email address is correct.
- Gmail SMTP authentication is working.
- The manuscript's status actually changed.

The application sends notifications for status changes, not for every monitoring run.

### Scheduled monitoring does not run

Check whether the LaunchAgent is loaded:

```bash
launchctl list | grep -i scholarone
```

Make sure the Mac is powered on and the scheduled process has access to the project and browser.

## Future Development

Planned improvements:

- Support for Editorial Manager and additional manuscript platforms.
- Support for Chrome and other browsers.
- A user-friendly installation and configuration interface.
- Support for additional local AI models.
- Easier installation and distribution.
- Simplified LaunchAgent installation for new users.
- A more general-purpose manuscript monitoring application for researchers using different submission systems.
