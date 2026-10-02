@echo off
echo =========================================
echo Setting up Optimal Routing API...
echo =========================================

echo.
echo [1/2] Creating Python virtual environment...
python -m venv venv

echo.
echo [2/2] Activating virtual environment and installing dependencies...
call venv\Scripts\activate
pip install django djangorestframework requests pandas numpy scikit-learn polyline

echo.
echo =========================================
echo Setup Complete! 
echo You can now double-click 'run_server.bat' to start the API.
echo =========================================
pause
