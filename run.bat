@echo off
setlocal

if /I not "%~1"=="sentiment" (
  echo Usage: run sentiment
  exit /b 1
)

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "PYTHON=%BACKEND%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Creating the backend virtual environment...
  python -m venv "%BACKEND%\.venv" || exit /b 1
)

"%PYTHON%" -c "import fastapi, uvicorn, torch, transformers, multipart" >nul 2>&1
if errorlevel 1 (
  echo Installing backend dependencies. This can take a few minutes the first time...
  "%PYTHON%" -m pip install -r "%BACKEND%\requirements.txt" || exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
  echo Installing frontend dependencies...
  pushd "%FRONTEND%"
  call npm install || (popd & exit /b 1)
  popd
)

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if errorlevel 1 (
  start "Sentiment Analyzer API" /D "%BACKEND%" cmd /k ".venv\Scripts\python.exe -m uvicorn main:app --reload"
) else (
  echo Backend is already running on http://localhost:8000
)

netstat -ano | findstr /R /C:":5173 .*LISTENING" >nul
if errorlevel 1 (
  start "Sentiment Analyzer Frontend" /D "%FRONTEND%" cmd /k "npm run dev"
) else (
  echo Frontend is already running on http://localhost:5173
)

echo.
echo Sentiment Analyzer is starting.
echo Open http://localhost:5173
echo API docs: http://localhost:8000/docs
