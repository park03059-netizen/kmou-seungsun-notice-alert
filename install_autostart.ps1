$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$venvPythonw = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
$runner = Join-Path $PSScriptRoot "run_check.bat"

if (-not (Test-Path -LiteralPath $venvPythonw)) {
    Write-Host "먼저 install.bat 을 실행해 주세요. 가상환경이 없습니다."
    exit 1
}

$intervalName = "KMOUSeungsunNoticeEvery5Min"
$oldHourlyName = "KMOUSeungsunNoticeHourly"
$oldLogonName = "KMOUSeungsunNoticeOnLogon"
$taskCommand = "`"$runner`""
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$startupBat = Join-Path $startupDir "KMOUSeungsunNotice.bat"
$startupLnk = Join-Path $startupDir "KMOUSeungsunNotice.lnk"

# 예전에 만든 작업이 있으면 지웁니다. 없어도 오류로 멈추지 않습니다.
cmd.exe /c "schtasks /Delete /TN $oldHourlyName /F >nul 2>&1" | Out-Null
cmd.exe /c "schtasks /Delete /TN $oldLogonName /F >nul 2>&1" | Out-Null

schtasks /Create /TN $intervalName /TR $taskCommand /SC MINUTE /MO 5 /RL LIMITED /F | Out-Host
if ($LASTEXITCODE -ne 0) { throw "5분마다 확인할 예약 작업을 만들지 못했습니다." }

New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
Remove-Item -LiteralPath $startupBat -ErrorAction SilentlyContinue
$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut($startupLnk)
$shortcut.TargetPath = $runner
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 7
$shortcut.Save()

Write-Host ""
Write-Host "자동 시작 설정이 끝났습니다. 이 파일은 한 번만 실행하면 됩니다."
Write-Host "PC를 다시 켤 때마다 다시 누를 필요는 없습니다."
Write-Host "- $intervalName : 5분마다 확인"
Write-Host "- 시작프로그램: 로그인하면 바로 한 번 확인"
Write-Host "작업 스케줄러에서 KMOUSeungsun 으로 검색하면 볼 수 있습니다."
Write-Host "해제하려면 uninstall_autostart.bat 을 실행하세요."
