@echo off
SET ROOT_DIR=ai-service

echo Creating directory structure %ROOT_DIR%...

mkdir %ROOT_DIR%
cd %ROOT_DIR%

mkdir routes
mkdir services
mkdir middleware
mkdir models

echo. > main.py
echo. > routes\chat.py
echo. > services\groq.py
echo. > middleware\auth.py
echo. > models\schemas.py
echo. > requirements.txt
echo. > .env

echo Completion! Directory structure has been created at: %cd%
pause
