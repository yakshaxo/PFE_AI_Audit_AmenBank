@echo off
REM Batch Script to Setup PFE AI Audit Project Structure
REM Run this from your project root: C:\Users\lenovo\PFE_AI_Audit_AmenBank

echo.
echo ======================================
echo  Setting up PFE AI Audit Project
echo ======================================
echo.

REM Create directories
echo Creating folder structure...
mkdir zabbix 2>nul
mkdir zabbix\config 2>nul
mkdir grafana 2>nul
mkdir grafana\dashboards 2>nul
mkdir grafana\provisioning 2>nul
mkdir grafana\provisioning\dashboards 2>nul
mkdir grafana\provisioning\datasources 2>nul
mkdir postgres 2>nul
mkdir postgres\init 2>nul
mkdir ai-chatbot 2>nul
mkdir ai-chatbot\app 2>nul
mkdir ai-chatbot\models 2>nul
mkdir auth-service 2>nul
mkdir auth-service\app 2>nul
mkdir docs 2>nul

echo   [OK] Folders created!
echo.

echo Creating .gitignore file...
(
echo # Python
echo __pycache__/
echo *.py[cod]
echo *.so
echo .Python
echo venv/
echo env/
echo.
echo # Environment variables
echo .env
echo.
echo # Database
echo *.db
echo *.sqlite3
echo postgres/data/
echo.
echo # Docker volumes
echo grafana/data/
echo zabbix/data/
echo.
echo # AI Models
echo ai-chatbot/models/*.bin
echo ai-chatbot/models/*.gguf
echo ai-chatbot/models/*.pt
echo.
echo # IDE
echo .vscode/
echo .idea/
echo *.swp
echo.
echo # OS
echo .DS_Store
echo Thumbs.db
echo.
echo # Logs
echo *.log
) > .gitignore

echo   [OK] .gitignore created!
echo.

echo Setup complete!
echo.
echo Next steps:
echo   1. I will create remaining files manually for you
echo   2. Edit .env with your passwords
echo   3. Run: docker-compose up -d
echo.
pause
