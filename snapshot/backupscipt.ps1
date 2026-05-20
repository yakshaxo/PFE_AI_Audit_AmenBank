# 1. Define where to save the backup - UPDATED TO NEXUS DIRECTORY
$date = Get-Date -Format "yyyyMMdd_HHmm"
$backupDir = "C:\Users\lenovo\NEXUS\backups"
$backupFile = "$backupDir\ai_audit_snapshot_$date.sql"

# 2. Create the folder if it doesn't exist
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir }

# 3. Execute the Docker Snapshot (With Password Injection)
Write-Host "Starting snapshot for ai_audit..." -ForegroundColor Cyan

# Injecting the password from your .env to prevent manual prompts
$env:PGPASSWORD = "StrongPassword123" 
docker exec -e PGPASSWORD=$env:PGPASSWORD pfe_postgres pg_dump -U zabbix ai_audit > $backupFile
$env:PGPASSWORD = $null # Security: Clear password from memory

# 4. Success check
if (Test-Path $backupFile) {
    Write-Host "Snapshot successfully saved to: $backupFile" -ForegroundColor Green
} else {
    Write-Host "Error: Snapshot failed." -ForegroundColor Red
}

# 5. Cleanup: Keep only the last 30 days of backups
Get-ChildItem "$backupDir\*" | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | Remove-Item