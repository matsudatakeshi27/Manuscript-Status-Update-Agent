# ScholarOne Manuscript Status Monitor

A Python-based monitoring tool that automatically checks manuscript statuses in ScholarOne, detects status changes, and sends email notifications when a manuscript's status changes.

The goal is to make it easier for researchers to keep track of submitted manuscripts without manually logging into ScholarOne every day.

## 1. Current Status

| Platform | Support status |
|---|---|
| macOS | Tested and working |
| Windows | Experimental; implementation provided but not yet tested on a Windows machine |

The application currently supports these ScholarOne journals:

- **Marketing Science:** https://mc.manuscriptcentral.com/mksc
- **Journal of Marketing Research:** https://mc.manuscriptcentral.com/ama_jmr

Additional journals may be supported by adapting the journal configuration and checking their ScholarOne page structures.

## 2. How It Works

The monitoring process follows these steps:

1. **Open the ScholarOne browser session.** The application connects to an OpenClaw-controlled browser using Chrome DevTools Protocol (CDP).
2. **Log in to ScholarOne.** The application retrieves the saved username and password from the operating system's secure credential store.
3. **Retrieve manuscript information.** It checks the relevant ScholarOne manuscript queues and extracts manuscript IDs, titles, and current statuses.
4. **Compare with previous results.** The application compares the newly retrieved information with the locally stored manuscript database.
5. **Detect status changes.** If a manuscript's status differs from its previously recorded status, the application identifies the change.
6. **Send an email notification.** An email is sent only when an existing manuscript's status has changed.
7. **Save the latest results.** The database is updated so the next monitoring run can compare against the latest known statuses.

### Important monitoring behavior

- The first time a manuscript is discovered, its status is saved as the baseline. No notification is sent for this initial discovery.
- Notifications are sent only for subsequent status changes.
- If a manuscript has not changed status, no email is sent.
- Both journals are checked before the database is updated. If either journal's retrieval process fails, the application avoids updating the database with an incomplete set of results.
- Manuscripts are identified using both the journal and manuscript ID, so manuscripts from different journals are tracked separately.
- The application checks the required **Manuscripts with Decisions** queue and can also check **Submitted Manuscripts** and **Manuscripts I Have Co-Authored** when available.
- Optional queues that are unavailable are skipped. Unsubmitted and draft manuscripts are not monitored.

## 3. System Architecture and Dependencies

The project uses several tools that work together.

| Component | Purpose |
|---|---|
| Python | Runs the monitoring and comparison logic |
| OpenClaw | Manages the browser session used to access ScholarOne |
| Playwright | Controls and interacts with the browser through CDP |
| Brave or another supported browser | Displays the ScholarOne website |
| Python Keyring | Stores and retrieves ScholarOne credentials securely |
| Gmail SMTP | Sends email notifications |
| JSON | Stores manuscript statuses and monitoring configuration |
| macOS LaunchAgent / Windows Task Scheduler | Runs the monitoring process automatically |

### Does the application require an AI model?

The core monitoring process is Python-based. It does not need an AI model to compare manuscript statuses or decide whether to send notifications.

OpenClaw may use an AI model as part of its browser-agent configuration. For example, a local Ollama model such as Qwen3 8B can be used if configured in OpenClaw.

Ollama is therefore optional for the monitoring application itself. Whether it is needed depends on the OpenClaw configuration being used.

### Python dependencies

The external Python packages are listed in `requirements.txt`:

```text
python-dotenv>=1.0.0
platformdirs>=4.0.0
keyring>=25.0.0
playwright>=1.50.0
```

Other modules used by the application, such as `json`, `os`, `datetime`, and `smtplib`, are part of Python's standard library.

## 4. Project Structure

```text
scholarone-monitor/
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

**`monitor.py`**

The main entry point. It coordinates the monitoring process, retrieves browser results, compares manuscript statuses, updates the database, and sends email notifications when changes are detected.

**`auto_login.py`**

Retrieves ScholarOne credentials from the operating system's secure credential store and uses Playwright to log in to the appropriate journal website.

**`fetch_browser_results.py`**

Connects to the OpenClaw browser through CDP and retrieves manuscript information from ScholarOne.

**`paths.py`**

Defines the application's file locations. It uses `platformdirs` to store configuration, manuscript data, temporary browser results, and logs in an appropriate application-data directory for each operating system.

**`setup_credentials.py`**

Prompts the user for ScholarOne usernames and passwords and saves them securely using Python Keyring.

**`configure_schedule.py`**

Configures automatic monitoring on macOS using a LaunchAgent.

### Windows setup scripts

**`install_windows.ps1`**

Creates a Python virtual environment, installs the Python dependencies, initializes the application's private data directory, copies example configuration files when needed, and saves ScholarOne credentials.

**`configure_schedule_windows.ps1`**

Creates a Windows Scheduled Task to run the monitoring process at the configured interval.

These Windows scripts are experimental and have not yet been tested on a Windows machine.

## 5. Installation

### 5.1. Prerequisites

Before installing the Python application, install and configure:

1. **Python 3** — required to run the application.
2. **OpenClaw** — required to manage the browser session.
3. **A supported browser** — for example, Brave or Chromium.
4. **A Gmail account** — required if you want email notifications.

OpenClaw must be installed and configured separately. The installation scripts in this repository do not install OpenClaw.

The browser must be accessible through OpenClaw's CDP connection. The default CDP address is:

```text
http://127.0.0.1:18800
```

If your OpenClaw browser uses a different address, set the `OPENCLAW_CDP_URL` environment variable accordingly.

For example, on macOS:

```bash
export OPENCLAW_CDP_URL="http://127.0.0.1:18800"
```

For Windows PowerShell:

```powershell
$env:OPENCLAW_CDP_URL = "http://127.0.0.1:18800"
```

The examples above use the default address. You only need to change it if your OpenClaw configuration uses a different CDP endpoint.

---

### 5.2. macOS Installation

The following instructions describe the macOS setup that has been tested.

**Step 1. Clone the repository**

```bash
git clone https://github.com/matsudatakeshi27/Manuscript-Status-Update-Agent.git

cd Manuscript-Status-Update-Agent
```

**Step 2. Create a Python virtual environment**

```bash
python3 -m venv .venv

source .venv/bin/activate
```

A virtual environment keeps the project's Python dependencies separate from other Python projects on your computer.

**Step 3. Install dependencies**

```bash
python -m pip install --upgrade pip

pip install -r requirements.txt
```

**Step 4. Configure OpenClaw**

Install and configure OpenClaw separately.

Make sure that:

- OpenClaw is installed and available from the terminal.
- The browser integration is enabled.
- The browser can be started successfully.
- The CDP endpoint is accessible at `http://127.0.0.1:18800`, or at the address you configured.

For example, check the browser status using:

```bash
openclaw browser status
```

If necessary, start the browser:

```bash
openclaw browser start
```

The application connects to this browser session rather than launching an unrelated browser session.

**Step 5. Set up ScholarOne credentials**

Run:

```bash
python src/setup_credentials.py
```

The script asks for the username and password for each supported journal:

- Marketing Science
- Journal of Marketing Research

Credentials are saved using Python Keyring. On macOS, they are stored in the macOS Keychain rather than in the project directory or a plain-text credentials file.

You can run the script again if your ScholarOne password changes.

**Step 6. Configure email notifications**

The application uses Gmail SMTP to send notification emails.

The repository includes an example environment file:

```text
.env.example
```

The application stores its private configuration files in the operating system's application-data directory, not in the project directory.

On macOS, this directory is:

```text
~/Library/Application Support/ScholarOneMonitor/
```

Create the `.env` file in that directory. It should contain:

```text
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
NOTIFICATION_EMAIL=recipient@example.com
```

Replace the example values with your actual email information.

**Important:** Use a Gmail App Password rather than your regular Gmail account password. Gmail App Passwords require two-step verification to be enabled on the Google account.

Keep this file private. Do not commit it to GitHub.

You can restrict access to the file using:

```bash
chmod 600 "$HOME/Library/Application Support/ScholarOneMonitor/.env"
```

**Step 7. Configure monitoring settings**

The example configuration file is:

```text
config.example.json
```

The application uses a private `config.json` file in its application-data directory.

A typical configuration is:

```json
{
  "monitoring_interval_hours": 6,
  "notification_enabled": true
}
```

The `monitoring_interval_hours` setting determines how frequently the application runs automatically.

The `notification_enabled` setting controls whether email notifications are enabled.

If the private configuration file does not exist, copy the example file into the application-data directory and name it `config.json`.

**Step 8. Run the application manually**

From the project directory, run:

```bash
python src/monitor.py
```

Check the terminal output and log files to confirm that:

- OpenClaw is accessible.
- ScholarOne login works.
- Manuscript information is retrieved.
- The database is updated successfully.
- Email notifications work when a status change is detected.

The application writes logs to:

```text
~/Library/Application Support/ScholarOneMonitor/logs/
```

The main log is `monitor.log`; errors are recorded in `monitor_error.log`.

**Step 9. Configure automatic monitoring**

Once the manual run works, configure the macOS LaunchAgent:

```bash
python src/configure_schedule.py
```

The LaunchAgent runs the application automatically at the interval specified in `config.json`.

For example, if:

```json
{
  "monitoring_interval_hours": 6,
  "notification_enabled": true
}
```

the application is scheduled to run every six hours.

The LaunchAgent configuration is stored in the application's private data directory.

---

### 5.3. Windows Installation (Experimental)

**Windows support is experimental.** The installation and scheduling scripts have been written, but have not yet been tested on a Windows machine. Some setup steps or browser behaviors may require adjustment.

**Step 1. Install prerequisites**

Install:

- Python 3
- OpenClaw
- A supported browser
- Git

OpenClaw must be installed and configured separately before running the application.

Make sure the OpenClaw browser is working and its CDP endpoint is accessible.

**Step 2. Clone the repository**

Open PowerShell:

```powershell
git clone https://github.com/matsudatakeshi27/Manuscript-Status-Update-Agent.git

cd Manuscript-Status-Update-Agent
```

**Step 3. Run the Windows installation script**

Allow script execution for the current PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then run:

```powershell
.\install_windows.ps1
```

The script:

1. Finds the Python installation.
2. Creates a project-specific virtual environment.
3. Installs the required Python packages.
4. Installs Playwright Chromium.
5. Initializes the application's private data directory.
6. Copies example configuration files if they do not already exist.
7. Prompts for ScholarOne credentials and saves them through Python Keyring.

**Step 4. Configure email notifications**

The Windows application-data directory is:

```text
%LOCALAPPDATA%\ScholarOneMonitor\
```

The `.env` file should be located there.

For a typical Windows installation, this resolves to:

```text
C:\Users\YOUR_USERNAME\AppData\Local\ScholarOneMonitor\.env
```

Edit the file and provide:

```text
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
NOTIFICATION_EMAIL=recipient@example.com
```

Do not commit this file to GitHub.

**Step 5. Configure monitoring settings**

Edit:

```text
%LOCALAPPDATA%\ScholarOneMonitor\config.json
```

For example:

```json
{
  "monitoring_interval_hours": 6,
  "notification_enabled": true
}
```

**Step 6. Run the application manually**

Run:

```powershell
.\.venv\Scripts\python.exe src\monitor.py
```

Confirm that the browser connection, ScholarOne login, manuscript retrieval, database updates, and email notifications work before enabling automatic scheduling.

**Step 7. Configure automatic monitoring**

Run:

```powershell
.\configure_schedule_windows.ps1
```

The script creates a Windows Scheduled Task that runs at the configured interval.

The scheduled task is configured to run while the Windows user is logged in. This is important because the application needs access to the user's browser session and saved credentials.

Check the task in **Task Scheduler** under:

```text
Task Scheduler Library
```

The task name is:

```text
ScholarOne Manuscript Monitor
```

Because Windows support is experimental, verify the task's execution history and application logs after setup.

## 6. Private Data and File Storage

The application separates its code from private user data.

This is important because usernames, passwords, email settings, and manuscript information should not be stored in the GitHub repository.

The application uses `platformdirs` to determine the appropriate private data directory.

| File or directory | Purpose |
|---|---|
| `config.json` | Monitoring interval and notification settings |
| `.env` | Gmail SMTP configuration |
| `manuscripts.json` | Previously recorded manuscript information and statuses |
| `browser_results.json` | Latest retrieved browser results |
| `logs/monitor.log` | Main application log |
| `logs/monitor_error.log` | Error log |

### Data locations

**macOS**

```text
~/Library/Application Support/ScholarOneMonitor/
```

**Windows**

```text
%LOCALAPPDATA%\ScholarOneMonitor\
```

These directories are created automatically when the application initializes its paths.

### Credential storage

ScholarOne credentials are stored separately from the application-data files.

- macOS: credentials are stored in Keychain.
- Windows: Python Keyring uses the Windows credential backend, normally Windows Credential Manager.

This means the application does not need to save ScholarOne passwords in `config.json`, `.env`, or `manuscripts.json`.

## 7. Email Notifications

The application sends an email only when a previously recorded manuscript changes status.

For example:

```text
Subject: ScholarOne Manuscript Status Update

Manuscript: Example Manuscript
Journal: Marketing Science
Manuscript ID: MS-2026-001

Previous Status: Submitted
New Status: Under Review

Last Checked: 2026-11-13 10:00:00
```

The sender is the Gmail address configured in `GMAIL_ADDRESS`.

The recipient is the address configured in `NOTIFICATION_EMAIL`.

The application uses Gmail SMTP with STARTTLS on port 587.

The application does not send an email for every monitoring run. It sends notifications only when a genuine status change is detected.

## 8. Automatic Scheduling

The application supports automatic scheduling on both operating systems.

| Operating system | Scheduling mechanism |
|---|---|
| macOS | LaunchAgent |
| Windows | Windows Task Scheduler |

The monitoring interval is controlled by:

```json
{
  "monitoring_interval_hours": 6
}
```

The default example uses six hours, but the interval can be changed.

**Important:** The browser and OpenClaw must be available when the scheduled task runs. On Windows, the provided task is configured to run only while the user is logged in.

## 9. Troubleshooting

### OpenClaw browser connection fails

Check the browser status:

```bash
openclaw browser status
```

Start the browser if necessary:

```bash
openclaw browser start
```

Confirm that the CDP endpoint is accessible and matches the `OPENCLAW_CDP_URL` setting.

### ScholarOne login fails

Check that:

- The correct username and password were entered.
- The credentials are saved in the operating system's credential store.
- The journal's login page is accessible.
- The browser is not displaying an unexpected authentication or security prompt.

If credentials have changed, run:

```bash
python src/setup_credentials.py
```

### No manuscripts are found

The application retrieves manuscripts from the configured ScholarOne queues.

If no manuscripts are found, check the ScholarOne dashboard manually to confirm that the account contains manuscripts in the supported queues.

An empty dashboard is a valid result and does not necessarily indicate an application error.

### No email notification is received

Check:

- The Gmail address in `.env`.
- The Gmail App Password.
- The recipient address.
- Whether `notification_enabled` is set to `true`.
- The application logs for SMTP errors.

Also remember that the first time a manuscript is discovered, its status is saved as a baseline. An email is not sent for this initial discovery.

### Scheduled monitoring does not run

On macOS, check the LaunchAgent status and application logs.

On Windows, open Task Scheduler and inspect the task's Last Run Time, Last Run Result, and History.

The application logs are stored in the private application-data directory described above.

## 10. Privacy and Security

The application handles ScholarOne credentials, email configuration, and manuscript information.

The following precautions are used:

- ScholarOne passwords are stored through the operating system's credential manager.
- Gmail settings are stored in a private `.env` file.
- Manuscript data and logs are stored outside the GitHub project directory.
- Sensitive configuration files should not be committed to GitHub.
- The `.gitignore` file excludes environment files, Python cache files, and local browser data.

Before pushing changes to GitHub, check:

```bash
git status --short
```

Make sure that `.env`, private configuration files, manuscript databases, browser data, and credentials are not included in the commit.

## 11. Limitations and Future Improvements

Current limitations include:

- Only Marketing Science and Journal of Marketing Research are configured.
- ScholarOne page changes may require updates to the browser retrieval logic.
- The application depends on OpenClaw and an accessible browser session.
- Windows support has not yet been tested on a Windows machine.
- Gmail SMTP is the current email delivery method.

Potential future improvements include:

- Adding support for more ScholarOne journals.
- Providing a graphical interface for setup and monitoring.
- Making notification emails more customizable.
- Adding more robust error recovery and monitoring reports.
- Testing and validating Windows support on different Windows configurations.

## 12. Repository

GitHub:

https://github.com/matsudatakeshi27/Manuscript-Status-Update-Agent.git

Contributions, bug reports, and suggestions are welcome.
