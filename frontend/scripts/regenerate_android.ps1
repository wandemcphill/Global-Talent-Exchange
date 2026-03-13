$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot/..
flutter create . --platforms=android
flutter pub get
Write-Host 'Android scaffold regenerated. You can now run: flutter build apk --debug'
