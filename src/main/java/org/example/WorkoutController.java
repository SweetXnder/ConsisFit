package org.example;

import org.example.database.WorkoutDatabase;
import org.example.models.DigestedWorkout;
import org.example.models.WorkoutSession;
import py4j.GatewayServer;

import java.util.Date;
import java.util.Random;

public class WorkoutController {
    private final WorkoutDatabase db = WorkoutDatabase.getInstance();

    public String processVideoResult(String exercise, int count, String metricType) {
        String id = "LOG-" + (10000 + new Random().nextInt(89999));
        String date = new Date().toString();
        WorkoutSession session = new DigestedWorkout(id, date, exercise, count, metricType);
        db.insert(session);
        return "Java Server System Success: Logged " + count + " " + metricType + " for " + exercise;
    }

    public boolean checkProfileExists() { return db.hasUserProfile(); }
    public String fetchProfile() { return db.getUserProfile(); }
    public String registerUser(String age, String weight, String height, String gender, String goal) {
        // 1. Update the database
        db.saveUserProfile(age, weight, height, gender, goal);

        return "Profile Registration Confirmed";
    }

    public static void main(String[] args) {
        WorkoutController app = new WorkoutController();
        GatewayServer server = new GatewayServer(app);
        server.start();
        System.out.println("ConsisFit Java Server Framework: ONLINE. Port 25333 Listening...");
    }
}
