param(
  [string]$ApiBaseUrl = 'http://127.0.0.1:8000',
  [string]$BackendMode = 'live',
  [string]$DeviceId,
  [switch]$SkipAdbReverse
)

$ErrorActionPreference = 'Stop'

function Get-ApiPort {
  param([uri]$Uri)

  if (-not $Uri.IsDefaultPort) {
    return $Uri.Port
  }

  if ($Uri.Scheme -eq 'https') {
    return 443
  }

  return 80
}

function Get-ListeningAddressesForPort {
  param([int]$Port)

  try {
    $addresses = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop |
      Select-Object -ExpandProperty LocalAddress -Unique
    if ($addresses) {
      return @($addresses)
    }
  } catch {
  }

  $listeningAddresses = New-Object System.Collections.Generic.HashSet[string]
  $netstatLines = netstat -ano -p tcp | Select-String -Pattern 'LISTENING'
  foreach ($line in $netstatLines) {
    $parts = ($line.ToString() -split '\s+') | Where-Object { $_ -ne '' }
    if ($parts.Count -lt 4) {
      continue
    }

    $localEndpoint = $parts[1]
    $separatorIndex = $localEndpoint.LastIndexOf(':')
    if ($separatorIndex -lt 0) {
      continue
    }

    $localAddress = $localEndpoint.Substring(0, $separatorIndex)
    $localPort = $localEndpoint.Substring($separatorIndex + 1)
    if ($localPort -ne $Port.ToString()) {
      continue
    }

    if ($localAddress.StartsWith('[') -and $localAddress.EndsWith(']')) {
      $localAddress = $localAddress.Substring(1, $localAddress.Length - 2)
    }

    [void]$listeningAddresses.Add($localAddress)
  }

  return @($listeningAddresses)
}

function Test-IsLoopbackHost {
  param([string]$HostName)

  return $HostName -in @('127.0.0.1', 'localhost', '::1')
}

function Test-IsLoopbackOnlyBinding {
  param([string[]]$Addresses)

  if (-not $Addresses -or $Addresses.Count -eq 0) {
    return $false
  }

  foreach ($address in $Addresses) {
    if ($address -in @('0.0.0.0', '::', '*')) {
      return $false
    }

    if (-not ($address -in @('127.0.0.1', '::1'))) {
      return $false
    }
  }

  return $true
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot 'frontend'
$adbPath = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'

if (-not (Test-Path $frontendDir)) {
  throw "Frontend directory not found at $frontendDir"
}

if (-not (Test-Path $adbPath)) {
  throw "adb not found at $adbPath"
}

[uri]$apiUri = $ApiBaseUrl
$apiPort = Get-ApiPort -Uri $apiUri
$isLoopbackHost = Test-IsLoopbackHost -HostName $apiUri.Host
$listeningAddresses = Get-ListeningAddressesForPort -Port $apiPort

if ($isLoopbackHost -and $SkipAdbReverse) {
  throw "ApiBaseUrl points at $($apiUri.Host):$apiPort but -SkipAdbReverse was supplied. A physical Android device cannot reach host loopback without adb reverse."
}

if (-not $isLoopbackHost -and (Test-IsLoopbackOnlyBinding -Addresses $listeningAddresses)) {
  $bindingList = ($listeningAddresses -join ', ')
  throw "ApiBaseUrl points at $ApiBaseUrl, but the backend is only listening on loopback for port $apiPort ($bindingList). Rebind the backend to 0.0.0.0 or use localhost plus adb reverse."
}

$adbArgs = @()
if ($DeviceId) {
  $adbArgs += '-s'
  $adbArgs += $DeviceId
}

$loopbackMatch = [regex]::Match(
  $ApiBaseUrl,
  '^https?://(?:127\.0\.0\.1|localhost):(?<port>\d+)(?:/.*)?$'
)
if ($loopbackMatch.Success -and -not $SkipAdbReverse) {
  $port = $loopbackMatch.Groups['port'].Value
  Write-Host "Using adb reverse for host loopback on tcp:$port"
  & $adbPath @adbArgs reverse "tcp:$port" "tcp:$port"
} elseif (-not $isLoopbackHost) {
  Write-Host "Using LAN-reachable backend $ApiBaseUrl"
}

$flutterArgs = @(
  'run',
  "--dart-define=GTE_API_BASE_URL=$ApiBaseUrl",
  "--dart-define=GTE_BACKEND_MODE=$BackendMode"
)
if ($DeviceId) {
  $flutterArgs += '-d'
  $flutterArgs += $DeviceId
}

Push-Location $frontendDir
try {
  & flutter @flutterArgs
} finally {
  Pop-Location
}
