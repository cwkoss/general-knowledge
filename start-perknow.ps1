#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick start script for Perknow knowledge management system
.DESCRIPTION
    Starts the Perknow web server and AI gardener worker, finding an available port automatically
#>

param(
    [int]$StartPort = 8000,
    [int]$MaxPort = 9000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

# Colors for output
$Green = "`e[32m"
$Yellow = "`e[33m"
$Red = "`e[31m"
$Blue = "`e[34m"
$Reset = "`e[0m"

function Write-Status($message, $color = $Green) {
    Write-Host "$color[PERKNOW]$Reset $message"
}

function Write-Error($message) {
    Write-Host "$Red[ERROR]$Reset $message"
}

function Write-Info($message) {
    Write-Host "$Blue[INFO]$Reset $message"
}

function Write-Warn($message) {
    Write-Host "$Yellow[WARN]$Reset $message"
}

# Check if we're in the right directory
if (-not (Test-Path "perknow/main.py")) {
    Write-Error "Not in perknow project root directory. Please cd to the project folder."
    exit 1
}

Write-Status "Starting Perknow Knowledge Management System..."
Write-Info "Project directory: $(Get-Location)"

# Check Python/uvicorn availability
try {
    $uvicornVersion = uvicorn --version 2>&1
    Write-Info "Uvicorn found: $uvicornVersion"
} catch {
    Write-Error "uvicorn not found. Run: pip install -r requirements.txt"
    exit 1
}

# Check Ollama
try {
    $ollamaPs = Get-Process ollama -ErrorAction SilentlyContinue
    if (-not $ollamaPs) {
        Write-Warn "Ollama process not detected. Attempting to start..."
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    }
    
    # Test Ollama API
    $testResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 5
    Write-Info "Ollama is running at http://localhost:11434"
    
    # Check for required models
    $requiredModels = @("nomic-embed-text", "llama3.2")
    $availableModels = $testResponse.models | ForEach-Object { $_.name }
    
    foreach ($model in $requiredModels) {
        $found = $availableModels | Where-Object { $_ -like "$model*" }
        if ($found) {
            Write-Info "Model ready: $found"
        } else {
            Write-Warn "Model not found: $model. Run: ollama pull $model"
        }
    }
} catch {
    Write-Error "Ollama not responding. Ensure Ollama is installed and running."
    Write-Info "Download from: https://ollama.com/download"
    exit 1
}

# Find available port
Write-Info "Searching for available port starting from $StartPort..."
$port = $StartPort
$foundPort = $false

while ($port -lt $MaxPort) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if (-not $connection) {
        $foundPort = $true
        break
    }
    $port++
}

if (-not $foundPort) {
    Write-Error "No available ports found between $StartPort and $MaxPort"
    exit 1
}

Write-Status "Found available port: $port"

# Initialize directories
$dataDir = "data"
$exportDir = "export"

if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
    Write-Info "Created directory: $dataDir"
}

if (-not (Test-Path $exportDir)) {
    New-Item -ItemType Directory -Path $exportDir | Out-Null
    Write-Info "Created directory: $exportDir"
}

# Initialize git in export if not already
if (-not (Test-Path "$exportDir/.git")) {
    Write-Info "Initializing git repository in export/"
    Push-Location $exportDir
    git init 2>&1 | Out-Null
    Pop-Location
}

# Start the gardener worker in a new window
Write-Status "Starting AI Gardener worker..."
$gardenerJob = Start-Job -ScriptBlock {
    param($location)
    Set-Location $location
    python scripts/gardener_worker.py
} -ArgumentList (Get-Location)

Start-Sleep -Seconds 1

# Check if gardener started
if ($gardenerJob.State -eq "Failed") {
    Write-Error "Gardener worker failed to start"
    Receive-Job $gardenerJob
    exit 1
}

Write-Status "Gardener worker started (Job ID: $($gardenerJob.Id))"

# Start the web server
Write-Status "Starting web server on http://localhost:$port ..."
Write-Info "Press Ctrl+C to stop both server and gardener"

if (-not $NoBrowser) {
    # Open browser after a short delay
    Start-Job -ScriptBlock {
        param($port)
        Start-Sleep -Seconds 3
        Start-Process "http://localhost:$port"
    } -ArgumentList $port | Out-Null
}

try {
    # Run uvicorn (this blocks until Ctrl+C)
    uvicorn perknow.main:app --host 0.0.0.0 --port $port --reload
} finally {
    # Cleanup on exit
    Write-Host "`n"
    Write-Warn "Shutting down..."
    
    # Stop the gardener job
    if ($gardenerJob) {
        Stop-Job $gardenerJob
        Remove-Job $gardenerJob
        Write-Info "Gardener worker stopped"
    }
    
    Write-Status "Perknow stopped. Goodbye!"
}
