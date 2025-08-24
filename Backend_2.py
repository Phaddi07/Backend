# backend.py
from flask import Flask, jsonify
import pickle
import random
import os

app = Flask(__name__)

# Base path (current file's directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load trained model + encoders using relative paths
model = pickle.load(open(os.path.join(BASE_DIR, "Trained models", "landmark_demand_predictor.pkl"), "rb"))
le_day = pickle.load(open(os.path.join(BASE_DIR, "Trained models", "label_encoder_day.pkl"), "rb"))
le_time = pickle.load(open(os.path.join(BASE_DIR, "Trained models", "label_encoder_time.pkl"), "rb"))
le_type = pickle.load(open(os.path.join(BASE_DIR, "Trained models", "label_encoder_type.pkl"), "rb"))

# Simulation clock
current_day_index = 0  # 0=Monday
current_time_index = 0  # each tick = 15 mins, 0 = 00:00
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Root route (for Render health check / base test)
@app.route("/")
def home():
    return jsonify({"message": "Taxi Swarm Backend is running!"})

@app.route("/next_demand")
def next_demand():
    global current_day_index, current_time_index

    # Pick a random landmark type
    landmark_types = ["Metro", "Stadium", "Mall", "Office", "Temple"]
    landmark_type = random.choice(landmark_types)

    # Encode features
    X = [[
        le_day.transform([days[current_day_index]])[0],
        le_time.transform([str(current_time_index)])[0],
        le_type.transform([landmark_type])[0]
    ]]

    # Predict demand probability (for simplicity we use prediction as strength)
    demand_label = model.predict(X)[0]

    # Generate random coords inside NYC bounding box
    lat = 40.60 + random.random() * 0.25
    lng = -74.05 + random.random() * 0.25

    # Advance time
    current_time_index += 1
    if current_time_index >= 96:  # 24h * 4 ticks per hour
        current_time_index = 0
        current_day_index = (current_day_index + 1) % 7

    return jsonify({
        "day": days[current_day_index],
        "time_index": current_time_index,
        "landmark_type": landmark_type,
        "demand_label": int(demand_label),
        "lat": lat,
        "lng": lng
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
