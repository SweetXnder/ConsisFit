import cv2
import numpy as np
import time
from core.config import EXERCISE_CONFIG
from core.state import AppState

try:
    import mediapipe.python.solutions.pose as mp_pose
    import mediapipe.python.solutions.drawing_utils as mp_drawing
except ImportError:
    pass

class VisionEngine:
    @staticmethod
    def calculate_angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180.0 else angle

    @staticmethod
    def analyze_form(exercise, landmarks, side, stage, primary_angle):
        try:
            req_joints = EXERCISE_CONFIG[exercise]["joints"]
            for j in req_joints:
                if landmarks[getattr(mp_pose.PoseLandmark, f"{side}_{j}")].visibility < 0.6:
                    return "WARNING: Step back. Structural joints occluded.", (0, 0, 255)

            if exercise in ["Push-Ups", "Planks"]:
                s = [landmarks[getattr(mp_pose.PoseLandmark, f"{side}_SHOULDER")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{side}_SHOULDER")].y]
                h = [landmarks[getattr(mp_pose.PoseLandmark, f"{side}_HIP")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{side}_HIP")].y]
                a = [landmarks[getattr(mp_pose.PoseLandmark, f"{side}_ANKLE")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{side}_ANKLE")].y]
                body_line = VisionEngine.calculate_angle(s, h, a)
                if body_line < 152: return "CORRECTION: Core sagging. Brace your midsection.", (0, 165, 255)

            elif exercise == "Squats":
                if stage == "down" and primary_angle > 115: return "TIP: Drive lower to hit target parallel depth.", (0, 255, 255)
        except Exception: pass
        return "Form Status: Stable.", (0, 255, 0)

    @staticmethod
    def generate_frames(exercise, source, java_backend):
        AppState.LATEST_TELEMETRY["exercise"] = exercise
        AppState.LATEST_TELEMETRY["lowest_angle"] = 180

        video_source = 0 if source == '0' else source
        cap = cv2.VideoCapture(video_source)
        pose = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)
        
        system_state = "CALIBRATING"
        calibration_start_time = None
        REQUIRED_HOLD_TIME = 3.0
        
        rep_count, stage, SIDE = 0, "up", "LEFT"
        plank_start_time, total_plank_duration = None, 0.0

        try:
            while cap.isOpened():
                success, frame = cap.read()
                if not success: break

                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(image)
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                coach_text, coach_color = "Syncing posture line...", (200, 200, 200)

                if results.pose_landmarks and exercise in EXERCISE_CONFIG:
                    mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                    cfg = EXERCISE_CONFIG[exercise]
                    landmarks = results.pose_landmarks.landmark
                    
                    try:
                        j1, j2, j3 = cfg["joints"]
                        p1 = [landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j1}")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j1}")].y]
                        p2 = [landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j2}")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j2}")].y]
                        p3 = [landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j3}")].x, landmarks[getattr(mp_pose.PoseLandmark, f"{SIDE}_{j3}")].y]
                        primary_angle = VisionEngine.calculate_angle(p1, p2, p3)

                        if primary_angle < AppState.LATEST_TELEMETRY["lowest_angle"]:
                            AppState.LATEST_TELEMETRY["lowest_angle"] = int(primary_angle)

                        if system_state == "CALIBRATING":
                            is_ready = False
                            if cfg["mode"] == "rep" and primary_angle > (cfg["up"] - 15): is_ready = True
                            elif cfg["mode"] == "time" and primary_angle > cfg["straight"]: is_ready = True

                            if is_ready:
                                if calibration_start_time is None: calibration_start_time = time.time()
                                remaining = max(0, REQUIRED_HOLD_TIME - (time.time() - calibration_start_time))
                                coach_text, coach_color = f"STABILIZE START: {remaining:.1f}s", (0, 165, 255)
                                if remaining <= 0: system_state = "ACTIVE"
                            else:
                                calibration_start_time = None
                                coach_text, coach_color = "Assume starting extension.", (0, 0, 255)

                        elif system_state == "ACTIVE":
                            if cfg["mode"] == "rep":
                                if cfg["trigger"] == "up":
                                    if primary_angle < cfg["down"]: stage = "down"
                                    if primary_angle > cfg["up"] and stage == "down": stage = "up"; rep_count += 1
                                elif cfg["trigger"] == "down":
                                    if primary_angle > cfg["down"]: stage = "down"
                                    if primary_angle < cfg["up"] and stage == "down": stage = "up"; rep_count += 1
                                coach_text, coach_color = VisionEngine.analyze_form(exercise, landmarks, SIDE, stage, primary_angle)
                            elif cfg["mode"] == "time":
                                if primary_angle > cfg["straight"]:
                                    stage = "HOLDING"
                                    if plank_start_time is None: plank_start_time = time.time()
                                    total_plank_duration += time.time() - plank_start_time
                                    plank_start_time = time.time()
                                else:
                                    stage = "FORM FAULT"
                                    plank_start_time = None
                                rep_count = int(total_plank_duration)
                                coach_text, coach_color = VisionEngine.analyze_form(exercise, landmarks, SIDE, stage, primary_angle)
                    except Exception: pass

                    cv2.rectangle(image, (0,0), (280,115), (0,0,0), -1)
                    metric_label = "SECONDS" if cfg["mode"] == "time" else "REPS"
                    cv2.putText(image, f"{exercise}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.putText(image, f"{metric_label}: {rep_count}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                    cv2.putText(image, f"STATE: {stage} | {system_state}", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                h_img, w_img, _ = image.shape
                cv2.rectangle(image, (0, h_img - 35), (w_img, h_img), (0, 0, 0), -1)
                cv2.putText(image, f"ConsisFit: {coach_text}", (10, h_img - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, coach_color, 2)

                ret, buffer = cv2.imencode('.jpg', image)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except GeneratorExit:
            pass
        finally:
            cap.release()
            if java_backend is not None and rep_count > 0:
                m_type = "Seconds" if EXERCISE_CONFIG[exercise]["mode"] == "time" else "Reps"
                try:
                    java_backend.processVideoResult(exercise, rep_count, m_type)
                except Exception as e:
                    print(f"Error saving to Java: {e}")
