import joblib
from sklearn.preprocessing import LabelEncoder

# --------------------------
# Encode weekdays
# --------------------------
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
le_day = LabelEncoder()
le_day.fit(days)
joblib.dump(le_day, "label_encoder_day.pkl")

# --------------------------
# Encode time slots (0–95 for 15-minute intervals)
# --------------------------
time_slots = [str(i) for i in range(96)]
le_time = LabelEncoder()
le_time.fit(time_slots)
joblib.dump(le_time, "label_encoder_time.pkl")

# --------------------------
# Encode landmark types (use the same set as in backend)
# --------------------------
landmark_types = ["Metro", "Stadium", "Mall", "Office", "Temple"]
le_type = LabelEncoder()
le_type.fit(landmark_types)
joblib.dump(le_type, "label_encoder_type.pkl")

print("✅ Encoders retrained and saved successfully!")
