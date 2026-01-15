import requests
import json
import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

CONFIG_FILE = 'config.json'
SENT_ALERTS_FILE = 'sent_alerts.json'

def degree_to_direction(deg):
    """Convertit les degrés (0-360) en direction cardinale (N, NE, etc.)"""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                  "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]
    index = int((deg + 11.25) / 22.5) % 16
    return directions[index]

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
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn&forecast_days=2"
    try:
        response = requests.get(url).json()
        hourly = response.get('hourly', {})
        
        speeds = hourly.get('wind_speed_10m', [])[24:48]
        directions = hourly.get('wind_direction_10m', [])[24:48]
        times = hourly.get('time', [])[24:48]
        
        forecast_details = []
        is_good_day = False

        for t, speed, direction in zip(times, speeds, directions):
            hour_str = datetime.fromisoformat(t).strftime('%H:%M')
            meets_criteria = speed >= threshold and dir_min <= direction <= dir_max
            if meets_criteria:
                is_good_day = True
            
            forecast_details.append({
                "hour": hour_str,
                "speed": speed,
                "dir_str": degree_to_direction(direction),
                "valid": meets_criteria
            })
            
        return is_good_day, forecast_details
    except Exception as e:
        print(f"❌ Erreur API : {e}")
    return False, []

def send_email(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = "jeanchristophe.vaillant@gmail.com"
    msg['To'] = "jeanchristophe.vaillant@gmail.com"
    password = os.environ.get('EMAIL_PASSWORD')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(msg['From'], password)
            smtp.send_message(msg)
        print(f"✅ Email envoyé : {subject}")
        return True
    except Exception as e:
        print(f"❌ Erreur SMTP : {e}")
        return False

def main():
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    configs = load_json(CONFIG_FILE)
    sent_alerts = load_json(SENT_ALERTS_FILE)

    for alert in configs:
        alert_id = str(alert.get('id'))
        lieu = alert['lieu']
        
        if sent_alerts.get(alert_id) == tomorrow_str:
            print(f"⏭️ {lieu} déjà fait.")
            continue
            
        is_valid, forecast = check_weather(
            alert['lat'], alert['lon'], alert['seuil_vent'], 
            alert['dir_min'], alert['dir_max']
        )
        
        if is_valid:
            # On prépare le rappel de la configuration en texte
            dir_min_txt = degree_to_direction(alert['dir_min'])
            dir_max_txt = degree_to_direction(alert['dir_max'])
            
            subject = f"⚠️ PLANNING VENT DEMAIN ({tomorrow_str}) : {lieu}"
            
            # Construction du corps du mail avec rappel des seuils
            body = f"Salut JC !\n\nVoici les prévisions pour DEMAIN à {lieu} :\n"
            body += f"⚙️ Config : Min {alert['seuil_vent']} kts | Secteur {dir_min_txt} - {dir_max_txt}\n\n"
            body += "HEURE | VENT (kts) | DIR\n"
            body += "--------------------------\n"
            
            for f in forecast:
                marker = "⭐" if f['valid'] else "  "
                body += f"{f['hour']} | {f['speed']:>4} kts  | {f['dir_str']:<3} {marker}\n"
            
            body += "\nBonne session !"
            
            if send_email(subject, body):
                sent_alerts[alert_id] = tomorrow_str
            
    save_json(SENT_ALERTS_FILE, sent_alerts)

if __name__ == "__main__":
    main()
