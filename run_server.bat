@echo off
echo =========================================
echo Starting Optimal Routing API...
echo =========================================

echo.
echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Starting Django Server...
python manage.py runserver

pause
