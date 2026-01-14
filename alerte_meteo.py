import requests
import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

CONFIG_FILE = 'config.json'
SENT_ALERTS_FILE = 'sent_alerts.json'

def load_json(filename):
    try:
        with open(filename, 'r') as f:
            content = f.read().strip()
            if not content:
                return {} if 'sent' in filename else []
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if 'sent' in filename else []

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def check_weather(lat, lon, threshold, dir_min, dir_max):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn&forecast_days=1"
    try:
        response = requests.get(url).json()
        hourly = response.get('hourly', {})
        speeds = hourly.get('wind_speed_10m', [])
        directions = hourly.get('wind_direction_10m', [])
        
        for speed, direction in zip(speeds, directions):
            if speed >= threshold and dir_min <= direction <= dir_max:
                return True, speed, direction
    except Exception as e:
        print(f"Erreur API Meteo : {e}")
    return False, 0, 0

def send_email(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = "jeanchristophe.vaillant@gmail.com"
    msg['To'] = "jeanchristophe.vaillant@gmail.com"

    password = os.environ.get('EMAIL_PASSWORD')
    if not password:
        print("❌ Erreur: Secret EMAIL_PASSWORD introuvable dans GitHub.")
        return False

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(msg['From'], password)
            smtp.send_message(msg)
        print(f"✅ Email envoyé avec succès : {subject}")
        return True
    except Exception as e:
        print(f"❌ Erreur SMTP : {e}")
        return False

def main():
    print(f"--- Démarrage du script le {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
    
    configs = load_json(CONFIG_FILE)
    sent_alerts = load_json(SENT_ALERTS_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Mémoire actuelle : {sent_alerts}")

    for alert in configs:
        alert_id = str(alert.get('id'))
        lieu = alert.get('lieu')
        
        print(f"\n🔎 Vérification de : {lieu} (ID: {alert_id})")

        # Vérification anti-spam
        if sent_alerts.get(alert_id) == today:
            print(f"⏭️  Déjà alerté aujourd'hui pour {lieu}. On passe au suivant.")
            continue
            
        is_valid, speed, direction = check_weather(
            alert['lat'], alert['lon'], alert['seuil_vent'], 
            alert['dir_min'], alert['dir_max']
        )
        
        if is_valid:
            print(f"🎯 Conditions remplies ! ({speed} kts, {direction}°)")
            subject = f"⚠️ ALERTE VENT : {lieu}"
            body = f"Les conditions sont réunies à {lieu} !\nVent prévu : {speed} noeuds\nDirection : {direction}°"
            
            if send_email(subject, body):
                # On ne met à jour la mémoire QUE si le mail est parti
                sent_alerts[alert_id] = today
        else:
            print(f"🍃 Conditions non remplies pour {lieu}.")
            
    # Sauvegarde finale de la mémoire
    save_json(SENT_ALERTS_FILE, sent_alerts)
    print("\n--- Fin du script ---")

if __name__ == "__main__":
    main()