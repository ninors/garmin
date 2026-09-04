import os
import json
from datetime import datetime
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")
token_dir = os.path.expanduser("~/.garminconnect")

def init_garmin():
    """Initialise la connexion à Garmin Connect."""
    if not email or not password:
        raise ValueError("Les variables d'environnement GARMIN_EMAIL et GARMIN_PASSWORD doivent être configurées.")

    garmin = Garmin(email, password)

    # 1. Tentative de connexion via les tokens existants
    if os.path.exists(token_dir):
        try:
            print("Tentative de connexion avec les tokens enregistrés...")
            garmin.login(token_dir)
            print("Connexion réussie via les tokens.")
            return garmin
        except Exception as e:
            print(f"Échec de connexion avec les tokens : {e}. Tentative avec identifiants...")

    # 2. Connexion initiale avec identifiants
    try:
        print("Connexion initiale avec e-mail et mot de passe...")
        garmin.login()
        # Enregistre les nouveaux tokens
        os.makedirs(token_dir, exist_ok=True)
        garmin.login(token_dir)
        print("Nouveaux tokens enregistrés.")
        return garmin
    except (GarminConnectAuthenticationError, GarminConnectTooManyRequestsError) as e:
        print(f"Erreur lors de la connexion Garmin : {e}")
        raise

def main():
    garmin = init_garmin()

    today = datetime.now().strftime("%Y-%m-%d")

    print("Récupération des données...")

    # Résumé quotidien
    try:
        stats = garmin.get_user_summary(today)
    except Exception as e:
        print(f"Impossible de récupérer le résumé quotidien : {e}")
        stats = {}

    # Dernières activités
    try:
        activities = garmin.get_activities(0, 5)
    except Exception as e:
        print(f"Impossible de récupérer les activités : {e}")
        activities = []

    # Structure JSON finale
    output_data = {
        "updated_at": datetime.now().isoformat(),
        "today_summary": {
            "steps": stats.get("totalSteps", 0),
            "step_goal": stats.get("userDailyStepGoal", 0),
            "calories_total": stats.get("totalKilocalories", 0),
            "calories_active": stats.get("activeKilocalories", 0),
            "resting_heart_rate": stats.get("restingHeartRate", 0),
            "floors_climbed": stats.get("floorsClimbed", 0)
        },
        "recent_activities": [
            {
                "id": act.get("activityId"),
                "name": act.get("activityName"),
                "type": act.get("activityType", {}).get("typeKey"),
                "start_time": act.get("startTimeLocal"),
                "distance_meters": act.get("distance"),
                "duration_seconds": act.get("duration"),
                "average_hr": act.get("averageHR"),
                "max_hr": act.get("maxHR"),
                "calories": act.get("calories")
            }
            for act in activities
        ]
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("Fichier data.json généré avec succès !")

if __name__ == "__main__":
    main()
