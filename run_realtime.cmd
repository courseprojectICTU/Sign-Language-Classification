@echo off
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM 1. Tim Python 3.12 tren he thong
set "PYTHON_EXE="
for /f "delims=" %%I in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do (
  set "PYTHON_EXE=%%I"
)

REM 2. Fallback neu py launcher khong co: doc tu pyvenv.cfg
if "%PYTHON_EXE%"=="" (
  if exist "%ROOT%\.venv\pyvenv.cfg" (
    for /f "tokens=1,2 delims==" %%A in ('type "%ROOT%\.venv\pyvenv.cfg" 2^>nul') do (
      if /i "%%A"=="executable " set "PYTHON_EXE=%%B"
      if /i "%%A"=="executable" set "PYTHON_EXE=%%B"
    )
  )
)

REM 3. Fallback duong dan mac dinh may nay
if "%PYTHON_EXE%"=="" set "PYTHON_EXE=D:\program\python\python.exe"

REM Kiem tra ton tai
if not exist "%PYTHON_EXE%" (
  echo [LOI] Khong tim thay Python 3.12 tren may.
  echo       Vui long cai dat Python 3.12 theo HUONG-DAN-CHAY.md
  pause
  exit /b 1
)

REM Thiet lap PYTHONPATH tro vao .venv cua project
set "PYTHONPATH=%ROOT%\.venv\Lib\site-packages;%PYTHONPATH%"
set "__PYVENV_LAUNCHER__=%ROOT%\.venv\Scripts\python.exe"

echo Dang khoi dong nhan dien ky hieu truc tiep...
echo Dung Python: %PYTHON_EXE%
"%PYTHON_EXE%" "%ROOT%\run_realtime.py"
endlocal
