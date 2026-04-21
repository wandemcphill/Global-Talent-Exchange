[CmdletBinding()]
param(
    [string]$UnityExe = "C:\Program Files\Unity\Hub\Editor\6000.3.12f1\Editor\Unity.exe",
    [string]$ProjectPath,
    [string]$ExecuteMethod = "FStudio.GTEX.Editor.GtexBuildTools.BuildWindows64ProductionFromCommandLine",
    [string]$LogFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($ProjectPath))
{
    $ProjectPath = Join-Path $repoRoot "Gtex_Test_Migration"
}

if ([string]::IsNullOrWhiteSpace($LogFile))
{
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $LogFile = Join-Path (Join-Path $repoRoot "tmp") ("gtex_test_migration_windows_production_build_{0}.log" -f $timestamp)
}

if (-not (Test-Path -Path $UnityExe -PathType Leaf))
{
    throw "Unity executable not found: $UnityExe"
}

if (-not (Test-Path -Path $ProjectPath -PathType Container))
{
    throw "Unity project path not found: $ProjectPath"
}

$logDirectory = Split-Path -Parent $LogFile
if (-not [string]::IsNullOrWhiteSpace($logDirectory) -and -not (Test-Path -Path $logDirectory -PathType Container))
{
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class GtexExecutionState
{
    [Flags]
    public enum EXECUTION_STATE : uint
    {
        ES_AWAYMODE_REQUIRED = 0x00000040,
        ES_CONTINUOUS = 0x80000000,
        ES_SYSTEM_REQUIRED = 0x00000001
    }

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern EXECUTION_STATE SetThreadExecutionState(EXECUTION_STATE esFlags);
}
"@

$keepAwakeState =
    [GtexExecutionState+EXECUTION_STATE]::ES_CONTINUOUS -bor
    [GtexExecutionState+EXECUTION_STATE]::ES_SYSTEM_REQUIRED -bor
    [GtexExecutionState+EXECUTION_STATE]::ES_AWAYMODE_REQUIRED

[GtexExecutionState]::SetThreadExecutionState($keepAwakeState) | Out-Null

$arguments = @(
    "-batchmode"
    "-quit"
    "-nographics"
    "-buildTarget"
    "StandaloneWindows64"
    "-projectPath"
    $ProjectPath
    "-executeMethod"
    $ExecuteMethod
    "-logFile"
    $LogFile
)

function Format-ProcessArgument([string]$Argument)
{
    if ([string]::IsNullOrEmpty($Argument))
    {
        return '""'
    }

    if ($Argument.Contains('"'))
    {
        $Argument = $Argument.Replace('"', '\"')
    }

    if ($Argument.IndexOfAny([char[]]@(' ', "`t")) -ge 0)
    {
        return '"' + $Argument + '"'
    }

    return $Argument
}

$argumentString = ($arguments | ForEach-Object { Format-ProcessArgument $_ }) -join ' '

Write-Host "[GTEX Build] Keeping Windows awake for the duration of the Unity batch build."
Write-Host "[GTEX Build] Project: $ProjectPath"
Write-Host "[GTEX Build] Method: $ExecuteMethod"
Write-Host "[GTEX Build] Log: $LogFile"

try
{
    $process = Start-Process -FilePath $UnityExe -ArgumentList $argumentString -PassThru -Wait
    $exitCode = $process.ExitCode
    Write-Host "[GTEX Build] Unity exited with code $exitCode."

    if ($exitCode -ne 0)
    {
        throw "Unity batch build failed with exit code $exitCode."
    }
}
finally
{
    [GtexExecutionState]::SetThreadExecutionState([GtexExecutionState+EXECUTION_STATE]::ES_CONTINUOUS) | Out-Null
    Write-Host "[GTEX Build] Restored default Windows execution state."
}
