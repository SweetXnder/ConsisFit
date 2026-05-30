import cv2
import mediapipe as mp
import numpy as np
import time
import os 
from core.config import EXERCISE_CONFIG
from core.state import AppState

# Initialize MediaPipe outside the class to save memory
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class VisionEngine:
    @staticmethod
    def calculate_angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180.0 else angle

    @staticmethod
    def analyze_form(exercise, landmarks, side, stage, primary_angle):
        # This now returns strings for the AI Chatbox
        try:
            if exercise in ["Push-Ups", "Planks"]:
                s = [landmarks[getattr(mp_pose.PoseLandmark, f"{side}_SHOULDER")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{side}_SHOULDER")].y]
                h = [landmarks[getattr(mp_pose.PoseLandmark, f"{side}_HIP")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{side}_HIP")].y]
                a = [landmarks[getattr(mp_pose.PoseLandmark, f"{side}_ANKLE")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{side}_ANKLE")].y]
                body_line = VisionEngine.calculate_angle(s, h, a)
                if body_line < 152: return "Core sagging. Brace midsection."
            elif exercise == "Squats":
                if stage == "down" and primary_angle > 115: return "Drive lower to hit parallel depth."
        except Exception: pass
        return "Stable"

    @staticmethod
    def generate_frames(exercise, source, java_backend):
        # CROSS-PLATFORM COMPATIBILITY FIX: 
        # Removed cv2.CAP_DSHOW as it breaks macOS AVFoundation
        if str(source) == '0':
            cap = cv2.VideoCapture(0)
        else:
            cap = cv2.VideoCapture(source)

        # Critical Safety Check for Mac Privacy Permissions
        if not cap.isOpened():
            print(f"CRITICAL ERROR: OpenCV could not open source {source}.")
            print("If using webcam on Mac, check System Settings > Privacy & Security > Camera.")
            return

        pose = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)
        
        rep_count, stage, SIDE = 0, "up", "LEFT"
        AppState.LATEST_TELEMETRY = {"reps": 0, "status": "READY", "feedback": "Stable"}

        while cap.isOpened():
            success, frame = cap.read()
            if not success: break

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            if results.pose_landmarks and exercise in EXERCISE_CONFIG:
                mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                cfg = EXERCISE_CONFIG[exercise]
                landmarks = results.pose_landmarks.landmark
                
                # --- CALCULATE ANGLE ---
                j1, j2, j3 = cfg["joints"]
                p1 = [landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j1}")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j1}")].y]
                p2 = [landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j2}")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j2}")].y]
                p3 = [landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j3}")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j3}")].y]
                primary_angle = VisionEngine.calculate_angle(p1, p2, p3)
                
                # --- DEBUG ---
                print(f"DEBUG: Current Angle: {primary_angle:.2f}")

                # --- REP COUNTING LOGIC ---
                # Check for "DOWN" position
                if primary_angle < cfg["down"]: 
                    stage = "down"
                
                # Check for "UP" position (Rep Complete)
                if primary_angle > cfg["up"] and stage == "down":
                    stage = "up"
                    rep_count += 1
                    # Save to Java
                    if java_backend: java_backend.processVideoResult(exercise, 1, "Reps")
                
                # --- TELEMETRY BRIDGE ---
                feedback_msg = VisionEngine.analyze_form(exercise, landmarks, SIDE, stage, primary_angle)
                AppState.LATEST_TELEMETRY = {
                    "reps": rep_count,
                    "status": "ACTIVE",
                    "feedback": feedback_msg
                }

            ret, buffer = cv2.imencode('.jpg', image)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        cap.release()