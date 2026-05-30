package org.example.database;

import org.example.interfaces.IDataOperations;
import org.example.models.WorkoutSession;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

public class WorkoutDatabase implements IDataOperations {
    private static WorkoutDatabase instance;
    private final String DB_PATH = "workout_history.csv";
    private final String PROFILE_PATH = "user_profile.csv";

    private WorkoutDatabase() {}

    public static WorkoutDatabase getInstance() { 
        if (instance == null) instance = new WorkoutDatabase();
        return instance;
    }

    @Override
    public void insert(WorkoutSession session) {
        try (PrintWriter out = new PrintWriter(new BufferedWriter(new FileWriter(DB_PATH, true)))) {
            out.println(session.toCSV());
        } catch (IOException e) { 
            System.err.println("Java Database Insertion Error: " + e.getMessage()); 
        }
    }

    public boolean hasUserProfile() {
        return new File(PROFILE_PATH).exists();
    }

    public void saveUserProfile(String age, String weight, String height, String gender, String goal) {
        try (PrintWriter out = new PrintWriter(new FileWriter(PROFILE_PATH, false))) {
            out.println(age + "," + weight + "," + height + "," + gender + "," + goal);
        } catch (IOException e) { 
            System.err.println("Java Profile Exception: " + e.getMessage()); 
        }
    }

    public String getUserProfile() {
        if (!hasUserProfile()) return "NONE";
        try (BufferedReader br = new BufferedReader(new FileReader(PROFILE_PATH))) {
            return br.readLine();
        } catch (IOException e) { 
            return "ERROR"; 
        }
    }
}
