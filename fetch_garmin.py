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
    if not email or not password:
        raise ValueError("Variables GARMIN_EMAIL et GARMIN_PASSWORD requises.")

    garmin = Garmin(email, password)

    if os.path.exists(token_dir):
        try:
            garmin.login(token_dir)
            return garmin
        except Exception:
            pass

    garmin.login()
    os.makedirs(token_dir, exist_ok=True)
    garmin.login(token_dir)
    return garmin

def main():
    garmin = init_garmin()
    os.makedirs("courses", exist_ok=True)

    print("Récupération de la liste des parcours enregistrés...")
    # Récupère la liste de tes parcours sauvegardés
    courses = garmin.get_courses()
    
    courses_summary = []

    for course in courses:
        course_id = course.get("courseId")
        course_name = course.get("courseName", f"Course_{course_id}")
        
        if not course_id:
            continue

        gpx_filename = f"courses/course_{course_id}.gpx"
        
        # Télécharge le fichier GPX du parcours s'il n'est pas déjà en cache local
        if not os.path.exists(gpx_filename):
            try:
                print(f"Téléchargement du parcours : {course_name} (ID: {course_id})...")
                gpx_data = garmin.download_course_gpx(course_id)
                with open(gpx_filename, "wb") as f:
                    f.write(gpx_data)
            except Exception as e:
                print(f"Erreur lors du téléchargement de {course_id} : {e}")

        courses_summary.append({
            "id": course_id,
            "name": course_name,
            "distance_meters": course.get("distanceInMeters"),
            "elevation_gain": course.get("elevationGain"),
            "gpx_file": gpx_filename
        })

    # Génère un index léger que ta PWA pourra consulter instantanément
    with open("courses_index.json", "w", encoding="utf-8") as f:
        json.dump(courses_summary, f, indent=2, ensure_ascii=False)

    print("Mise à jour des parcours terminée !")

if __name__ == "__main__":
    main()
