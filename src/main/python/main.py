import os
import time
import json
from werkzeug.utils import secure_filename
from flask import Flask, render_template, Response, request, jsonify, redirect, url_for
from py4j.java_gateway import JavaGateway
from groq import Groq

# Import our new OOP Modules
from core.config import UPLOAD_FOLDER, GROQ_API_KEY
from core.state import AppState
from engine.vision import VisionEngine

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- SECURE API ENGINES ---
os.environ["GROQ_API_KEY"] = GROQ_API_KEY 

try:
    groq_client = Groq()
except Exception:
    groq_client = None
    print("Warning: Groq LLM Key absent. AI Coaching components offline.")

try:
    gateway = JavaGateway()
    java_backend = gateway.entry_point
except Exception:
    java_backend = None
    print("Critical: Java Process detached. Verify WorkoutController instance is alive.")

# --- RESTFUL ROUTING LAYERS ---
@app.route('/')
def index():
    if java_backend and not java_backend.checkProfileExists():
        return redirect(url_for('onboarding'))
    return render_template('index.html')

@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    if request.method == 'POST':
        if java_backend:
            java_backend.registerUser(
                request.form.get('age'), request.form.get('weight'),
                request.form.get('height'), request.form.get('gender'),
                request.form.get('goal')
            )
        return redirect(url_for('index'))
    return render_template('onboarding.html')

@app.route('/api/get_profile')
def get_profile():
    if not java_backend: return jsonify({"error": "Java Core Offline"}), 500
    profile = java_backend.fetchProfile().split(",")
    if len(profile) < 5: return jsonify({"error": "Empty or default state map"}), 404
    return jsonify({
        "age": profile[0],
        "weight": profile[1],
        "height": profile[2],
        "gender": profile[3],
        "goal": profile[4]
    })

@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    if not java_backend: return jsonify({"error": "Java Core Offline"}), 500
    data = request.json
    try:
        java_backend.registerUser(
            str(data.get('age')), str(data.get('weight')),
            str(data.get('height')), str(data.get('gender')),
            str(data.get('goal'))
        )
        AppState.CACHED_PLAN_DATA = None
        AppState.LAST_GROQ_CALL_TIME = 0
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/daily_plan')
def get_daily_plan():
    if not groq_client or not java_backend: return jsonify({"error": "AI pipeline components not ready."})
    
    current_time = time.time()
    if AppState.CACHED_PLAN_DATA and (current_time - AppState.LAST_GROQ_CALL_TIME) < 10:
        return jsonify(AppState.CACHED_PLAN_DATA)

    profile = java_backend.fetchProfile().split(",")
    if len(profile) < 5: return jsonify({"error": "Profile parsing fault."})

    csv_path = "/Users/xander/IdeaProjects/GymRat/workout_history.csv"
    v_loaded = 0
    active_days = set()
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            for row in f:
                parts = row.strip().split(',')
                if len(parts) >= 4:
                    try:
                        v_loaded += int(parts[2].split()[0])
                        d_chunk = parts[3].split()
                        active_days.add(f"{d_chunk[1]} {d_chunk[2]}")
                    except: pass
    
    current_streak = len(active_days)
    total_xp = v_loaded * 15
    user_level = (total_xp // 1000) + 1 

    unlocked_exercises = ["Push-Ups", "Squats", "Lunges", "Dips"]
    if user_level >= 3: unlocked_exercises.append("Pull-Ups")
    if user_level >= 6: unlocked_exercises.extend(["Handstand Push-Ups", "Hanging Leg Raises"])
    if user_level >= 10: unlocked_exercises.append("Planks")

    last_ex = AppState.LATEST_TELEMETRY["exercise"]
    lowest_ang = AppState.LATEST_TELEMETRY["lowest_angle"]

    form_accuracy_pct = 94
    form_flaws_summary = "Excellent postural integrity maintained across your prior session."
    energy_level = "High"
    tempo_preference = "High-BPM focus frames (Violin arrangements / Upbeat Melodic Classical)"

    if last_ex == "Dips" and lowest_ang < 90:
        form_accuracy_pct = 76
        form_flaws_summary = f"Excessive drop depth detected at {lowest_ang} degrees, hyperextending past your safe 90-degree threshold frame and stressing anterior deltoids."
        energy_level = "Medium"
    elif last_ex in ["Push-Ups", "Planks"] and lowest_ang < 152 and lowest_ang != 180:
        form_accuracy_pct = 80
        form_flaws_summary = f"Midsection sag lines detected. Core line angle dropped out of structural target plane down to {lowest_ang} degrees."

    prompt = f"""
    You are ConsisFit, an elite, data-driven AI Personal Gym Trainer and Performance Nutritionist. 

    [ATHLETE BIOMETRICS]
    - Age: {profile[0]}
    - Weight: {profile[1]}kg
    - Height: {profile[2]}cm
    - Gender: {profile[3]}
    - Primary Fitness Goal: {profile[4]}

    [CONSISFIT REAL-TIME & HISTORICAL DATA]
    - Current Character Level: Level {user_level}
    - Dynamic Unlocked Exercise Choices: {", ".join(unlocked_exercises)}
    - Recent Form Accuracy Score (Mediapipe): {form_accuracy_pct}%
    - Main Form Deficiencies Identified: {form_flaws_summary}
    - Current Workout Streak: {current_streak} days
    - Athlete Energy/Fatigue Level: {energy_level}
    - Audio/Tempo Preference: {tempo_preference}

    [INSTRUCTIONS]
    1. Calculate optimal daily macronutrients and calories explicitly based on the Athlete Biometrics (Weight, Height, Age, Gender) using the Mifflin-St Jeor equation, adjusted for their primary goal.
    2. Design today's calisthenics routine selecting ONLY from the provided [Dynamic Unlocked Exercise Choices].
    3. Generate a hyper-personalized, actionable 'insight'.

    [OUTPUT CONSTRAINT]
    Return a flat JSON object ONLY. Enclose all values in string quotes. 
    You MUST dynamically calculate the specific nutritional values for this athlete. Do NOT use generic examples.

    Target JSON format:
    {{
        "calories": "<CALCULATE_BASED_ON_BIOMETRICS> kcal",
        "protein": "<CALCULATED_TARGET>g",
        "carbs": "<CALCULATED_TARGET>g",
        "fats": "<CALCULATED_TARGET>g",
        "workout": "<e.g., 5x10 Standard Dips, 4xMax Pushups>",
        "insight": "<Insert personalized insight here>"
    }}
    """
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        AppState.LAST_GROQ_CALL_TIME = time.time()
        AppState.CACHED_PLAN_DATA = json.loads(res.choices[0].message.content)
        return jsonify(AppState.CACHED_PLAN_DATA)
    except Exception as e: 
        return jsonify({"error": str(e)})

@app.route('/ask_coach', methods=['POST'])
def ask_coach():
    if not groq_client: return jsonify({"answer": "AI Engine link is offline."})
    user_q = request.json.get('question')
    
    profile = ["19", "70", "175", "Male", "V-Taper Focus"]
    if java_backend:
        try: profile = java_backend.fetchProfile().split(",")
        except: pass

    rag_context = f"""
    You are ConsisFit, an elite AI Gym Trainer.
    [ATHLETE BIOMETRICS] Age: {profile[0]} | Weight: {profile[1]}kg | Height: {profile[2]}cm | Gender: {profile[3]} | Goal: {profile[4]}
    [LAST TRACKED SET] Exercise: {AppState.LATEST_TELEMETRY['exercise']} | Deepest Joint Apex: {AppState.LATEST_TELEMETRY['lowest_angle']} degrees
    [USER QUERY] "{user_q}"
    Answer concisely (max 3 sentences) using plain prose.
    """
    try:
        res = groq_client.chat.completions.create(messages=[{"role": "user", "content": rag_context}], model="llama-3.1-8b-instant")
        return jsonify({"answer": res.choices[0].message.content})
    except Exception as e: 
        return jsonify({"answer": f"API Request fault: {str(e)}"})

@app.route('/upload_video', methods=['POST'])
def upload_video():
    file = request.files['video']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return jsonify({"filepath": filepath}), 200

@app.route('/video_feed')
def video_feed():
    # Pass the Java Gateway down to the Engine
    return Response(VisionEngine.generate_frames(request.args.get('exercise', 'Push-Ups'), request.args.get('source', '0'), java_backend), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stats')
def get_stats():
    csv_path = "/Users/xander/IdeaProjects/GymRat/workout_history.csv"
    total_volume = highest_rep = 0
    highest_rep_exercise = "None"
    active_days = set()
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            for row in f:
                parts = row.strip().split(',')
                if len(parts) >= 4:
                    try:
                        ex_name = parts[1]
                        val = int(parts[2].split()[0])
                        if parts[2].split()[1] == "Reps":
                            total_volume += val
                            if val > highest_rep: highest_rep, highest_rep_exercise = val, ex_name
                        else: total_volume += val
                        d_chunk = parts[3].split()
                        active_days.add(f"{d_chunk[1]} {d_chunk[2]}")
                    except: pass
    
    total_xp = total_volume * 15
    milestones = []
    if total_volume > 0: milestones.append(" Gym Cutie (First Set Logged)")
    if total_volume >= 150: milestones.append(" Gym Chad (150+ Total Units)")
    if len(active_days) >= 3: milestones.append(" Habit Builder (3+ Active Days)")
    if highest_rep >= 15: milestones.append(" Rep Demon (Crushed 15+ Single Set Reps)")
    if not milestones: milestones.append(" Syncing initial records...")

    return jsonify({
        "level": (total_xp // 1000) + 1, "xp": total_xp, 
        "streak": len(active_days), "workouts_logged": len(active_days),
        "total_volume": total_volume, "highest_rep": highest_rep,
        "highest_rep_exercise": highest_rep_exercise, "milestones": milestones[:3]
    })

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
