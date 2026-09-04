#!/usr/bin/env python3
"""
Générateur local de Tokens Garmin Connect (Solution anti-429 Rate Limit)
Exécutez ce script sur votre ordinateur une seule fois pour générer une clé de session GARMIN_TOKENS.
"""

import os
import sys
import base64
import io
import zipfile
from pathlib import Path

try:
    from garminconnect import Garmin
except ImportError:
    print("Veuillez installer garminconnect: pip install garminconnect garth")
    sys.exit(1)

TOKEN_DIR = Path(".garminconnect")

def main():
    print("=== Générateur de Tokens Garmin Connect (Anti-429) ===")
    email = os.environ.get("GARMIN_EMAIL") or input("Email Garmin : ").strip()
    password = os.environ.get("GARMIN_PASSWORD") or input("Mot de passe Garmin : ").strip()

    if not email or not password:
        print("Erreur : Email et mot de passe requis.")
        sys.exit(1)

    print(f"\nConnexion à Garmin Connect depuis votre IP locale...")
    try:
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        garmin = Garmin(email, password)
        garmin.login(str(TOKEN_DIR))
        
        # Securité de sauvegarde du dossier token
        if hasattr(garmin, "garth") and garmin.garth:
            try:
                garmin.garth.dump(str(TOKEN_DIR))
            except Exception:
                pass
        elif hasattr(garmin, "dump"):
            try:
                garmin.dump(str(TOKEN_DIR))
            except Exception:
                pass

        print("✓ Connexion réussie ! Tokens générés dans le dossier .garminconnect")

        # Compression du dossier .garminconnect en base64 pour GitHub Secrets
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in TOKEN_DIR.rglob("*"):
                if file_path.is_file():
                    zip_file.write(file_path, file_path.relative_to(TOKEN_DIR))

        b64_tokens = base64.b64encode(buffer.getvalue()).decode("utf-8")

        print("\n=======================================================")
        print("COPIEZ LA CLÉ CI-DESSOUS DANS VOS SECRETS GITHUB :")
        print("Nom du Secret : GARMIN_TOKENS")
        print("=======================================================\n")
        print(b64_tokens)
        print("\n=======================================================")

    except Exception as e:
        print(f"Erreur de connexion : {e}")

if __name__ == "__main__":
    main()
