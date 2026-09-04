import os
import json
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")
token_dir = os.path.expanduser("~/.garminconnect")

def init_garmin():
    """Initialise la connexion avec réutilisation des tokens."""
    if not email or not password:
        raise ValueError("Variables GARMIN_EMAIL et GARMIN_PASSWORD requises.")

    garmin = Garmin(email, password)

    if os.path.exists(token_dir):
        try:
            print("Connexion via les tokens...")
            garmin.login(token_dir)
            return garmin
        except Exception as e:
            print(f"Échec jetons de session : {e}")

    print("Connexion via identifiants...")
    garmin.login()
    os.makedirs(token_dir, exist_ok=True)
    garmin.login(token_dir)
    return garmin

def main():
    try:
        garmin = init_garmin()
    except (GarminConnectAuthenticationError, GarminConnectTooManyRequestsError) as e:
        print(f"Arrêt du script : Impossible de se connecter à Garmin (Rate limit ou identifiants) : {e}")
        return

    os.makedirs("courses", exist_ok=True)

    print("Récupération de la liste des parcours enregistrés...")
    
    courses = []
    try:
        # La bonne méthode dans la librairie garminconnect :
        courses = garmin.get_user_courses()
    except AttributeError:
        # Fallback selon la version installée
        try:
            courses = garmin.get_courses()
        except Exception as e:
            print(f"Impossible de récupérer les parcours : {e}")
    except Exception as e:
        print(f"Erreur lors de la requête des parcours : {e}")

    courses_summary = []

    for course in courses:
        course_id = course.get("courseId")
        course_name = course.get("courseName", f"Course_{course_id}")
        
        if not course_id:
            continue

        gpx_filename = f"courses/course_{course_id}.gpx"
        
        # Téléchargement uniquement si le fichier n'est pas déjà en cache
        if not os.path.exists(gpx_filename):
            try:
                print(f"Téléchargement du GPX : {course_name} (ID: {course_id})...")
                gpx_data = garmin.download_course_gpx(course_id)
                with open(gpx_filename, "wb") as f:
                    f.write(gpx_data)
            except Exception as e:
                print(f"Erreur téléchargement GPX {course_id} : {e}")

        courses_summary.append({
            "id": course_id,
            "name": course_name,
            "distance_meters": course.get("distanceInMeters"),
            "elevation_gain": course.get("elevationGain"),
            "gpx_file": gpx_filename
        })

    with open("courses_index.json", "w", encoding="utf-8") as f:
        json.dump(courses_summary, f, indent=2, ensure_ascii=False)

    print(f"Mise à jour réussie : {len(courses_summary)} parcours traités.")

if __name__ == "__main__":
    main()
