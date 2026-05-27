# Windows PowerShell Installer for Always-On Lyrics Overlay App
$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Teal
Write-Host "   Installing Always-On Lyrics Overlay App...     " -ForegroundColor Teal
Write-Host "==================================================" -ForegroundColor Teal

# 1. Define paths
$InstallDir = Join-Path $env:LocalAppData "Programs\LyricsOverlay"
$ExeName = "LyricsOverlay.exe"
$SourceExe = Join-Path $PSScriptRoot "dist\$ExeName"

if (-not (Test-Path $SourceExe)) {
    # Fallback to local search if executed outside project root
    $SourceExe = Join-Path $PSScriptRoot "LyricsOverlay.exe"
    if (-not (Test-Path $SourceExe)) {
        Write-Error "Error: Standalone executable 'LyricsOverlay.exe' not found! Please build the executable using build.py first."
        exit 1
    }
}

# 2. Terminate background processes if active
Write-Host "Terminating active instances..." -ForegroundColor Yellow
Stop-Process -Name "LyricsOverlay" -Force -ErrorAction SilentlyContinue

# 3. Create folder
Write-Host "Creating installation directory at $InstallDir..." -ForegroundColor Gray
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# 4. Copy files
Write-Host "Copying executable..." -ForegroundColor Gray
Copy-Item -Path $SourceExe -Destination (Join-Path $InstallDir $ExeName) -Force

# 5. Create Start Menu Shortcut
$StartMenuPath = [System.IO.Path]::Combine($env:AppData, "Microsoft\Windows\Start Menu\Programs")
$ShortcutPath = Join-Path $StartMenuPath "Lyrics Overlay.lnk"
Write-Host "Creating Start Menu shortcut at $ShortcutPath..." -ForegroundColor Gray

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $InstallDir $ExeName
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Save()

# 6. Create Desktop Shortcut
$DesktopPath = [System.Environment]::GetFolderPath("Desktop")
$DesktopShortcutPath = Join-Path $DesktopPath "Lyrics Overlay.lnk"
Write-Host "Creating Desktop shortcut..." -ForegroundColor Gray
$DesktopShortcut = $WshShell.CreateShortcut($DesktopShortcutPath)
$DesktopShortcut.TargetPath = Join-Path $InstallDir $ExeName
$DesktopShortcut.WorkingDirectory = $InstallDir
$DesktopShortcut.Save()

# 7. Write Uninstall Key to Registry for standard Add/Remove Programs integration
$UninstallKey = "Software\Microsoft\Windows\CurrentVersion\Uninstall\LyricsOverlay"
Write-Host "Registering uninstaller in Windows Settings..." -ForegroundColor Gray

$RegPath = "HKCU:\$UninstallKey"
if (-not (Test-Path $RegPath)) {
    New-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall" -Name "LyricsOverlay" -Force | Out-Null
}

Set-ItemProperty -Path $RegPath -Name "DisplayName" -Value "Always-On Lyrics Overlay"
Set-ItemProperty -Path $RegPath -Name "DisplayIcon" -Value (Join-Path $InstallDir $ExeName)
Set-ItemProperty -Path $RegPath -Name "DisplayVersion" -Value "1.0.0"
Set-ItemProperty -Path $RegPath -Name "Publisher" -Value "Antigravity Open Source"
Set-ItemProperty -Path $RegPath -Name "InstallLocation" -Value $InstallDir

# Create PowerShell-based uninstaller script on disk
$UninstallScriptPath = Join-Path $InstallDir "uninstall.ps1"
$UninstallContent = @"
Stop-Process -Name "LyricsOverlay" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$ShortcutPath" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$DesktopShortcutPath" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "HKCU:\$UninstallKey" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$InstallDir" -Recurse -Force
Write-Host "Always-On Lyrics Overlay successfully uninstalled."
"@
Set-Content -Path $UninstallScriptPath -Value $UninstallContent

# Uninstall command
$UninstallCmd = "powershell.exe -ExecutionPolicy Bypass -File `"$UninstallScriptPath`""
Set-ItemProperty -Path $RegPath -Name "UninstallString" -Value $UninstallCmd

Write-Host "==================================================" -ForegroundColor Green
Write-Host "  Success! Always-On Lyrics Overlay is ready!     " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host "Start the app from the Desktop or Start Menu!" -ForegroundColor Green

# Optional: Prompt to start the application now
$Answer = Read-Host "Would you like to run the application now? (Y/N)"
if ($Answer.Trim().ToUpper() -eq "Y") {
    Start-Process -FilePath (Join-Path $InstallDir $ExeName) -WorkingDirectory $InstallDir
}
