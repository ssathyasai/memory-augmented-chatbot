@echo off
echo Starting Memory-Augmented Chatbot...
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Download spaCy model if needed
echo Checking spaCy model...
python -m spacy download en_core_web_sm

REM Create necessary directories
if not exist "vector_stores" mkdir vector_stores
if not exist "logs" mkdir logs

REM Check for .env file
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and configure your settings.
    echo.
    pause
    exit /b 1
)

REM Run Streamlit app
echo.
echo Starting Streamlit app...
streamlit run app.py

pause
