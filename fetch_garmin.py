import os
import json
from datetime import datetime
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)

# Récupération des identifiants stockés dans les secrets GitHub
email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")
token_dir = os.path.expanduser("~/.garminconnect")

def init_garmin():
    """Initialise la connexion à Garmin Connect en réutilisant les tokens si possible."""
    try:
        # Essai de reconnexion via les tokens enregistrés
        garmin = Garmin()
        garmin.login(token_dir)
        print("Connexion réussie via les tokens de session.")
        return garmin
    except (FileNotFoundError, GarminConnectAuthenticationError):
        # Première connexion ou tokens expirés
        try:
            print("Connexion initiale avec e-mail et mot de passe...")
            garmin = Garmin(email, password)
            garmin.login()
            # Sauvegarde des tokens pour les prochaines exécutions
            garmin.garth.dump(token_dir)
            return garmin
        except (GarminConnectAuthenticationError, GarminConnectTooManyRequestsError) as e:
            print(f"Erreur d'authentification Garmin : {e}")
            raise

def main():
    if not email or not password:
        raise ValueError("Les variables d'environnement GARMIN_EMAIL et GARMIN_PASSWORD doivent être configurées.")

    garmin = init_garmin()

    # Date du jour (YYYY-MM-DD)
    today = datetime.now().strftime("%Y-%m-%d")

    print("Récupération des données...")

    # 1. Résumé quotidien (pas, calories, rythme cardiaque, etc.)
    try:
        stats = garmin.get_user_summary(today)
    except Exception as e:
        print(f"Impossible de récupérer le résumé quotidien : {e}")
        stats = {}

    # 2. Les 5 dernières activités enregistrées
    try:
        activities = garmin.get_activities(0, 5)
    except Exception as e:
        print(f"Impossible de récupérer les activités : {e}")
        activities = []

    # Structure JSON finale exportée
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

    # Écriture dans le fichier data.json
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("Fichier data.json généré avec succès !")

if __name__ == "__main__":
    main()
