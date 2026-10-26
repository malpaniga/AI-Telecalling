param(
    [string]$Message = "Update platform",
    [string]$KeyPath = "",
    [string]$Server = "92.5.149.29",
    [string]$User = "ubuntu"
)

$ErrorActionPreference = "Stop"

# Auto-locate SSH key if not specified
if (-not $KeyPath) {
    $possiblePaths = @(
        "C:\Programs\ssh-key.key",
        "$PSScriptRoot\..\ssh-key.key",
        "$PSScriptRoot\ssh-key.key"
    )
    foreach ($p in $possiblePaths) {
        if (Test-Path $p) {
            $KeyPath = (Resolve-Path $p).Path
            break
        }
    }
}

if (-not $KeyPath -or -not (Test-Path $KeyPath)) {
    Write-Host "[ERROR] Could not find ssh-key.key! Please specify -KeyPath" -ForegroundColor Red
    exit 1
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  [DEPLOY] AI Telecalling Auto-Redeploy" -ForegroundColor Cyan
Write-Host "  Server: $User@$Server" -ForegroundColor Cyan
Write-Host "  SSH Key: $KeyPath" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Git push for Vercel
Write-Host "`n[1/4] Pushing changes to GitHub (triggers Vercel frontend build)..." -ForegroundColor Yellow
try {
    git add .
    $status = git status --porcelain
    if ($status) {
        git commit -m $Message
        Write-Host "  [OK] Committed local changes." -ForegroundColor Green
    }
    
    # Check if local branch is ahead of origin
    $unpushed = git log '@{u}..HEAD' --oneline 2>$null
    if ($unpushed -or $status) {
        git push origin HEAD
        Write-Host "  [OK] GitHub updated. Vercel is redeploying the frontend." -ForegroundColor Green
    } else {
        Write-Host "  [INFO] No new changes to push to GitHub." -ForegroundColor DarkGray
    }
} catch {
    Write-Host "  [WARN] Git warning: $_ (proceeding with backend deploy)" -ForegroundColor DarkYellow
}

# 2. Package backend and configs
Write-Host "`n[2/4] Packaging project for Oracle Cloud..." -ForegroundColor Yellow
$tarFile = "$PSScriptRoot\app.tar.gz"
if (Test-Path $tarFile) { Remove-Item $tarFile -Force }

tar -czf "$tarFile" `
    --exclude='.venv' `
    --exclude='node_modules' `
    --exclude='.next' `
    --exclude='.git' `
    --exclude='app.tar.gz' `
    -C "$PSScriptRoot" .

$tarItem = Get-Item $tarFile
$tarSize = [math]::Round($tarItem.Length / 1MB, 2)
Write-Host "  [OK] Compressed into $tarSize MB archive" -ForegroundColor Green

# 3. Upload to server
Write-Host "`n[3/4] Uploading to Oracle Cloud server..." -ForegroundColor Yellow
scp -i "$KeyPath" "$tarFile" "${User}@${Server}:~/"
Remove-Item $tarFile -Force -ErrorAction SilentlyContinue
Write-Host "  [OK] Upload complete." -ForegroundColor Green

# 4. Extract and rebuild containers on server
Write-Host "`n[4/4] Rebuilding Docker containers on server..." -ForegroundColor Yellow
$remoteCommands = "mkdir -p ~/saas && tar -xzf ~/app.tar.gz -C ~/saas && rm -f ~/app.tar.gz && cd ~/saas && docker compose -f docker-compose.prod.yml up -d --build"
ssh -i "$KeyPath" "${User}@${Server}" "$remoteCommands"

Write-Host "`n[OK] All containers updated!" -ForegroundColor Green

# 5. Quick Health Check
Write-Host "`n[Verification] Testing backend health..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
try {
    $res = curl.exe -s "http://${Server}/health"
    Write-Host "  Backend Response: $res" -ForegroundColor Green
} catch {
    Write-Host "  Could not verify health check directly, check http://${Server}/health" -ForegroundColor DarkYellow
}

Write-Host "`n[SUCCESS] Redeployment finished successfully!" -ForegroundColor Cyan
