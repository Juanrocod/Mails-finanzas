"""
Genera links de registro o reset de contraseña.

Uso:
  python create_invite.py invite
  python create_invite.py reset --username <username>
"""
import argparse
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.models.invite_token import InviteToken
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera invite/reset tokens")
    parser.add_argument("tipo", choices=["invite", "reset"])
    parser.add_argument("--username", help="Username existente (requerido para reset)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user_id = None
        if args.tipo == "reset":
            if not args.username:
                print("Error: --username requerido para tipo 'reset'")
                sys.exit(1)
            user = db.query(User).filter(User.username == args.username).first()
            if not user:
                print(f"Error: usuario '{args.username}' no encontrado en DB")
                sys.exit(1)
            user_id = user.id

        token_value = secrets.token_urlsafe(32)
        expira_en = datetime.now(timezone.utc) + timedelta(hours=48)

        row = InviteToken(
            token=token_value,
            tipo=args.tipo,
            user_id=user_id,
            expira_en=expira_en,
        )
        db.add(row)
        db.commit()

        base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        if args.tipo == "invite":
            url = f"{base_url}/register?token={token_value}"
            print(f"\nLink de registro (valido 48hs):\n  {url}\n")
        else:
            url = f"{base_url}/reset-password?token={token_value}"
            print(f"\nLink de reset para '{args.username}' (valido 48hs):\n  {url}\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
