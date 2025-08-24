import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import pickle

# ----------------------------
# 1. Load dataset
# ----------------------------
df = pd.read_csv("C:\Pragun\Project\Final project\Simulation part\Last try\orange_ready_colorcode.csv")  
# Ensure it has columns: "day", "time", "type", "demand_label"

# ----------------------------
# 2. Initialize encoders
# ----------------------------
le_day = LabelEncoder()
le_time = LabelEncoder()
le_type = LabelEncoder()
le_label = LabelEncoder()   # also encode the demand_label if categorical (e.g., High/Low)

# ----------------------------
# 3. Encode features + label
# ----------------------------
df['day_enc'] = le_day.fit_transform(df['day'])
df['time_enc'] = le_time.fit_transform(df['time'])
df['type_enc'] = le_type.fit_transform(df['type'])
df['label_enc'] = le_label.fit_transform(df['demand_label'])

# ----------------------------
# 4. Train the model
# ----------------------------
X = df[['day_enc', 'time_enc', 'type_enc']]
y = df['label_enc']

model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X, y)

# ----------------------------
# 5. Save model + encoders
# ----------------------------
pickle.dump(model, open("landmark_demand_predictor.pkl", "wb"))
pickle.dump(le_day, open("label_encoder_day.pkl", "wb"))
pickle.dump(le_time, open("label_encoder_time.pkl", "wb"))
pickle.dump(le_type, open("label_encoder_type.pkl", "wb"))
pickle.dump(le_label, open("label_encoder_label.pkl", "wb"))

print("✅ Model and encoders saved successfully!")
