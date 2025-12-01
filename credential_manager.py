import json
import os
from getpass import getpass
from tools.utils import log


CRED_FILE = "qa_agent_user_creds.json"


def interactive_setup():
    """Force interactive username + password input. Always asks."""
    log("Interactive credential setup activated.")

    username = input("Enter username: ").strip()
    password = getpass("Enter password: ").strip()

    confirm = input("Save these credentials? (y/n): ").strip().lower()
    if confirm == "y":
        save_credentials(username, password)
        log("Credentials saved.")
    else:
        log("Credentials not saved.")


def save_credentials(username: str, password: str):
    with open(CRED_FILE, "w") as f:
        json.dump({"username": username, "password": password}, f, indent=2)


def load_credentials():
    if not os.path.exists(CRED_FILE):
        raise FileNotFoundError("Credential file not found. Run interactive setup.")

    with open(CRED_FILE, "r") as f:
        return json.load(f)


def get_credentials():
    """Used by the test runner. Will only read, not ask."""
    return load_credentials()


if __name__ == "__main__":
    # ALWAYS runs interactive setup when called directly
    interactive_setup()
