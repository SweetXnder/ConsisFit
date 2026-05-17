package org.example.models;

public abstract class WorkoutSession {
    private final String id;
    private final String timestamp;

    public WorkoutSession(String id, String timestamp) {
        this.id = id;
        this.timestamp = timestamp;
    }
    public String getId() { return id; }
    public String getTimestamp() { return timestamp; }
    public abstract String toCSV();
}
