
import getpass
import keyring

JOURNALS = {
    "Marketing Science": "marketingscience-monitor",
    "Management Science": "managementscience-monitor",
    "Journal of Marketing Research": "jmr-monitor",
    "Journal of Marketing": "journalofmarketing-monitor",
    "Journal of Consumer Research": "jconres-monitor",
    "Information Systems Research": "isr-monitor",
    "International Journal of Research in Marketing": "ijrm-monitor",
    "Production and Operations Management": "poms-monitor",
}

print("\nAvailable journals:")
for i, journal in enumerate(JOURNALS, 1):
    print(f"{i}. {journal}")

choice = input(
    "\nEnter journal number (or press Enter to skip): "
).strip()

if not choice:
    print("Skipped. No credentials changed.")
    raise SystemExit(0)

try:
    journal = list(JOURNALS.keys())[int(choice) - 1]
except (ValueError, IndexError):
    raise SystemExit("Invalid journal selection.")

service = JOURNALS[journal]

username = input(f"ScholarOne username for {journal}: ").strip()
password = getpass.getpass("ScholarOne password: ")

if not username or not password:
    raise SystemExit("Username and password cannot be empty.")

keyring.set_password(service, "username", username)
keyring.set_password(service, "password", password)

print(f"\nCredentials saved securely for {journal}.")
