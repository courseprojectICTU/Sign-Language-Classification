@echo off
REM ---------------------------------------------------------------------------
REM Launcher for Jupyter in this project.
REM See HUONG-DAN-CHAY.md section 9.3 for the full explanation.
REM
REM Why this exists: on this machine python.exe can only write files INSIDE the
REM project folder. Jupyter defaults to C:\Users\<you>\.jupyter, which fails with
REM     PermissionError: [Errno 13] Permission denied: ...\.jupyter\migrated
REM Redirecting config/data/runtime into the project avoids that entirely.
REM
REM A .cmd file is used instead of .ps1 because this machine's PowerShell
REM execution policy refuses to load unsigned .ps1 scripts.
REM
REM Usage:
REM     run_notebook.cmd
REM     run_notebook.cmd --port 8888
REM ---------------------------------------------------------------------------

setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "JUPYTER_CONFIG_DIR=%ROOT%\.jupyter-config"
set "JUPYTER_DATA_DIR=%ROOT%\.jupyter-data"
set "JUPYTER_RUNTIME_DIR=%ROOT%\.jupyter-runtime"

if not exist "%JUPYTER_CONFIG_DIR%"  mkdir "%JUPYTER_CONFIG_DIR%"
if not exist "%JUPYTER_DATA_DIR%"    mkdir "%JUPYTER_DATA_DIR%"
if not exist "%JUPYTER_RUNTIME_DIR%" mkdir "%JUPYTER_RUNTIME_DIR%"

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo [LOI] Khong tim thay .venv\Scripts\python.exe
  echo       Xem HUONG-DAN-CHAY.md de tao moi truong.
  exit /b 1
)

REM 1. Tim Python 3.12 tren he thong
set "PYTHON_EXE="
for /f "delims=" %%I in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do (
  set "PYTHON_EXE=%%I"
)

REM 2. Fallback doc tu pyvenv.cfg
if "%PYTHON_EXE%"=="" (
  if exist "%ROOT%\.venv\pyvenv.cfg" (
    for /f "tokens=1,2 delims==" %%A in ('type "%ROOT%\.venv\pyvenv.cfg" 2^>nul') do (
      if /i "%%A"=="executable " set "PYTHON_EXE=%%B"
      if /i "%%A"=="executable" set "PYTHON_EXE=%%B"
    )
  )
)

if "%PYTHON_EXE%"=="" (
  for /f "delims=" %%I in ('where python 2^>nul') do (
    if "%PYTHON_EXE%"=="" set "PYTHON_EXE=%%I"
  )
)

set "PYTHONPATH=%ROOT%\.venv\Lib\site-packages;%PYTHONPATH%"
set "__PYVENV_LAUNCHER__=%ROOT%\.venv\Scripts\python.exe"

echo Jupyter config -^> %JUPYTER_CONFIG_DIR%
echo Python kernel  -^> %PYTHON_EXE%

REM Launch Jupyter notebook
"%PYTHON_EXE%" -m notebook %*
endlocal
