@echo off
python -m pip install --upgrade pip

:: Create the virtual environment if it doesn't exist
if not exist venv (
    python -m venv venv
)

:: Activate the virtual environment
call venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt

echo Libraries installed successfully.
pause