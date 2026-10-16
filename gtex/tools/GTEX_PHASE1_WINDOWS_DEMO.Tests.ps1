<#
.SYNOPSIS
    Regression tests for the GTEX Windows launcher's argument-quoting logic.
    Covers the bug where Start-Process -ArgumentList truncated paths at the
    first space (e.g. repo paths under "GLOBAL TALENT EXCHANGE").

.NOTES
    Run with: Invoke-Pester -Path .\tools\GTEX_PHASE1_WINDOWS_DEMO.Tests.ps1
    Written against the legacy (dash-less) Should syntax for compatibility
    with the Windows-bundled Pester 3.4.0 module.
#>

. (Join-Path $PSScriptRoot "GTEX_Launcher_Common.ps1")

Describe "ConvertTo-QuotedArgumentString" {

    It "quotes an argument containing spaces" {
        $result = ConvertTo-QuotedArgumentString -ArgumentValues @("C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_live_backend.py")
        $result | Should Be '"C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\tools\run_gtex_live_backend.py"'
    }

    It "leaves simple arguments without spaces unquoted" {
        $result = ConvertTo-QuotedArgumentString -ArgumentValues @("--profile", "local", "--port", 8000)
        $result | Should Be '--profile local --port 8000'
    }

    It "reproduces the real backend argv and does not truncate at the first space" {
        $repoRootWithSpace = "C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE"
        $backendScript = Join-Path $repoRootWithSpace "tools\run_gtex_live_backend.py"
        $argValues = @($backendScript, "--profile", "local", "--port", 8000, "--log-level", "info")

        $argString = ConvertTo-QuotedArgumentString -ArgumentValues $argValues

        # The script path must appear as one fully-quoted token, not split at "GLOBAL".
        $argString | Should Match ([regex]::Escape('"' + $backendScript + '"'))

        # The old bug joined array elements with a bare space and no quoting, so the
        # child process's argv[0] became "C:\Users\ayomc\Desktop\GLOBAL" (truncated).
        # Confirm the quoted string does NOT contain that bare truncated token.
        $argString.Split(' ')[0] | Should Not Be 'C:\Users\ayomc\Desktop\GLOBAL'
    }

    It "escapes embedded double quotes" {
        $result = ConvertTo-QuotedArgumentString -ArgumentValues @('a "quoted" value')
        $result | Should Be '"a \"quoted\" value"'
    }

    It "handles the Unity player log path with spaces" {
        $repoRootWithSpace = "C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE"
        $playerLog = Join-Path $repoRootWithSpace "tmp\gtex_windows_demo_player.log"
        $unityArgs = @("-popupwindow", "-screen-fullscreen", "0", "-screen-width", "1280", "-screen-height", "720", "-logFile", $playerLog)

        $result = ConvertTo-QuotedArgumentString -ArgumentValues $unityArgs

        $result | Should Match ([regex]::Escape('"' + $playerLog + '"'))
        $result | Should Match '^-popupwindow -screen-fullscreen 0 -screen-width 1280 -screen-height 720 -logFile'
    }

    It "passes an integer port through as a bare token" {
        $result = ConvertTo-QuotedArgumentString -ArgumentValues @(8000)
        $result | Should Be '8000'
    }
}

Describe "GTEX_PHASE1_WINDOWS_DEMO.ps1 static structure" {

    It "dot-sources the shared common helpers instead of redefining them inline" {
        $scriptContent = Get-Content (Join-Path $PSScriptRoot "GTEX_PHASE1_WINDOWS_DEMO.ps1") -Raw
        $scriptContent | Should Match 'GTEX_Launcher_Common\.ps1'
    }

    It "passes a pre-quoted single string to -ArgumentList for the backend Start-Process call" {
        $scriptContent = Get-Content (Join-Path $PSScriptRoot "GTEX_PHASE1_WINDOWS_DEMO.ps1") -Raw
        $scriptContent | Should Match '\$backendArgString\s*=\s*ConvertTo-QuotedArgumentString'
        $scriptContent | Should Match '-ArgumentList\s+\$backendArgString'
    }

    It "passes a pre-quoted single string to -ArgumentList for the Unity Start-Process call" {
        $scriptContent = Get-Content (Join-Path $PSScriptRoot "GTEX_PHASE1_WINDOWS_DEMO.ps1") -Raw
        $scriptContent | Should Match '\$unityArgString\s*=\s*ConvertTo-QuotedArgumentString'
        $scriptContent | Should Match '-ArgumentList\s+\$unityArgString'
    }
}
