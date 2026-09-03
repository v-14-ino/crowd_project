Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting Municipality Crowd Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$backendPort = 8000
$frontendPort = 5173
$backendUrl = "http://127.0.0.1:$backendPort"
$frontendUrl = "http://localhost:$frontendPort"

$backendRunning = $false
try {
    $response = Invoke-WebRequest -Uri "$backendUrl/health" -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $backendRunning = $true
        Write-Host "[OK] Backend is already running on $backendUrl" -ForegroundColor Green
    }
} catch {
    Write-Host "[..] Backend not found on port $backendPort. Starting..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd backend && uvicorn main:app --host 127.0.0.1 --port $backendPort"
}

$frontendRunning = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("127.0.0.1", $frontendPort)
    $tcp.Close()
    $frontendRunning = $true
    Write-Host "[OK] Frontend is already running on port $frontendPort" -ForegroundColor Green
} catch {
    Write-Host "[..] Frontend not found on port $frontendPort. Starting..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd frontend && npm run dev -- --host 127.0.0.1 --port $frontendPort"
}

Write-Host ""
Write-Host "Waiting for backend health check ($backendUrl/health)..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "$backendUrl/health" -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($ready) {
    Write-Host "[OK] Backend is ready." -ForegroundColor Green
    Write-Host "[OK] Opening $frontendUrl in default browser..." -ForegroundColor Green
    Start-Sleep -Seconds 2
    Start-Process $frontendUrl
} else {
    Write-Host "[ERROR] Backend did not become ready within 30 seconds." -ForegroundColor Red
    Write-Host "Please check the backend terminal for errors." -ForegroundColor Red
}

Write-Host ""
Write-Host "=========================================="
Write-Host " Backend:  $backendUrl"
Write-Host " Frontend: $frontendUrl"
Write-Host "=========================================="
Write-Host "You may close this launcher window (Servers will remain running in their own windows)."
