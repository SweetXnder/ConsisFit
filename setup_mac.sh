#!/bin/bash
echo "Setting up ConsisFit for macOS/Linux..."

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo " Installing Python libraries..."
pip install --upgrade pip
pip install -r requirements.txt

# Compile Java backend
echo " Compiling Java Backend via Maven..."
mvn clean compile

echo ""
echo "Setup Complete!"
echo "--------------------------------------------------------"
echo "To run the Java server (Open a new terminal tab):"
echo "mvn exec:java -Dexec.mainClass=\"org.example.WorkoutController\""
echo ""
echo "To run the Python server (In this terminal tab):"
echo "source venv/bin/activate"
echo "python src/main/python/main.py"
echo "--------------------------------------------------------"
