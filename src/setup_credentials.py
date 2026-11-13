import getpass
import keyring

SERVICE = "marketingscience-monitor"

username = input("ScholarOne username: ").strip()
password = getpass.getpass("ScholarOne password: ")

if not username or not password:
    raise SystemExit("Username and password cannot be empty.")

keyring.set_password(SERVICE, "username", username)
keyring.set_password(SERVICE, "password", password)

print("ScholarOne credentials saved securely in macOS Keychain.")
