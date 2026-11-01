# 一键发版：构建 exe -> 提交 -> 打 tag -> SSH 推送 -> 建 Release 挂 exe
#
# 用法：
#   .\auto_publish.ps1                 用当前 __version__ 发版
#   .\auto_publish.ps1 -SkipBuild      不重新打包，直接推
#
# 前提：git remote 走 SSH（git@github.com:...），并且该 key 已作为 deploy key 加到仓库。
# HTTPS 那条路在本机不可靠：代理端口会变，而且分流规则常挡住 github.com 主站。

param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$User = "wenzi4055"
$Repo = "DaFeiYu-Study-Assistant"

# 1. 版本号直接从源码读，避免文档和代码不一致
$version = (Select-String -Path "dafeiyu.py" -Pattern '^__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
if (-not $version) { Write-Error "读不到 dafeiyu.py 里的 __version__"; exit 1 }
Write-Host "版本: $version" -ForegroundColor Cyan

# 2. 构建
if (-not $SkipBuild) {
    Get-Process DaFeiYu -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Milliseconds 400
    # PyInstaller 把日志写 stderr，Stop 模式下会被当成致命错误，这里临时放开
    $ErrorActionPreference = "Continue"
    python -m PyInstaller --noconfirm --clean --onefile --noconsole --name DaFeiYu dafeiyu.py 2>&1 | Select-Object -Last 1
    $ErrorActionPreference = "Stop"
    Remove-Item DaFeiYu.spec -ErrorAction SilentlyContinue
    if (-not (Test-Path "dist\DaFeiYu.exe")) { Write-Error "打包失败"; exit 1 }
    Write-Host "打包完成: dist\DaFeiYu.exe" -ForegroundColor Green
}

# 3. 提交 + tag + 推送（SSH，不过代理）
$dirty = (git status --porcelain)
if ($dirty) {
    Write-Host "有未提交改动：" -ForegroundColor Yellow
    $dirty
    Write-Host "先自己按规范拆好提交，再跑本脚本。" -ForegroundColor Yellow
    exit 1
}
git tag -f "v$version" -m "v$version"
git push origin master
git push origin "v$version" --force
Write-Host "已推送 master 与 v$version" -ForegroundColor Green

# 4. 找可用代理（端口每个月都可能变，所以自动探测）
function Find-Proxy {
    foreach ($p in 7893, 7890, 7897, 12000, 10809, 10808, 1080) {
        try {
            $r = Invoke-WebRequest -Uri "https://api.github.com" -Headers @{ "User-Agent" = "dafeiyu" } `
                 -Proxy "http://127.0.0.1:$p" -TimeoutSec 6
            if ($r.StatusCode -eq 200) { return "http://127.0.0.1:$p" }
        } catch { }
    }
    return ""
}
$px = Find-Proxy
if (-not $px) { Write-Error "找不到可用代理，Release 这步跳过。先把代理开起来再重跑。"; exit 1 }
Write-Host "代理: $px" -ForegroundColor Cyan

# 5. 用凭据里的 token 调 API 建 Release 并上传 exe
$cred = @("protocol=https", "host=github.com", "") | git credential fill 2>$null
$token = ($cred | Where-Object { $_ -like "password=*" }) -replace "^password=", ""
if (-not $token) { Write-Error "取不到 token，Release 跳过"; exit 1 }
$h = @{ "Authorization" = "token $token"; "User-Agent" = "dafeiyu"; "Accept" = "application/vnd.github+json" }
$base = "https://api.github.com/repos/$User/$Repo"

$payload = @{ tag_name = "v$version"; name = "v$version"; draft = $false; prerelease = $false } | ConvertTo-Json -Compress
$bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
$rel = Invoke-RestMethod -Uri "$base/releases" -Method Post -Headers $h -Body $bytes `
       -ContentType "application/json; charset=utf-8" -Proxy $px -TimeoutSec 60

$exe = [System.IO.File]::ReadAllBytes("dist\DaFeiYu.exe")
$up = "https://uploads.github.com/repos/$User/$Repo/releases/$($rel.id)/assets?name=DaFeiYu.exe"
$a = Invoke-RestMethod -Uri $up -Method Post -Headers $h -Body $exe `
     -ContentType "application/octet-stream" -Proxy $px -TimeoutSec 300

Write-Host ""
Write-Host "发版完成: $($rel.html_url)" -ForegroundColor Green
Write-Host "下载: $($a.browser_download_url)"
