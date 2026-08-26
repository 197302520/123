@echo off
setlocal
title Social Network Teaching Platform - Stop

echo Stopping platform services...

rem Close windows opened by start.bat (and their child processes)
taskkill /FI "WINDOWTITLE eq SNA-backend-8000*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq SNA-frontend-5173*" /T /F >nul 2>&1

rem Fallback: kill any process still listening on the ports
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1

echo All services stopped (backend 8000 / frontend 5173).
pause
