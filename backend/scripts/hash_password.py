import getpass
import secrets
import sys

import bcrypt


def main() -> int:
    pw = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm: ")
    if pw != confirm:
        print("passwords do not match", file=sys.stderr)
        return 1
    if len(pw) < 12:
        print("use at least 12 characters", file=sys.stderr)
        return 1
    hashed = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    session_secret = secrets.token_urlsafe(48)
    print()
    print("Add these to backend/.env:")
    print(f"ADMIN_PASSWORD_HASH={hashed}")
    print(f"SESSION_SECRET={session_secret}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
