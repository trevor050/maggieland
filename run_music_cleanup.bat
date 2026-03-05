@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "EXE=%SCRIPT_DIR%music-cleanup.exe"
set "CONFIG=%SCRIPT_DIR%cleanup.config.yml"

if not exist "%EXE%" (
  echo [ERROR] music-cleanup.exe not found in:
  echo %SCRIPT_DIR%
  pause
  exit /b 1
)

if not exist "%CONFIG%" (
  echo [ERROR] cleanup.config.yml not found.
  echo Please copy cleanup.config.example.yml to cleanup.config.yml and edit it.
  pause
  exit /b 1
)

echo Running music cleanup...
"%EXE%" --config "%CONFIG%"
set "ERR=%ERRORLEVEL%"

echo.
if "%ERR%"=="0" (
  echo Done. Check your output folder for songs/, non-songs/, report.csv, and review.csv.
) else (
  echo Finished with errors. Check logs and report files in output directory.
)

echo.
pause
exit /b %ERR%
