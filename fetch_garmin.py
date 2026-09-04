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

    if os.path.exists(token_dir):
        try:
            print("Tentative de connexion avec les tokens enregistrés...")
            garmin.login(token_dir)
            print("Connexion réussie via les tokens.")
            return garmin
        except Exception as e:
            print(f"Échec de connexion avec les tokens : {e}. Connexion via identifiants...")

    try:
        print("Connexion initiale avec e-mail et mot de passe...")
        garmin.login()
        os.makedirs(token_dir, exist_ok=True)
        garmin.login(token_dir)
        print("Nouveaux tokens enregistrés.")
        return garmin
    except (GarminConnectAuthenticationError, GarminConnectTooManyRequestsError) as e:
        print(f"Erreur lors de la connexion Garmin : {e}")
        raise

def download_gpx_files(garmin, activities):
    """Télécharge les fichiers GPX des activités récentes."""
    os.makedirs("gpx", exist_ok=True)
    for act in activities:
        act_id = act.get("activityId")
        if not act_id:
            continue
        gpx_filename = f"gpx/activity_{act_id}.gpx"
        if not os.path.exists(gpx_filename):
            try:
                print(f"Téléchargement du GPX pour l'activité {act_id}...")
                gpx_data = garmin.download_activity(act_id, dl_fmt=Garmin.ActivityDownloadFormat.GPX)
                with open(gpx_filename, "wb") as f:
                    f.write(gpx_data)
            except Exception as e:
                print(f"Impossible de télécharger le GPX pour {act_id} : {e}")

def main():
    garmin = init_garmin()
    today = datetime.now().strftime("%Y-%m-%d")

    print("Récupération de l'ensemble des données...")

    # 1. Résumé quotidien & Santé / Physiologie
    try:
        stats = garmin.get_user_summary(today)
    except Exception as e:
        print(f"Erreur résumé quotidien : {e}")
        stats = {}

    try:
        max_metrics = garmin.get_max_metrics(today)
    except Exception:
        max_metrics = {}

    # 2. Récupération des 10 dernières activités avec détails poussés
    detailed_activities = []
    try:
        raw_activities = garmin.get_activities(0, 10)
        
        # Téléchargement des traces GPX
        download_gpx_files(garmin, raw_activities)

        for act in raw_activities:
            act_id = act.get("activityId")
            
            # Récupération des Laps (Splits au KM / Tours)
            laps = []
            if act_id:
                try:
                    splits_data = garmin.get_activity_splits(act_id)
                    laps = splits_data.get("lapDTOs", [])
                except Exception:
                    pass

            # Récupération des détails complets (Allures, Dénivelé, Cadence, Puissance)
            details = {}
            if act_id:
                try:
                    details = garmin.get_activity_details(act_id)
                except Exception:
                    pass

            detailed_activities.append({
                "summary": act,
                "laps": laps,
                "gpx_file": f"gpx/activity_{act_id}.gpx" if act_id else None
            })
    except Exception as e:
        print(f"Erreur lors de la récupération des activités : {e}")

    # 3. Parcours enregistrés (Routes / GPX sauvés sur Garmin Connect)
    courses = []
    try:
        courses = garmin.get_courses()
    except Exception as e:
        print(f"Impossible de récupérer les parcours : {e}")

    # 4. Entraînements planifiés (Workouts)
    workouts = []
    try:
        workouts = garmin.get_workouts()
    except Exception as e:
        print(f"Impossible de récupérer les entraînements : {e}")

    # 5. Plans PacePro
    pacepro_plans = []
    try:
        pacepro_plans = garmin.get_pacepro_plans()
    except Exception as e:
        print(f"Impossible de récupérer les plans PacePro : {e}")

    # Structure JSON globale ultracomplète
    output_data = {
        "updated_at": datetime.now().isoformat(),
        "user_summary": {
            "today": stats,
            "vo2_max_running": max_metrics.get("generic", {}).get("vo2MaxPrecision"),
            "vo2_max_cycling": max_metrics.get("cycling", {}).get("vo2MaxPrecision"),
        },
        "recent_activities": detailed_activities,
        "saved_courses": courses,
        "workouts": workouts,
        "pacepro_plans": pacepro_plans
    }

    # Écriture dans data.json
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("Fichier data.json et fichiers GPX générés avec succès !")

if __name__ == "__main__":
    main()
