import requests
import json
import os
import smtplib
from datetime import datetime, timedelta
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
    # On demande 2 jours (aujourd'hui + demain)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn&forecast_days=2"
    try:
        response = requests.get(url).json()
        hourly = response.get('hourly', {})
        
        # Extraction des données de DEMAIN uniquement (les 24 dernières heures du pack de 48h)
        # L'index [24:48] correspond exactement à la deuxième journée
        speeds_tomorrow = hourly.get('wind_speed_10m', [])[24:48]
        directions_tomorrow = hourly.get('wind_direction_10m', [])[24:48]
        
        # On cherche s'il y a au moins un créneau favorable demain
        for speed, direction in zip(speeds_tomorrow, directions_tomorrow):
            if speed >= threshold and dir_min <= direction <= dir_max:
                return True, speed, direction
    except Exception as e:
        print(f"❌ Erreur API Meteo : {e}")
    return False, 0, 0

def send_email(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = "jeanchristophe.vaillant@gmail.com"
    msg['To'] = "jeanchristophe.vaillant@gmail.com"

    password = os.environ.get('EMAIL_PASSWORD')
    if not password:
        print("❌ Erreur: Secret EMAIL_PASSWORD manquant.")
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
    now = datetime.now()
    # Calcul de la date de demain
    tomorrow = now + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    
    print(f"--- Script lancé le {now.strftime('%Y-%m-%d %H:%M')} ---")
    print(f"🎯 Cible des prévisions : DEMAIN ({tomorrow_str})")
    
    configs = load_json(CONFIG_FILE)
    sent_alerts = load_json(SENT_ALERTS_FILE)
    
    print(f"Mémoire actuelle : {sent_alerts}")

    for alert in configs:
        alert_id = str(alert.get('id'))
        lieu = alert.get('lieu')
        
        print(f"\n🔎 Analyse pour demain à : {lieu}")

        # On vérifie si on a déjà prévenu pour la date de DEMAIN
        if sent_alerts.get(alert_id) == tomorrow_str:
            print(f"⏭️  Alerte déjà envoyée précédemment pour le {tomorrow_str}. Passage au suivant.")
            continue
            
        is_valid, speed, direction = check_weather(
            alert['lat'], alert['lon'], alert['seuil_vent'], 
            alert['dir_min'], alert['dir_max']
        )
        
        if is_valid:
            print(f"🎯 Conditions favorables trouvées pour demain ! ({speed} kts, {direction}°)")
            subject = f"⚠️ ALERTE DEMAIN ({tomorrow_str}) : {lieu}"
            body = f"Salut JC !\n\nLes prévisions pour DEMAIN ({tomorrow_str}) sont bonnes à {lieu} :\n- Vent : {speed} noeuds\n- Direction : {direction}°\n\nPrépare le matos !"
            
            if send_email(subject, body):
                # On enregistre la date cible (demain) dans la mémoire
                sent_alerts[alert_id] = tomorrow_str
        else:
            print(f"🍃 Pas de conditions favorables pour demain à {lieu}.")
            
    save_json(SENT_ALERTS_FILE, sent_alerts)
    print("\n--- Fin du script ---")

if __name__ == "__main__":
    main()