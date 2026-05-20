@echo off
set EXE_NAME=1820232048project1
cd /d "%~dp0"
python -m venv venv
call venv\Scripts\activate.bat
pip install pyinstaller -q
set PYTHONPATH=src
pyinstaller --noconfirm --onefile --name %EXE_NAME% --paths src --hidden-import config_loader --hidden-import pdu --hidden-import crc_ccitt --hidden-import channel --hidden-import logger src\gbn_host.py
copy /Y dist\%EXE_NAME%.exe .
echo SUCCESS: %CD%\%EXE_NAME%.exe
pause
