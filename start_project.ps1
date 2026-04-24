Write-Host "Starting Nexus Infrastructure..."
docker-compose up -d

$ready = $false
while (-not $ready) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000" -Method Head -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) { $ready = $true }
    } catch {
        Start-Sleep -Seconds 2
    }
}

Start-Process "http://localhost:5000/admin_dashboard"
Write-Host "Nexus is running. Use docker-compose down to stop."