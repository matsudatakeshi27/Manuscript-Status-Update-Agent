# ScholarOne Manuscript Status Monitor

An agent that automatically checks manuscript statuses in ScholarOne, detects status changes, and sends email notifications when a manuscript's status changes.

## 1. Current Status

| Platform | Support status                                                                |
| -------- | ----------------------------------------------------------------------------- |
| macOS    | Tested and working                                                            |
| Windows  | Experimental; implementation provided but not yet tested on a Windows machine |

**Supported journals**

- [Marketing Science](https://mc.manuscriptcentral.com/mksc)
- [Journal of Marketing Research](https://mc.manuscriptcentral.com/ama_jmr)

Additional journals may be supported by adapting the journal configuration and browser retrieval logic.

## 2. How It Works

The application follows these steps:

1. Connects to an OpenClaw-controlled browser using Chrome DevTools Protocol (CDP).
2. Logs in to ScholarOne using credentials stored securely by the operating system.
3. Retrieves manuscript IDs, titles, and current statuses.
4. Compares current results with the locally stored manuscript database.
5. Detects changes in manuscript statuses.
6. Sends an email notification when an existing manuscript's status changes.
7. Saves the latest results for the next monitoring run.

**Important monitoring behavior**

- The first discovery of a manuscript establishes its baseline status. No notification is sent at that point.
- Emails are sent only when an existing manuscript's status changes.
- Both journals are checked before the database is updated. If either retrieval process fails, the application avoids updating the database with incomplete results.
- Manuscripts are identified using both journal and manuscript ID.
- The application checks the required **Manuscripts with Decisions** queue and can also check **Submitted Manuscripts** and **Manuscripts I Have Co-Authored** when available.
- Unavailable optional queues are skipped. Unsubmitted and draft manuscripts are not monitored.

## 3. System Architecture and Dependencies

| Component                            | Purpose                                  |
| ------------------------------------ | ---------------------------------------- |
| Python                               | Monitoring and status-comparison logic   |
| OpenClaw                             | Manages the browser session              |
| Playwright                           | Browser interaction through CDP          |
| Brave or another supported browser   | Displays ScholarOne                      |
| Python Keyring                       | Secure credential storage                |
| Gmail SMTP                           | Email notifications                      |
| JSON                                 | Stores manuscript data and configuration |
| LaunchAgent / Windows Task Scheduler | Automatic monitoring                     |

### AI model requirements

The core monitoring process is Python-based and does not require an AI model to compare statuses or send notifications.

OpenClaw may use an AI model for its browser-agent configuration. For example, a local Ollama model such as Qwen3 8B can be used if configured in OpenClaw.

Ollama is optional for the monitoring application itself.

- [Download Ollama](https://ollama.com/download)
- [Browse available models](https://ollama.com/library)

Example:

```bash
ollama pull qwen3:8b
```

### Python dependencies

The external packages are listed in `requirements.txt`:

```text
python-dotenv>=1.0.0
platformdirs>=4.0.0
keyring>=25.0.0
playwright>=1.50.0
```

Other modules, such as `json`, `os`, `datetime`, and `smtplib`, are included in Python's standard library.

## 4. Project Structure

```text
Manuscript-Status-Update-Agent/
│
├── src/
│   ├── auto_login.py
│   ├── configure_schedule.py
│   ├── fetch_browser_results.py
│   ├── monitor.py
│   ├── paths.py
│   └── setup_credentials.py
│
├── requirements.txt
├── config.example.json
├── .env.example
├── install_windows.ps1
├── configure_schedule_windows.ps1
├── .gitignore
└── README.md
```

### Main Python files

| File                       | Description                                                                                                       |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `monitor.py`               | Main entry point. Coordinates manuscript retrieval, status comparison, database updates, and email notifications. |
| `auto_login.py`            | Retrieves saved ScholarOne credentials and logs in using Playwright.                                              |
| `fetch_browser_results.py` | Connects to the OpenClaw browser through CDP and retrieves manuscript information.                                |
| `paths.py`                 | Defines application-data and log locations using `platformdirs`.                                                  |
| `setup_credentials.py`     | Prompts for ScholarOne credentials and saves them using Python Keyring.                                           |
| `configure_schedule.py`    | Configures automatic monitoring on macOS using LaunchAgent.                                                       |

### Configuration and setup files

| File                             | Description                                                                  |
| -------------------------------- | ---------------------------------------------------------------------------- |
| `requirements.txt`               | Lists required Python packages.                                              |
| `config.example.json`            | Example monitoring configuration.                                            |
| `.env.example`                   | Template for Gmail SMTP settings.                                            |
| `.gitignore`                     | Prevents private files and unnecessary files from being committed to GitHub. |
| `install_windows.ps1`            | Installs Python dependencies and initializes the application on Windows.     |
| `configure_schedule_windows.ps1` | Creates a Windows Scheduled Task.                                            |

The Windows scripts are experimental and have not yet been tested on a Windows machine.

## 5. Installation

### 5.1. Prerequisites

Install the following before setting up the application:

| Software / Account         | Purpose                               | Official link                                                                                  |
| -------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Python 3                   | Runs the application                  | [Download Python](https://www.python.org/downloads/)                                           |
| Git                        | Downloads the project                 | [Download Git](https://git-scm.com/downloads)                                                  |
| OpenClaw                   | Manages the browser session           | [Installation guide](https://docs.openclaw.ai/install)                                         |
| Brave Browser              | Browser used with OpenClaw            | [Download Brave](https://brave.com/download/)                                                  |
| Gmail                      | Sends email notifications             | [Create a Google account](https://accounts.google.com/signup)                                  |
| Google 2-Step Verification | Required for Gmail App Passwords      | [Enable 2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification) |
| Gmail App Password         | Allows the application to send emails | [Create an App Password](https://myaccount.google.com/apppasswords)                            |

OpenClaw must be installed and configured separately. The project installation scripts do not install OpenClaw.

**Install OpenClaw**

macOS — open Terminal:

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

Windows — open PowerShell:

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

Follow the OpenClaw onboarding instructions to complete the initial configuration.

Official documentation: [OpenClaw](https://docs.openclaw.ai/)

**Configure the browser connection**

The default CDP address is:

```text
http://127.0.0.1:18800
```

If your OpenClaw browser uses a different address, set `OPENCLAW_CDP_URL`.

macOS:

```bash
export OPENCLAW_CDP_URL="http://127.0.0.1:18800"
```

Windows PowerShell:

```powershell
$env:OPENCLAW_CDP_URL = "http://127.0.0.1:18800"
```

These commands use the default address; change it only if your configuration requires a different endpoint.

---

### 5.2. macOS Installation

These instructions describe the tested macOS setup.

**Step 1. Clone the repository**

```bash
git clone https://github.com/matsudatakeshi27/Manuscript-Status-Update-Agent.git

cd Manuscript-Status-Update-Agent
```

**Step 2. Create a Python virtual environment**

```bash
python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

pip install -r requirements.txt
```

**Step 3. Check OpenClaw**

```bash
openclaw browser status
```

If necessary, start the browser:

```bash
openclaw browser start
```

**Step 4. Set up ScholarOne credentials**

```bash
python src/setup_credentials.py
```

Enter your username and password for each supported journal.

Credentials are saved using Python Keyring in macOS Keychain.

**Step 5. Configure Gmail notifications**

First, enable [Google 2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification).

Then create a [Gmail App Password](https://myaccount.google.com/apppasswords).

Google's [App Password instructions](https://support.google.com/accounts/answer/185833) explain eligibility and troubleshooting. App Passwords may not be available for some managed accounts or security configurations.

Initialize the private application-data directory:

```bash
python -c "from src.paths import DATA_DIR; print(DATA_DIR)"
```

On macOS, the directory is:

```text
~/Library/Application Support/ScholarOneMonitor/
```

Copy the example environment file:

```bash
cp .env.example "$HOME/Library/Application Support/ScholarOneMonitor/.env"
```

Open it:

```bash
open -e "$HOME/Library/Application Support/ScholarOneMonitor/.env"
```

Enter your Gmail information:

```text
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=recipient@example.com
```

Save the file and restrict its permissions:

```bash
chmod 600 "$HOME/Library/Application Support/ScholarOneMonitor/.env"
```

**Step 6. Configure monitoring settings**

Copy the example configuration:

```bash
cp config.example.json "$HOME/Library/Application Support/ScholarOneMonitor/config.json"
```

Open it:

```bash
open -e "$HOME/Library/Application Support/ScholarOneMonitor/config.json"
```

Example:

```json
{
  "monitoring_interval_hours": 6,
  "notification_enabled": true
}
```

The example configures monitoring every six hours.

**Step 7. Run the application manually**

```bash
python src/monitor.py
```

Confirm that:

- OpenClaw is accessible.
- ScholarOne login works.
- Manuscript information is retrieved.
- The database is updated successfully.
- Email notifications work when a status change is detected.

Logs are saved in:

```text
~/Library/Application Support/ScholarOneMonitor/logs/
```

**Step 8. Enable automatic monitoring**

After confirming that a manual run works:

```bash
python src/configure_schedule.py
```

This creates a macOS LaunchAgent that runs the application automatically at the interval specified in `config.json`.

---

### 5.3. Windows Installation (Experimental)

**Windows support is experimental and has not yet been tested on a Windows machine.**

**Step 1. Install prerequisites**

Install Python 3, Git, OpenClaw, and a supported browser using the links in Section 5.1.

Configure OpenClaw separately and make sure its browser is working.

**Step 2. Clone the repository**

Open PowerShell:

```powershell
git clone https://github.com/matsudatakeshi27/Manuscript-Status-Update-Agent.git

cd Manuscript-Status-Update-Agent
```

**Step 3. Run the installation script**

Allow script execution for the current PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Run the installer:

```powershell
.\install_windows.ps1
```

The script:

1. Finds Python.
2. Creates a virtual environment.
3. Installs Python dependencies.
4. Installs Playwright Chromium.
5. Initializes the private data directory.
6. Copies example configuration files if needed.
7. Prompts for ScholarOne credentials and saves them through Python Keyring.

**Step 4. Configure Gmail notifications**

Enable [Google 2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification) and create a [Gmail App Password](https://myaccount.google.com/apppasswords).

Open the environment file:

```powershell
notepad "$env:LOCALAPPDATA\ScholarOneMonitor\.env"
```

Enter:

```text
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=recipient@example.com
```

Save the file.

**Step 5. Configure monitoring settings**

Open:

```powershell
notepad "$env:LOCALAPPDATA\ScholarOneMonitor\config.json"
```

Example:

```json
{
  "monitoring_interval_hours": 6,
  "notification_enabled": true
}
```

**Step 6. Run the application manually**

```powershell
.\.venv\Scripts\python.exe src\monitor.py
```

Confirm that login, manuscript retrieval, database updates, and email notifications work.

**Step 7. Enable automatic monitoring**

```powershell
.\configure_schedule_windows.ps1
```

This creates a Windows Scheduled Task named:

```text
ScholarOne Manuscript Monitor
```

The task is configured to run while the Windows user is logged in, allowing access to the browser session and saved credentials.

Check its execution history in Windows Task Scheduler.

## 6. Private Data and File Storage

The application separates its code from private user data. Configuration, manuscript information, and logs are stored outside the GitHub repository.

| File or directory        | Purpose                                       |
| ------------------------ | --------------------------------------------- |
| `config.json`            | Monitoring interval and notification settings |
| `.env`                   | Gmail SMTP configuration                      |
| `manuscripts.json`       | Previously recorded manuscript statuses       |
| `browser_results.json`   | Latest retrieved browser results              |
| `logs/monitor.log`       | Main application log                          |
| `logs/monitor_error.log` | Error log                                     |

**macOS**

```text
~/Library/Application Support/ScholarOneMonitor/
```

**Windows**

```text
%LOCALAPPDATA%\ScholarOneMonitor\
```

These directories are created automatically by `paths.py`.

ScholarOne credentials are stored separately:

- macOS: Keychain.
- Windows: Windows Credential Manager through Python Keyring.

## 7. Email Notifications

The application sends an email only when a previously recorded manuscript changes status.

Example:

```text
Subject: ScholarOne Manuscript Status Update

Manuscript: Example Manuscript
Journal: Marketing Science
Manuscript ID: MS-2026-001

Previous Status: Submitted
New Status: Under Review

Last Checked: 2026-11-13 10:00:00
```

The sender is configured through `GMAIL_ADDRESS`; the recipient is configured through `NOTIFICATION_EMAIL`.

The application uses Gmail SMTP with STARTTLS on port 587. It does not send an email for every monitoring run.

## 8. Automatic Scheduling

| Operating system | Scheduling mechanism   |
| ---------------- | ---------------------- |
| macOS            | LaunchAgent            |
| Windows          | Windows Task Scheduler |

The monitoring interval is controlled by:

```json
{
  "monitoring_interval_hours": 6,
  "notification_enabled": true
}
```

The browser and OpenClaw must be available when the scheduled task runs. On Windows, the task is configured to run while the user is logged in.

## 9. Troubleshooting

**OpenClaw browser connection fails**

```bash
openclaw browser status
openclaw browser start
```

Check that the CDP endpoint matches `OPENCLAW_CDP_URL`.

**ScholarOne login fails**

Run the credential setup script again.

macOS:

```bash
python src/setup_credentials.py
```

Windows:

```powershell
.\.venv\Scripts\python.exe src\setup_credentials.py
```

**No manuscripts are found**

Check the ScholarOne dashboard manually. An empty dashboard is a valid result.

**No email is received**

Check the Gmail address, App Password, recipient address, and `notification_enabled` setting. Remember that no email is sent when a manuscript is first discovered.

**Scheduled monitoring does not run**

Check the LaunchAgent on macOS or task history in Windows Task Scheduler. Also inspect the application's error log.

## 10. Privacy, Security, and Limitations

- ScholarOne passwords are stored through the operating system's credential manager.
- Gmail settings are stored in a private `.env` file.
- Manuscript data and logs are stored outside the project directory.
- Never commit `.env`, private configuration files, manuscript databases, or credentials to GitHub.
- The `.gitignore` file excludes environment files, Python cache files, and local browser data.
- Only Marketing Science and Journal of Marketing Research are currently configured.
- ScholarOne website changes may require updates to the retrieval logic.
- OpenClaw and an accessible browser session are required.
- Windows support is experimental and needs testing.

Before pushing changes to GitHub, check:

```bash
git status --short
```

## Repository

[GitHub: Manuscript Status Update Agent](https://github.com/matsudatakeshi27/Manuscript-Status-Update-Agent)
