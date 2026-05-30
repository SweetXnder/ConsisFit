# ConsisFit - AI Personal Trainer & Calisthenics Tracker

ConsisFit is a data-driven, object-oriented fitness application designed to track calisthenics progression, monitor real-time exercise form using Computer Vision, and provide personalized nutritional insights via an AI Coach. 

This project was built to demonstrate advanced Object-Oriented Programming (OOP) principles, robust file transactions, and cross-runtime system architecture.

## Key Features
* **Computer Vision Tracking:** Real-time skeletal tracking and rep counting using OpenCV and MediaPipe.
* **OOP File Persistence:** Secure insert and update transactions for workout logs and user profiles via a Java backend.
* **AI Coaching System:** Integrated Groq LLM provides dynamically calculated macronutrients and situational RAG (Retrieval-Augmented Generation) coaching.
* **Interactive Progression Hub:** A responsive, cyberpunk-themed HTML/JS dashboard tracking Total Volume, Level/XP, and Personal Records (PRs).

## System Architecture & OOP Design
ConsisFit utilizes a **Client-Server Architecture** bridging a Python application layer with a secure Java database layer. 

* **The Facade Pattern (Python):** A Flask server acts as a unified interface (Facade) capturing web traffic, managing the AI pipeline, and utilizing `Py4J` to safely pass data to the Java core.
* **The Singleton Pattern (Java):** The `WorkoutDatabase.java` utilizes a thread-safe Singleton design to prevent multi-thread file-locking conflicts during IO read/write operations on `.csv` files.
* **Inheritance & Polymorphism:** Workout data is modeled using an abstract `WorkoutSession` class, extended by a `DigestedWorkout` subclass to allow dynamic metric serialization across different exercises.
* **Encapsulation:** Biometric states (`UserProfile`) are heavily protected with private access modifiers and defensive getter/setter boundaries.

## Tech Stack
* **Frontend:** HTML5, CSS3 (Custom Cyberpunk UI), Vanilla JavaScript
* **Facade / App Server:** Python 3.12, Flask, Py4J
* **Computer Vision Engine:** OpenCV, MediaPipe
* **AI Engine:** Groq API (Llama-3)
* **Persistence / OOP Core:** Java 

## Setup & Installation

**1. Prerequisites**
* Java Development Kit (JDK 8 or higher)
* Python 3.x
* A valid Groq API Key

**2. Python Dependencies**
Navigate to the project directory and install the required Python libraries:
```bash
pip install flask opencv-python mediapipe py4j groq werkzeug