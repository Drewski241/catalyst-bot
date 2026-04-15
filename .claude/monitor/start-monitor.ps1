# ============================================================
# CATalyst Bot Monitor — Session Starter
# ============================================================
# Run this script to kick off a fresh Claude Code monitor
# session with the right starting context.
#
# Usage: .\start-monitor.ps1
#
# What this does:
# 1. Verifies the bot is actually running (exits if not)
# 2. Checks that monitor.log is writable
# 3. Releases any stale monitor.lock (older than 10 min)
# 4. Prints the exact first prompt the new Claude session should execute
#
# You then copy that prompt into a new `claude` CLI session.
# ============================================================

$ErrorActionPreference = "Stop"

$REPO = "C:\chia_liquidity_bot_v2_v4_tauri"
$MONITOR_DIR = "$REPO\.claude\monitor"
$ENV_FILE = "$env:APPDATA\ChiaMarketMaker\.env"

Write-Host "=== CATalyst Monitor Startup ===" -ForegroundColor Cyan
Write-Host ""

# --- 1. Is the bot running? ---
Write-Host "[1/4] Checking bot process..."
$botRunning = $false
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/status" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    if ($resp.StatusCode -eq 200 -or $resp.StatusCode -eq 401) {
        $botRunning = $true
        Write-Host "      ✓ Bot is responding on port 5000" -ForegroundColor Green
    }
} catch {
    Write-Host "      ✗ Bot is NOT responding on port 5000" -ForegroundColor Red
    Write-Host ""
    Write-Host "The bot must be running before you start the monitor." -ForegroundColor Yellow
    Write-Host "Start the bot (python desktop_app.py) then re-run this script." -ForegroundColor Yellow
    exit 1
}

# --- 2a. Initialize MEMORY.md from template if missing ---
Write-Host "[2/5] Checking MEMORY.md..."
$memFile = "$MONITOR_DIR\MEMORY.md"
$memTemplate = "$MONITOR_DIR\MEMORY.md.template"
if (-not (Test-Path $memFile)) {
    if (Test-Path $memTemplate) {
        Copy-Item $memTemplate $memFile
        Write-Host "      ✓ Initialized MEMORY.md from template" -ForegroundColor Green
    } else {
        Write-Host "      ✗ MEMORY.md.template missing. Cannot proceed." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "      ✓ MEMORY.md exists ($(([System.IO.FileInfo]$memFile).Length) bytes) — preserving history"
}

# --- 2b. Check monitor.log writability ---
Write-Host "[3/5] Checking monitor.log..."
$logFile = "$MONITOR_DIR\monitor.log"
if (-not (Test-Path $logFile)) {
    New-Item -ItemType File -Path $logFile -Force | Out-Null
    Write-Host "      ✓ Created $logFile" -ForegroundColor Green
} else {
    Write-Host "      ✓ $logFile exists ($(([System.IO.FileInfo]$logFile).Length) bytes)"
}

# Test write
try {
    $now = Get-Date -Format "o"
    "{`"ts`":`"$now`",`"event`":`"monitor_startup_script_ran`",`"script`":`"start-monitor.ps1`"}" | Add-Content $logFile
    Write-Host "      ✓ monitor.log is writable" -ForegroundColor Green
} catch {
    Write-Host "      ✗ Cannot write to monitor.log: $_" -ForegroundColor Red
    exit 1
}

# --- 3. Release stale lock ---
Write-Host "[4/5] Checking for stale lock..."
$lockFile = "$MONITOR_DIR\monitor.lock"
if (Test-Path $lockFile) {
    $lockAge = (Get-Date) - (Get-Item $lockFile).LastWriteTime
    if ($lockAge.TotalMinutes -gt 10) {
        Remove-Item $lockFile -Force
        Write-Host "      ✓ Removed stale lock (age: $([int]$lockAge.TotalMinutes) min)" -ForegroundColor Green
    } else {
        Write-Host "      ⚠ Active lock file present ($([int]$lockAge.TotalSeconds)s old)" -ForegroundColor Yellow
        Write-Host "      → Another monitor sweep may be running. Aborting." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "      ✓ No existing lock"
}

# --- 4. Verify .env is readable (for BOT_LOCAL_WRITE_TOKEN) ---
Write-Host "[5/5] Verifying .env access..."
if (-not (Test-Path $ENV_FILE)) {
    Write-Host "      ✗ .env file not found at $ENV_FILE" -ForegroundColor Red
    exit 1
}
$token = (Select-String -Path $ENV_FILE -Pattern "^BOT_LOCAL_WRITE_TOKEN=" | Select-Object -First 1).Line -replace "^BOT_LOCAL_WRITE_TOKEN=",""
$token = $token.Trim("'").Trim('"')
if (-not $token) {
    Write-Host "      ✗ BOT_LOCAL_WRITE_TOKEN not found in .env" -ForegroundColor Red
    exit 1
}
Write-Host "      ✓ Auth token parsed (length: $($token.Length))" -ForegroundColor Green

Write-Host ""
Write-Host "=== Ready to launch monitor session ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now start a fresh Claude Code session and paste this as your first message:" -ForegroundColor White
Write-Host ""
Write-Host "──────────────────────────────────────────────────────────────────" -ForegroundColor Gray

$prompt = @"
I am starting a fresh monitoring session for the CATalyst bot.

MANDATORY: Before doing anything else, read these three files in order:
  1. C:\chia_liquidity_bot_v2_v4_tauri\CLAUDE.md
  2. C:\chia_liquidity_bot_v2_v4_tauri\.claude\monitor\MEMORY.md
  3. C:\chia_liquidity_bot_v2_v4_tauri\.claude\monitor\MONITOR_PLAYBOOK.md

Then execute the onboarding sequence defined in MONITOR_PLAYBOOK.md Part 2:
  Step 1: context loaded (done by reading above)
  Step 2: module tour — use the Explore agent for each module listed in Part 2 Step 2
  Step 3: verify API access (bot, Dexie, Spacescan, Sage)
  Step 4: initialize/append to monitor.log
  Step 5: schedule Tier 1 (2min), Tier 2 (15min), Tier 3 (hourly) via scheduled-tasks
  Step 6: run Tier 1 sweep immediately
  Step 7: post readiness confirmation

You have full autonomy per the playbook — do not ask permission for routine fixes. Escalate only novel issues (Pattern 5.14) or critical triggers (Part 8).

You are starting on Sonnet. Recommend switching to Opus only when a diagnosis requires it (per Part 9.5).

Begin.
"@

Write-Host $prompt
Write-Host "──────────────────────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host ""
Write-Host "Copy the text above and paste it into your new `claude` session." -ForegroundColor Yellow
Write-Host ""
Write-Host "The monitor will run autonomously from that point — read monitor.log for details." -ForegroundColor Gray
