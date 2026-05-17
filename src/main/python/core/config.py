import os

UPLOAD_FOLDER = 'src/main/python/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

GROQ_API_KEY = "GROQ API KEY DITO"

EXERCISE_CONFIG = {
    "Push-Ups":           {"joints": ("SHOULDER", "ELBOW", "WRIST"), "down": 100, "up": 150, "mode": "rep", "trigger": "up"},
    "Pull-Ups":           {"joints": ("SHOULDER", "ELBOW", "WRIST"), "down": 160, "up": 70,  "mode": "rep", "trigger": "down"},
    "Squats":             {"joints": ("HIP", "KNEE", "ANKLE"),       "down": 100, "up": 160, "mode": "rep", "trigger": "up"},
    "Lunges":             {"joints": ("HIP", "KNEE", "ANKLE"),       "down": 100, "up": 160, "mode": "rep", "trigger": "up"},
    "Dips":               {"joints": ("SHOULDER", "ELBOW", "WRIST"), "down": 95,  "up": 160, "mode": "rep", "trigger": "up"},
    "Handstand Push-Ups": {"joints": ("SHOULDER", "ELBOW", "WRIST"), "down": 100, "up": 150, "mode": "rep", "trigger": "up"},
    "Hanging Leg Raises": {"joints": ("SHOULDER", "HIP", "KNEE"),    "down": 160, "up": 100, "mode": "rep", "trigger": "down"},
    "Planks":             {"joints": ("SHOULDER", "HIP", "ANKLE"),   "straight": 165,        "mode": "time"}
}
