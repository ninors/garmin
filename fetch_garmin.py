#!/usr/bin/env python3
"""
Script d'extraction automatique Garmin Connect
Recupère les Parcours (GPX/FIT), Planifications/Entraînements, et Activités.
Inclus des mécanismes de secours (Token session, retry, fallbacks).
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("garmin_fetch")

try:
    from garminconnect import Garmin, GarminConnectAuthenticationError
    import garth
except ImportError:
    logger.error("La bibliothèque 'garminconnect' n'est pas installée. Exécutez: pip install garminconnect garth")
    sys.exit(1)

# Dossiers de sortie
BASE_DIR = Path("data")
COURSES_GPX_DIR = BASE_DIR / "courses" / "gpx"
COURSES_FIT_DIR = BASE_DIR / "courses" / "fit"
WORKOUTS_DIR = BASE_DIR / "workouts"
ACTIVITIES_GPX_DIR = BASE_DIR / "activities" / "gpx"
ACTIVITIES_FIT_DIR = BASE_DIR / "activities" / "fit"

TOKEN_DIR = Path(".garminconnect")

def init_directories():
    for d in [COURSES_GPX_DIR, COURSES_FIT_DIR, WORKOUTS_DIR, ACTIVITIES_GPX_DIR, ACTIVITIES_FIT_DIR, TOKEN_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name):
    """Nettoie une chaîne pour en faire un nom de fichier valide."""
    if not name:
        return "unnamed"
    clean = "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in name)
    return clean.strip().replace(" ", "_")[:60]

def login_garmin():
    """Authentification sécurisée avec User-Agent Navigateur (Contournement anti-bot 429)."""
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    tokens_base64 = os.environ.get("GARMIN_TOKENS")

    # Masquer l'agent Python et simuler un vrai navigateur Chrome (contourne le filtre 429 de sso.garmin.com)
    CHROME_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    
    try:
        garth.configure(domain="garmin.com")
        if hasattr(garth.client, "USER_AGENT"):
            garth.client.USER_AGENT = CHROME_USER_AGENT
        if hasattr(garth.client, "sess") and hasattr(garth.client.sess, "headers"):
            garth.client.sess.headers["User-Agent"] = CHROME_USER_AGENT
    except Exception as e:
        logger.warning(f"Impossible d'injecter le User-Agent Chrome : {e}")

    # 0. Restauration des tokens si présent dans GARMIN_TOKENS
    if tokens_base64:
        try:
            import base64, io, zipfile
            logger.info("Restauration des tokens de session depuis GARMIN_TOKENS...")
            decoded = base64.b64decode(tokens_base64)
            with zipfile.ZipFile(io.BytesIO(decoded), "r") as zip_ref:
                zip_ref.extractall(TOKEN_DIR)
            logger.info("Tokens restaurés avec succès !")
        except Exception as e:
            logger.warning(f"Erreur de restauration des tokens : {e}")

    # 1. Tentative de reprise de session par Token existant
    if TOKEN_DIR.exists() and any(TOKEN_DIR.iterdir()):
        try:
            logger.info("Tentative d'authentification par session/token existant...")
            garmin = Garmin()
            garmin.login(str(TOKEN_DIR))
            logger.info("Connexion par Token réussie !")
            return garmin
        except Exception as e:
            logger.warning(f"Échec d'utilisation des tokens enregistrés ({e})...")

    if not email or not password:
        logger.error("Erreur : GARMIN_EMAIL et GARMIN_PASSWORD doivent être définis !")
        sys.exit(1)

    # 2. Authentification avec simulation navigateur et retries
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connexion Garmin pour {email} (Tentative {attempt}/{max_retries} avec User-Agent Chrome)...")
            
            # Essai 1 via garth direct
            try:
                garth.login(email, password)
                garmin = Garmin()
                garmin.garth = garth.client
            except Exception:
                # Essai 2 via garminconnect
                garmin = Garmin(email, password)
                garmin.login()

            # Sauvegarde des tokens pour les exécutions futures
            if hasattr(garmin, "garth") and garmin.garth is not None:
                try:
                    garmin.garth.dump(str(TOKEN_DIR))
                    logger.info("Connexion réussie et tokens enregistrés !")
                except Exception:
                    pass
            return garmin

        except GarminConnectAuthenticationError as auth_err:
            logger.error(f"Identifiants Garmin incorrects : {auth_err}")
            sys.exit(1)
        except Exception as e:
            logger.warning(f"Avertissement lors de la tentative {attempt} : {e}")
            if attempt < max_retries:
                import time
                time.sleep( attempt * 5 )
            else:
                logger.error(f"Échec de connexion après {max_retries} tentatives : {e}")
                sys.exit(1)

def fetch_courses(garmin):
    """Récupère tous les parcours enregistrés avec export GPX & FIT."""
    logger.info("--- Récupération des parcours (Courses) ---")
    courses_data = []
    
    try:
        # Essai API principale des parcours
        courses = garmin.get_courses()
        logger.info(f"{len(courses)} parcours trouvé(s).")
    except Exception as e:
        logger.warning(f"Impossible de lister les parcours via l'API standard ({e}). Essai du fallback...")
        try:
            courses = garmin.connectapi("/course-service/course/user")
        except Exception as e2:
            logger.error(f"Échec de la récupération des parcours : {e2}")
            return courses_data

    for course in courses:
        course_id = course.get("courseId") or course.get("id")
        course_name = course.get("courseName") or course.get("name") or f"parcours_{course_id}"
        clean_name = sanitize_filename(course_name)
        
        distance_m = course.get("distance", 0)
        elevation_m = course.get("elevationGain", 0)
        created_date = course.get("createdDate") or course.get("updatedDate") or datetime.now().isoformat()

        logger.info(f"Traitement du parcours ID {course_id} : '{course_name}'")

        gpx_rel_path = None
        fit_rel_path = None

        # Export GPX (avec sécurité try/except pour continuer si un fichier bugue)
        try:
            gpx_bytes = garmin.download_course_gpx(course_id)
            gpx_filename = f"{clean_name}_{course_id}.gpx"
            gpx_filepath = COURSES_GPX_DIR / gpx_filename
            with open(gpx_filepath, "wb") as f:
                f.write(gpx_bytes)
            gpx_rel_path = f"data/courses/gpx/{gpx_filename}"
            logger.info(f"  ✓ GPX sauvegardé : {gpx_filename}")
        except Exception as e:
            logger.warning(f"  ⚠️ Impossible de télécharger le GPX pour {course_id} : {e}")

        # Export FIT
        try:
            fit_bytes = garmin.download_course_fit(course_id)
            fit_filename = f"{clean_name}_{course_id}.fit"
            fit_filepath = COURSES_FIT_DIR / fit_filename
            with open(fit_filepath, "wb") as f:
                f.write(fit_bytes)
            fit_rel_path = f"data/courses/fit/{fit_filename}"
            logger.info(f"  ✓ FIT sauvegardé : {fit_filename}")
        except Exception as e:
            logger.warning(f"  ⚠️ Impossible de télécharger le FIT pour {course_id} : {e}")

        if gpx_rel_path or fit_rel_path:
            courses_data.append({
                "id": str(course_id),
                "name": course_name,
                "distance_km": round(float(distance_m) / 1000.0, 2) if distance_m else 0,
                "elevation_m": round(float(elevation_m), 0) if elevation_m else 0,
                "date": created_date,
                "gpx_path": gpx_rel_path,
                "fit_path": fit_rel_path
            })

    return courses_data

def fetch_workouts(garmin):
    """Récupère les entraînements et planifications."""
    logger.info("--- Récupération des planifications & entraînements (Workouts) ---")
    workouts_data = []

    try:
        workouts = garmin.get_workouts()
        logger.info(f"{len(workouts)} entraînement(s) trouvé(s).")
    except Exception as e:
        logger.warning(f"Échec de la récupération des entraînements : {e}")
        return workouts_data

    for workout in workouts:
        workout_id = workout.get("workoutId") or workout.get("id")
        workout_name = workout.get("workoutName") or workout.get("name") or f"workout_{workout_id}"
        clean_name = sanitize_filename(workout_name)
        sport_type = workout.get("sportType", {}).get("sportTypeKey", "general")
        updated_date = workout.get("updatedDate") or datetime.now().isoformat()

        logger.info(f"Traitement de l'entraînement ID {workout_id} : '{workout_name}'")

        file_rel_path = None
        # Sauvegarde au format JSON structuré
        try:
            json_filename = f"{clean_name}_{workout_id}.json"
            json_filepath = WORKOUTS_DIR / json_filename
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(workout, f, ensure_ascii=False, indent=2)
            file_rel_path = f"data/workouts/{json_filename}"
            logger.info(f"  ✓ Entraînement JSON sauvegardé : {json_filename}")
        except Exception as e:
            logger.warning(f"  ⚠️ Échec de sauvegarde de l'entraînement {workout_id} : {e}")

        # Tenter d'exporter au format FIT si supporté
        try:
            fit_bytes = garmin.download_workout(workout_id)
            fit_filename = f"{clean_name}_{workout_id}.fit"
            fit_filepath = WORKOUTS_DIR / fit_filename
            with open(fit_filepath, "wb") as f:
                f.write(fit_bytes)
            logger.info(f"  ✓ Entraînement FIT sauvegardé : {fit_filename}")
        except Exception:
            pass  # Téléchargement FIT pas toujours disponible selon le type d'entraînement

        workouts_data.append({
            "id": str(workout_id),
            "name": workout_name,
            "sport": sport_type,
            "date": updated_date,
            "file_path": file_rel_path
        })

    return workouts_data

def fetch_recent_activities(garmin, limit=20):
    """Récupère les dernières activités au format GPX et FIT."""
    logger.info(f"--- Récupération des {limit} dernières activités ---")
    activities_data = []

    try:
        activities = garmin.get_activities(0, limit)
        logger.info(f"{len(activities)} activité(s) récente(s) trouvée(s).")
    except Exception as e:
        logger.warning(f"Échec de la récupération des activités : {e}")
        return activities_data

    for act in activities:
        act_id = act.get("activityId")
        act_name = act.get("activityName") or f"activite_{act_id}"
        clean_name = sanitize_filename(act_name)
        act_type = act.get("activityType", {}).get("typeKey", "activity")
        start_time = act.get("startTimeLocal") or act.get("startTimeGMT") or datetime.now().isoformat()
        distance_m = act.get("distance", 0)
        duration_s = act.get("duration", 0)

        logger.info(f"Traitement de l'activité ID {act_id} : '{act_name}'")

        gpx_rel_path = None
        fit_rel_path = None

        # Export GPX
        try:
            gpx_data = garmin.download_activity(act_id, dl_fmt=garmin.ActivityDownloadFormat.GPX)
            gpx_filename = f"{clean_name}_{act_id}.gpx"
            with open(ACTIVITIES_GPX_DIR / gpx_filename, "wb") as f:
                f.write(gpx_data)
            gpx_rel_path = f"data/activities/gpx/{gpx_filename}"
            logger.info(f"  ✓ GPX Activité sauvegardé : {gpx_filename}")
        except Exception as e:
            logger.warning(f"  ⚠️ Impossible d'exporter GPX activité {act_id} : {e}")

        # Export FIT (Original format ZIP/FIT)
        try:
            fit_data = garmin.download_activity(act_id, dl_fmt=garmin.ActivityDownloadFormat.ORIGINAL)
            fit_filename = f"{clean_name}_{act_id}.zip"
            with open(ACTIVITIES_FIT_DIR / fit_filename, "wb") as f:
                f.write(fit_data)
            fit_rel_path = f"data/activities/fit/{fit_filename}"
            logger.info(f"  ✓ FIT Activité sauvegardé : {fit_filename}")
        except Exception as e:
            logger.warning(f"  ⚠️ Impossible d'exporter FIT activité {act_id} : {e}")

        if gpx_rel_path or fit_rel_path:
            activities_data.append({
                "id": str(act_id),
                "name": act_name,
                "type": act_type,
                "distance_km": round(float(distance_m) / 1000.0, 2) if distance_m else 0,
                "duration_min": round(float(duration_s) / 60.0, 1) if duration_s else 0,
                "date": start_time,
                "gpx_path": gpx_rel_path,
                "fit_path": fit_rel_path
            })

    return activities_data

def main():
    logger.info("=== DÉMARRAGE DE LA SYNCHRONISATION GARMIN ===")
    init_directories()
    garmin = login_garmin()

    courses = fetch_courses(garmin)
    workouts = fetch_workouts(garmin)
    activities = fetch_recent_activities(garmin, limit=25)

    output = {
        "last_sync": datetime.now().isoformat(),
        "total_courses": len(courses),
        "total_workouts": len(workouts),
        "total_activities": len(activities),
        "courses": courses,
        "workouts": workouts,
        "activities": activities
    }

    data_json_path = BASE_DIR / "data.json"
    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"=== SYNCHRONISATION TERMINÉE AVEC SUCCÈS ===")
    logger.info(f"Résumé : {len(courses)} parcours, {len(workouts)} entraînements, {len(activities)} activités.")
    logger.info(f"Fichier de métadonnées généré : {data_json_path}")

if __name__ == "__main__":
    main()
