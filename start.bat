@echo off
setlocal
title Social Network Teaching Platform - Start
cd /d "%~dp0"

echo ============================================
echo   Social Network Teaching Platform
echo   One-click start (backend + frontend)
echo ============================================
echo.

echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)
python -c "import django, rest_framework, networkx, celery" >nul 2>&1
if errorlevel 1 (
    echo First run: installing backend dependencies, about 1-2 minutes...
    python -m pip install -e "backend[dev]"
    if errorlevel 1 (
        echo [ERROR] Backend dependency install failed. Check network and retry.
        pause
        exit /b 1
    )
)

echo [2/5] Initializing database and seeding teaching cases...
python backend/manage.py migrate --noinput
if errorlevel 1 ( echo [ERROR] migrate failed & pause & exit /b 1 )
python backend/manage.py seed_learning_content
if errorlevel 1 ( echo [ERROR] seed failed & pause & exit /b 1 )

echo [3/5] Checking Node.js and frontend dependencies...
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js 20+ and add it to PATH.
    pause
    exit /b 1
)
if not exist "frontend\node_modules" (
    echo First run: installing frontend dependencies, about 2-5 minutes...
    cd frontend
    call npm install
    if errorlevel 1 (
        cd ..
        echo [ERROR] Frontend dependency install failed. Check network and retry.
        pause
        exit /b 1
    )
    cd ..
)

echo [4/5] Starting backend and frontend...
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    start "SNA-backend-8000" cmd /k "cd /d %~dp0 && python backend/manage.py runserver 127.0.0.1:8000 --noreload"
    echo   backend started: http://127.0.0.1:8000  (new window)
) else (
    echo   backend already running on port 8000, skip.
)
netstat -ano | findstr ":5173 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    start "SNA-frontend-5173" cmd /k "cd /d %~dp0frontend && npm run dev"
    echo   frontend started: http://localhost:5173  (new window)
) else (
    echo   frontend already running on port 5173, skip.
)

echo [5/5] Waiting for services, then opening browser...
ping -n 9 127.0.0.1 >nul
start http://localhost:5173

echo.
echo ============================================
echo   Done! Browser opened at http://localhost:5173
echo   To stop: run stop.bat, or close the
echo   SNA-backend-8000 / SNA-frontend-5173 windows.
echo   Teacher admin: http://127.0.0.1:8000/admin/
echo ============================================
echo.
pause
