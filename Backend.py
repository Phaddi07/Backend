from flask import Flask, request, jsonify # type: ignore
from flask_cors import CORS # type: ignore
import pickle
import numpy as np # type: ignore

# -----------------------------
# Load model + encoders
# -----------------------------
MODEL_PATH = "C:\Pragun\Project\Final project\Simulation part\Last try\Trained models\landmark_demand_predictor.pkl"
LE_DAY_PATH = "C:\Pragun\Project\Final project\Simulation part\Last try\Trained models\label_encoder_day.pkl"
LE_TIME_PATH = "C:\Pragun\Project\Final project\Simulation part\Last try\Trained models\label_encoder_time.pkl"
LE_TYPE_PATH = "C:\Pragun\Project\Final project\Simulation part\Last try\Trained models\label_encoder_type.pkl"         # optional if you use "type"
LE_LABEL_PATH = "C:\Pragun\Project\Final project\Simulation part\Last try\Trained models\label_encoder_label.pkl"        # encodes y (e.g., High/Low)

model = pickle.load(open(MODEL_PATH, "rb"))
le_day = pickle.load(open(LE_DAY_PATH, "rb"))
le_time = pickle.load(open(LE_TIME_PATH, "rb"))
# If you didn’t train with "type", set le_type = None and handle below
try:
    le_type = pickle.load(open(LE_TYPE_PATH, "rb"))
except Exception:
    le_type = None
le_label = pickle.load(open(LE_LABEL_PATH, "rb"))

# Which label index is "High" (if it exists)?
try:
    HIGH_IDX = int(np.where(le_label.classes_ == "High")[0][0])
except Exception:
    # If you used numeric labels, fallback to the max-prob class
    HIGH_IDX = None

# -----------------------------
# Build candidate grid (NYC area: Manhattan/Brooklyn/Queens)
# -----------------------------
LAT_MIN, LAT_MAX = 40.64, 40.82
LON_MIN, LON_MAX = -74.05, -73.85
# 25 x 25 = 625 candidates (tweak as you like)
GRID_STEPS = 25

def candidate_points():
    lats = np.linspace(LAT_MIN, LAT_MAX, GRID_STEPS)
    lons = np.linspace(LON_MIN, LON_MAX, GRID_STEPS)
    pts = []
    for la in lats:
        for lo in lons:
            # quick-and-dirty water masks (avoid obvious rivers/bay)
            if lo < -74.02:      # Hudson
                continue
            if -73.99 < lo < -73.94:  # East River band
                continue
            if la < 40.68 and lo < -74.0:  # Upper Bay
                continue
            pts.append((float(la), float(lo)))
    return pts

CANDIDATES = candidate_points()

def safe_transform(le, values):
    """
    If a value is unseen, default to the first class to avoid errors.
    """
    if le is None:
        # If encoder doesn't exist (e.g., not trained with 'type'), return zeros
        return np.zeros(len(values), dtype=int)
    out = []
    classes = set(le.classes_)
    fallback = int(le.transform([le.classes_[0]])[0])
    for v in values:
        if v in classes:
            out.append(int(le.transform([v])[0]))
        else:
            out.append(fallback)
    return np.array(out, dtype=int)

def build_feature_matrix(day, time, typ, n_rows):
    day_enc = safe_transform(le_day, [day] * n_rows)
    time_enc = safe_transform(le_time, [time] * n_rows)
    type_enc = safe_transform(le_type, [typ] * n_rows)  # zeros if le_type is None

    # Must match your training feature order:
    X = np.column_stack([day_enc, time_enc, type_enc])
    return X

# -----------------------------
# Flask app
# -----------------------------
app = Flask(__name__)
CORS(app)  # allow local file frontend to call the API

@app.route("/predict", methods=["POST"])
def predict():
    """
    Request JSON:
    {
      "day": "Monday",
      "time": "09:00",
      "type": "Metro",          # optional, if you trained with 'type'
      "top_k": 6                # optional
    }
    Response:
    {
      "demands": [{"lat":..., "lng":..., "intensity":...}, ...]
    }
    """
    payload = request.get_json(force=True) or {}
    day = payload.get("day", "Monday")
    time = payload.get("time", "09:00")
    typ = payload.get("type", "General")
    top_k = int(payload.get("top_k", 6))

    if not CANDIDATES:
        return jsonify({"demands": []})

    X = build_feature_matrix(day, time, typ, len(CANDIDATES))

    # Predict probabilities (works best if your classifier supports predict_proba)
    try:
        proba = model.predict_proba(X)  # shape: [n_samples, n_classes]
        if HIGH_IDX is not None and HIGH_IDX < proba.shape[1]:
            intensities = proba[:, HIGH_IDX]
        else:
            # If no explicit HIGH label, take max class prob
            intensities = proba.max(axis=1)
    except Exception:
        # Fall back to decision_function or raw predict (less ideal)
        try:
            score = model.decision_function(X).astype(float)
            # min-max normalize
            intensities = (score - score.min()) / (score.ptp() + 1e-9)
        except Exception:
            # Last resort: uniform intensity
            intensities = np.ones(len(CANDIDATES), dtype=float)

    # pick top_k
    idx = np.argsort(intensities)[-top_k:][::-1]
    out = []
    for i in idx:
        la, lo = CANDIDATES[i]
        out.append({
            "lat": float(la),
            "lng": float(lo),
            "intensity": float(float(intensities[i]))
        })

    return jsonify({"demands": out})

if __name__ == "__main__":
    # Run: python app.py
    app.run(host="127.0.0.1", port=5000, debug=True)
