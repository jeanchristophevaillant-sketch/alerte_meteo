from flask import Flask, render_template, request, redirect
import json
import time

app = Flask(__name__)
CONFIG_FILE = 'config.json'

def load_configs():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_configs(configs):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(configs, f, indent=4)

@app.route('/')
def index():
    configs = load_configs()
    return render_template('index.html', configs=configs)

@app.route('/add', methods=['POST'])
def add():
    configs = load_configs()
    new_alert = {
        "id": int(time.time()), # Génère un identifiant unique
        "lieu": request.form['lieu'],
        "lat": float(request.form['lat']),
        "lon": float(request.form['lon']),
        "seuil_vent": int(request.form['seuil_vent']),
        "dir_min": int(request.form['dir_min']),
        "dir_max": int(request.form['dir_max'])
    }
    configs.append(new_alert)
    save_configs(configs)
    return redirect('/')

@app.route('/delete/<int:alert_id>')
def delete(alert_id):
    configs = load_configs()
    configs = [c for c in configs if c['id'] != alert_id]
    save_configs(configs)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=5000)