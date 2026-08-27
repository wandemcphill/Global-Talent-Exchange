<#
.SYNOPSIS
    Shared helpers for GTEX Windows launcher scripts. Dot-sourced by
    GTEX_PHASE1_WINDOWS_DEMO.ps1 and exercised directly by
    GTEX_PHASE1_WINDOWS_DEMO.Tests.ps1.
#>

function ConvertTo-QuotedArgumentString {
    <#
    .SYNOPSIS
        Builds a single Win32 command-line argument string from an array of
        raw argument values, quoting/escaping each element as needed.

        Start-Process -ArgumentList (string[]) does NOT reliably quote
        elements that contain spaces on Windows PowerShell 5.1 -- it joins
        elements with a bare space, so a path like
        "C:\Users\me\GLOBAL TALENT EXCHANGE\tools\foo.py" gets truncated at
        the first space when the child process parses argv. Pre-building an
        explicitly quoted string and passing that single string to
        -ArgumentList avoids the bug regardless of PowerShell version.
    #>
    param([Parameter(Mandatory = $true)][object[]]$ArgumentValues)
    $parts = foreach ($value in $ArgumentValues) {
        $text = [string]$value
        if ($text -match '[\s"]') {
            # Escape embedded double quotes per Windows argv conventions, then wrap in quotes.
            $escaped = $text -replace '"', '\"'
            '"' + $escaped + '"'
        } else {
            $text
        }
    }
    return ($parts -join ' ')
}
