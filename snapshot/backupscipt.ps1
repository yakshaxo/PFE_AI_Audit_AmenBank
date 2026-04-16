# 1. Define where to save the backup
$date = Get-Date -Format "yyyyMMdd_HHmm"
$backupDir = "C:\Users\lenovo\PFE_AI_Audit_AmenBank\backups"
$backupFile = "$backupDir\ai_audit_snapshot_$date.sql"

# 2. Create the folder if it doesn't exist
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir }

# 3. Execute the Docker Snapshot
Write-Host "Starting snapshot for ai_audit..." -ForegroundColor Cyan
docker exec pfe_postgres pg_dump -U zabbix ai_audit > $backupFile

# 4. Success check
if (Test-Path $backupFile) {
    Write-Host "Snapshot successfully saved to: $backupFile" -ForegroundColor Green
} else {
    Write-Host "Error: Snapshot failed." -ForegroundColor Red
}

# 5. Cleanup: Keep only the last 30 days of backups
Get-ChildItem "$backupDir\*" | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } | Remove-Item