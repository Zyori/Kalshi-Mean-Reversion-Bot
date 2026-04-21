import getpass
import os
import secrets
import sys

import bcrypt


def _read_password() -> str:
    env_pw = os.environ.get("ADMIN_PASSWORD")
    if env_pw is not None:
        return env_pw
    if not sys.stdin.isatty():
        pw = sys.stdin.readline().rstrip("\n")
        return pw
    pw = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm: ")
    if pw != confirm:
        print("passwords do not match", file=sys.stderr)
        sys.exit(1)
    return pw


def main() -> int:
    pw = _read_password()
    if not pw:
        print("password cannot be empty", file=sys.stderr)
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
