$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Get-PythonCommand {
    $candidates = @(
        @("py", "-3"),
        @("python"),
        @("python3")
    )
    foreach ($parts in $candidates) {
        $exe = $parts[0]
        $cmd = Get-Command $exe -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            $args = @()
            if ($parts.Count -gt 1) { $args += $parts[1..($parts.Count - 1)] }
            $args += @("-c", "import sys; print(sys.version)")
            & $exe @args | Out-Null
            if ($LASTEXITCODE -eq 0) { return @{ Exe = $exe; Prefix = $parts } }
        } catch {
            continue
        }
    }
    return $null
}

Write-Host "[1/3] Python 확인 중..."
$python = Get-PythonCommand
if (-not $python) {
    Write-Host "Python이 없습니다. https://www.python.org/downloads/ 에서 설치하세요."
    Write-Host "설치 화면에서 'Add python.exe to PATH' 를 반드시 체크하세요."
    exit 1
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "[2/3] 가상환경 만드는 중..."
    $createArgs = @()
    if ($python.Prefix.Count -gt 1) { $createArgs += $python.Prefix[1..($python.Prefix.Count - 1)] }
    $createArgs += @("-m", "venv", ".venv")
    & $python.Exe @createArgs
} else {
    Write-Host "[2/3] 기존 가상환경을 사용합니다."
}

Write-Host "[3/3] 필요한 패키지 설치 중..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")

$envPath = Join-Path $PSScriptRoot ".env"
$examplePath = Join-Path $PSScriptRoot ".env.example"
if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $examplePath -Destination $envPath
    $topic = "kmou-seungsun-" + (Get-Random -Minimum 100000 -Maximum 999999)
    $content = Get-Content -LiteralPath $envPath -Encoding UTF8
    $updated = $content | ForEach-Object {
        if ($_ -like "NTFY_TOPIC=*") { "NTFY_TOPIC=$topic" } else { $_ }
    }
    Set-Content -LiteralPath $envPath -Value $updated -Encoding UTF8
    Write-Host ""
    Write-Host "알림 토픽을 만들었습니다: $topic"
    Write-Host "iPhone ntfy 앱에서 이 토픽을 구독하세요."
} else {
    Write-Host "기존 .env 파일을 그대로 사용합니다."
}

Write-Host ""
Write-Host "설치가 끝났습니다."
Write-Host "1) iPhone에 ntfy 앱을 설치하고 .env 의 NTFY_TOPIC 을 구독하세요."
Write-Host "2) test_notify.bat 을 실행해 알림이 오는지 확인하세요."
Write-Host "3) install_autostart.bat 을 한 번만 실행하면, 이후 PC를 켤 때마다 5분마다 자동 확인합니다."
