$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = python -c "from version import __version__; print(__version__)"
$appName = python -c "from version import APP_NAME; print(APP_NAME)"
$exeName = python -c "from version import dist_exe_name; print(dist_exe_name())"
$installerName = python -c "from version import installer_filename; print(installer_filename())"
$tag = "v$version"
$releaseNotesPath = Join-Path $PSScriptRoot "docs\release-notes\v$version.md"

Write-Host "Publishing $appName $tag..."

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is not installed. Install: winget install GitHub.cli"
}

gh auth status | Out-Null

Write-Host "Step 1/5: Build artifacts..."
& "$PSScriptRoot\build.ps1"

$installerPath = Join-Path $PSScriptRoot "dist\$installerName"
$portablePath = Join-Path $PSScriptRoot "dist\$exeName.exe"

if (-not (Test-Path $installerPath)) {
    throw "Installer not found: $installerPath"
}
if (-not (Test-Path $portablePath)) {
    throw "Portable exe not found: $portablePath"
}

Write-Host "Step 2/5: SHA256 checksums..."
$installerHash = (Get-FileHash $installerPath -Algorithm SHA256).Hash
$portableHash = (Get-FileHash $portablePath -Algorithm SHA256).Hash
Write-Host "  $installerName  $installerHash"
Write-Host "  $exeName.exe       $portableHash"

if (-not (Test-Path $releaseNotesPath)) {
    throw "Release notes not found: $releaseNotesPath`nCreate from docs\release-notes\TEMPLATE.md"
}

$notesBody = Get-Content $releaseNotesPath -Raw -Encoding UTF8
$checksumBlock = @"

## Контрольные суммы (SHA256)

```
$installerName  $installerHash
$exeName.exe       $portableHash
```
"@
$notesBody = "$notesBody`n$checksumBlock"

$notesFile = Join-Path $env:TEMP "chatlist-release-notes-$version.md"
Set-Content -Path $notesFile -Value $notesBody -Encoding UTF8

Write-Host "Step 3/5: Git tag $tag..."
$existingTag = git tag -l $tag
if ($existingTag) {
    Write-Host "  Tag $tag already exists locally."
} else {
    git tag -a $tag -m "$appName $version"
    Write-Host "  Created local tag $tag."
}

$remoteTag = git ls-remote --tags origin "refs/tags/$tag"
if ($remoteTag) {
    Write-Host "  Tag $tag already exists on origin."
} else {
    git push origin $tag
    Write-Host "  Pushed tag $tag to origin."
}

Write-Host "Step 4/5: GitHub Release..."
$releaseExists = gh release view $tag 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Release $tag exists, uploading assets..."
    gh release upload $tag $installerPath $portablePath --clobber
    gh release edit $tag --notes-file $notesFile
} else {
    gh release create $tag `
        --title "$appName $version" `
        --notes-file $notesFile `
        $installerPath `
        $portablePath
}

Write-Host "Step 5/5: Done."
Write-Host "Release: https://github.com/lsm-sys/ChatList/releases/tag/$tag"
Write-Host "Pages:   https://lsm-sys.github.io/ChatList/ (after docs are pushed and Pages enabled)"
