package org.example.models;

public class DigestedWorkout extends WorkoutSession {
    private final String exerciseName;
    private int repCount;
    private final String metricType;

    public DigestedWorkout(String id, String timestamp, String exerciseName, int repCount, String metricType) {
        super(id, timestamp);
        this.exerciseName = exerciseName;
        this.repCount = repCount;
        this.metricType = metricType;
    }

    @Override
    public String toCSV() {
        return getId() + "," + exerciseName + "," + repCount + " " + metricType + "," + getTimestamp();
    }
}
