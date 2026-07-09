$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = python -c "from version import __version__; print(__version__)"
$appName = python -c "from version import APP_NAME; print(APP_NAME)"
$exeName = python -c "from version import dist_exe_name; print(dist_exe_name())"
$installerName = python -c "from version import installer_filename; print(installer_filename())"

Write-Host "Building $appName $version..."

python make_version_info.py

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    pip install pyinstaller
}

pyinstaller ChatList.spec --noconfirm

Write-Host "Executable: dist\$exeName.exe"

$isccPaths = @(
    (Get-Command iscc -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if ($isccPaths) {
    & $isccPaths "/DAppVersion=$version" "/DAppName=$appName" "/DAppExeName=$exeName" installer.iss
    Write-Host "Installer: dist\$installerName"
} else {
    Write-Host "Inno Setup (ISCC.exe) not found - exe built, installer skipped."
    Write-Host "Install: winget install JRSoftware.InnoSetup"
}
