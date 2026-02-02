# Taggarr Windows Service Installer
# Requires: NSSM (https://nssm.cc/download) in PATH
# Run as Administrator

$serviceName = "taggarr"
$uvPath = "$env:USERPROFILE\.local\bin\uv.exe"
$workDir = "$env:USERPROFILE\taggarr"

# Check if NSSM is available
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Error "NSSM not found. Download from https://nssm.cc/download and add to PATH"
    exit 1
}

# Check if uv is installed
if (-not (Test-Path $uvPath)) {
    Write-Error "uv not found at $uvPath. Install from https://docs.astral.sh/uv/"
    exit 1
}

# Check if workdir exists
if (-not (Test-Path $workDir)) {
    Write-Error "Taggarr directory not found at $workDir"
    exit 1
}

# Create logs directory
$logsDir = "$workDir\logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

# Install service
Write-Host "Installing taggarr service..."
nssm install $serviceName $uvPath run taggarr --loop
nssm set $serviceName AppDirectory $workDir
nssm set $serviceName AppStdout "$logsDir\service.log"
nssm set $serviceName AppStderr "$logsDir\service.error.log"
nssm set $serviceName AppRotateFiles 1
nssm set $serviceName AppRotateBytes 10485760

# Start service
Write-Host "Starting taggarr service..."
nssm start $serviceName

Write-Host "Done! Check status with: nssm status $serviceName"
