import os
import time
import json
from werkzeug.utils import secure_filename
from flask import Flask, Response, render_template, request, jsonify, redirect, url_for
from py4j.java_gateway import JavaGateway
from groq import Groq

# Import our OOP Modules
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

# --- UI ROUTING LAYERS ---

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/start')
def start():
    if java_backend and java_backend.checkProfileExists():
        return redirect(url_for('hub'))
    return render_template('onboarding.html')

@app.route('/hub')
def hub():
    if java_backend and not java_backend.checkProfileExists():
        return redirect(url_for('start'))
    return render_template('hub.html')

@app.route('/tracker')
def tracker():
    if java_backend and not java_backend.checkProfileExists():
        return redirect(url_for('start'))
    return render_template('tracker.html')

# --- DATA SYNCHRONIZATION APIs ---

@app.route('/api/telemetry')
def get_telemetry():
    """Returns the live, real-time data from the Computer Vision engine."""
    # Ensure LATEST_TELEMETRY exists in your AppState object
    if not hasattr(AppState, 'LATEST_TELEMETRY') or not AppState.LATEST_TELEMETRY:
        return jsonify({"reps": 0, "status": "READY", "feedback": ""})
    return jsonify(AppState.LATEST_TELEMETRY)
        
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

@app.route('/api/save_workout', methods=['POST'])
def save_workout():
    if not java_backend: return jsonify({"error": "Java Core Offline"}), 500
    data = request.json
    try:
        exercise_name = data.get('exercise', 'Unknown Exercise')
        completed_reps = data.get('completed_reps', 0)
        
        if completed_reps > 0:
            java_backend.processVideoResult(exercise_name, completed_reps, "Reps")
            return jsonify({"success": True, "logged": completed_reps})
        return jsonify({"success": False, "message": "No volume to log"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/stats')
def get_stats():
    csv_path = "/Users/xander/IdeaProjects/GymRat/workout_history.csv"
    total_volume = 0
    highest_rep = 0
    
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            for row in f:
                parts = [p.strip() for p in row.split(',')]
                # Format is: ['LOG-ID', 'Exercise', '11 Reps', 'Date']
                if len(parts) >= 3:
                    try:
                        # Extract the number from parts[2], e.g., "11 Reps" -> 11
                        raw_vol = parts[2]
                        # This splits "11 Reps" into ["11", "Reps"] and takes the first part
                        val = int(raw_vol.split()[0]) 
                        
                        total_volume += val
                        if val > highest_rep: 
                            highest_rep = val
                    except Exception as e:
                        # This will catch if the parsing fails for a specific line
                        continue
    
    return jsonify({
        "level": (total_volume * 15 // 1000) + 1, 
        "xp": total_volume * 15, 
        "total_volume": total_volume, 
        "highestPR": highest_rep,
        "milestones": ["🏆 Iron Initiate"] if total_volume > 0 else []
    })

# --- AI GENERATION APIS ---

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
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            for row in f:
                print(f"DEBUG: Reading row: {row}")
                parts = row.strip().split(',')
                if len(parts) >= 4:
                    try:
                        v_loaded += int(parts[2].split()[0])
                    except: pass
    
    user_level = ((v_loaded * 15) // 1000) + 1 
    unlocked_exercises = ["Push-Ups", "Squats", "Lunges", "Dips"]
    if user_level >= 3: unlocked_exercises.append("Pull-Ups")
    if user_level >= 6: unlocked_exercises.extend(["Handstand Push-Ups", "Hanging Leg Raises"])
    if user_level >= 10: unlocked_exercises.append("Planks")

    prompt = f"""
    You are ConsisFit, an elite, data-driven AI Personal Gym Trainer and Performance Nutritionist. 

    [ATHLETE BIOMETRICS]
    - Age: {profile[0]}
    - Weight: {profile[1]}kg
    - Height: {profile[2]}cm
    - Gender: {profile[3]}
    - Primary Fitness Goal: {profile[4]}

    [INSTRUCTIONS]
    1. Calculate optimal daily macronutrients and calories explicitly based on the Athlete Biometrics using the Mifflin-St Jeor equation.
    2. Design today's calisthenics routine selecting ONLY from: {", ".join(unlocked_exercises)}.
    3. Generate a hyper-personalized, actionable 'insight'.

    [OUTPUT CONSTRAINT]
    Return a flat JSON object ONLY. Enclose all values in string quotes. 
    You MUST dynamically calculate the specific nutritional values for this athlete.

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
    if not groq_client: return jsonify({"answer": "Error: AI Engine link is offline. Check API Key."})
    user_q = request.json.get('question')
    
    profile = ["19", "70", "175", "Male", "Calisthenics"]
    if java_backend:
        try: profile = java_backend.fetchProfile().split(",")
        except: pass

    rag_context = f"""
    You are ConsisFit, an elite AI Gym Trainer.
    [ATHLETE BIOMETRICS] Age: {profile[0]} | Weight: {profile[1]}kg | Height: {profile[2]}cm | Gender: {profile[3]}
    [USER QUERY] "{user_q}"
    Answer concisely (max 3 sentences) using plain prose.
    """
    try:
        res = groq_client.chat.completions.create(messages=[{"role": "user", "content": rag_context}], model="llama-3.1-8b-instant")
        return jsonify({"answer": res.choices[0].message.content})
    except Exception as e: 
        print(f"GROQ ERROR: {str(e)}") 
        return jsonify({"answer": f"API Fault: {str(e)}"}) 

# --- VISION ENDPOINTS ---

@app.route('/upload_video', methods=['POST'])
def upload_video():
    file = request.files['video']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # OS FIX for Windows Uploads
    safe_filepath = filepath.replace('\\', '/')
    return jsonify({"filepath": safe_filepath}), 200

@app.route('/video_feed')
def video_feed():
    # Pass java_backend and exercise name; the engine should now 
    # only be drawing SKELETONS, not text!
    return Response(
        VisionEngine.generate_frames(
            request.args.get('exercise', 'Push-Ups'), 
            request.args.get('source', '0'), 
            java_backend
        ), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
# --- ENSURE THIS BLOCK IS CORRECT ---
if __name__ == "__main__":
    # Ensure UPLOAD_FOLDER exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='127.0.0.1', port=5000, debug=True)