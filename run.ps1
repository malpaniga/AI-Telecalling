# AI Telecalling SaaS - PowerShell Runner
param(
    [Alias("s")]
    [switch]$Separate
)

$RootDir = $PSScriptRoot
Set-Location $RootDir

$PythonExe = if (Test-Path "$RootDir\.venv\Scripts\python.exe") {
    "$RootDir\.venv\Scripts\python.exe"
} else {
    "python"
}

if ($Separate) {
    & $PythonExe "$RootDir\run.py" --separate
} else {
    & $PythonExe "$RootDir\run.py" $args
}
