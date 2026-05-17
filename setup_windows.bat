@echo off
echo  Setting up ConsisFit for Windows...

:: Create and activate virtual environment
python -m venv venv
call venv\Scripts\activate.bat

:: Install Python dependencies
echo  Installing Python libraries...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Compile Java backend
echo  Compiling Java Backend via Maven...
call mvn clean compile

echo.
echo  Setup Complete!
echo --------------------------------------------------------
echo To run the Java server (Open a new command prompt):
echo mvn exec:java -Dexec.mainClass="org.example.WorkoutController"
echo.
echo To run the Python server (In this command prompt):
echo call venv\Scripts\activate.bat
echo python src\main\python\main.py
echo --------------------------------------------------------
pause
