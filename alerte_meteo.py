import requests
import json
import os
from datetime import datetime

CONFIG_FILE = 'config.json'
SENT_ALERTS_FILE = 'sent_alerts.json'

def load_json(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        return {} if 'sent' in filename else []

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def check_weather(lat, lon, threshold, dir_min, dir_max):
    # Appel à l'API Open-Meteo (unités en noeuds et direction)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn&forecast_days=1"
    response = requests.get(url).json()
    
    # On regarde les prévisions pour les prochaines heures
    hourly = response.get('hourly', {})
    speeds = hourly.get('wind_speed_10m', [])
    directions = hourly.get('wind_direction_10m', [])
    
    for speed, direction in zip(speeds, directions):
        # Si une seule heure dans la journée correspond aux critères
        if speed >= threshold and dir_min <= direction <= dir_max:
            return True, speed, direction
    return False, 0, 0

import smtplib
from email.message import EmailMessage

def send_email(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = "jeanchristophe.vaillant@gmail.com"
    msg['To'] = "jeanchristophe.vaillant@gmail.com" # Vous vous l'envoyez à vous-même

    # Récupération du mot de passe depuis les variables d'environnement (GitHub Actions)
    # Pour tester en local, vous pouvez remplacer par votre code de 16 caractères
    password = os.environ.get('EMAIL_PASSWORD')

    if not password:
        print("Erreur: Mot de passe email non configuré.")
        return

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(msg['From'], password)
            smtp.send_message(msg)
        print(f"Email envoyé avec succès pour : {subject}")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")
        
def main():
    configs = load_json(CONFIG_FILE)
    sent_alerts = load_json(SENT_ALERTS_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    
    for alert in configs:
        alert_id = str(alert['id'])
        lieu = alert['lieu']
        
        # Vérifier si déjà envoyé aujourd'hui pour cette alerte précise
        if sent_alerts.get(alert_id) == today:
            print(f"Déjà alerté aujourd'hui pour {lieu}. On passe.")
            continue
            
        is_valid, speed, direction = check_weather(
            alert['lat'], alert['lon'], alert['seuil_vent'], 
            alert['dir_min'], alert['dir_max']
        )
        
        if is_valid:
            subject = f"⚠️ ALERTE VENT : {lieu}"
            body = f"Les conditions sont réunies à {lieu} !\nVent prévu : {speed} noeuds\nDirection : {direction}°"
            
            send_email(subject, body)
            
            # Enregistrer qu'on a envoyé l'alerte
            sent_alerts[alert_id] = today
            
    save_json(SENT_ALERTS_FILE, sent_alerts)

if __name__ == "__main__":
    main()