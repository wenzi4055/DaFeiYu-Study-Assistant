# 一键发布到 GitHub：检测登录 -> 建仓库（或复用） -> 推送 -> 补描述/topics -> 建 Release 挂 exe
# 用法：.\auto_publish.ps1
# 前置：gh 已登录（gh auth login --web 走过一次浏览器授权）

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) { $gh = "gh" }

$User = "wenzi4055"
$Repo = "DaFeiYu-Study-Assistant"
$Desc = "大肥鱼监工器 · 三科考试进度悬浮窗：三态打卡 + 硬性验收标准常驻，单文件零依赖"

# 1. 登录检查
& $gh auth status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "还没登录 GitHub。先跑这条，浏览器里完成授权：" -ForegroundColor Yellow
    Write-Host "  & '$gh' auth login --web --hostname github.com --git-protocol https"
    exit 1
}
Write-Host "登录状态: OK" -ForegroundColor Green

# 2. 仓库是否存在
& $gh repo view "$User/$Repo" *> $null
$exists = ($LASTEXITCODE -eq 0)

if (-not $exists) {
    Write-Host "仓库不存在，创建中..." -ForegroundColor Cyan
    & $gh repo create $Repo --public --description $Desc --source . --remote origin --push
    if ($LASTEXITCODE -ne 0) { Write-Error "创建仓库失败，看上面的 gh 输出"; exit 1 }
} else {
    Write-Host "仓库已存在，直接推送..." -ForegroundColor Cyan
    git remote remove origin 2>$null | Out-Null
    git remote add origin "https://github.com/$User/$Repo.git"
    git push -u origin master
    if ($LASTEXITCODE -ne 0) { Write-Error "推送失败"; exit 1 }
}

# 3. 补仓库信息
& $gh repo edit "$User/$Repo" --description $Desc `
    --add-topic study-tools,exam,productivity,tkinter,python,desktop-widget,self-discipline 2>$null | Out-Null

# 4. Release（exe 挂附件，README 里的下载链接就有着落了）
$exe = Join-Path $PSScriptRoot "dist\DaFeiYu.exe"
if (Test-Path $exe) {
    & $gh release view "v0.2" --repo "$User/$Repo" *> $null
    if ($LASTEXITCODE -ne 0) {
        & $gh release create "v0.2" $exe `
            --repo "$User/$Repo" `
            --title "v0.2 · 配置驱动 + exe 打包" `
            --notes "tasks.json 配置驱动（任意任务池/任意监督对象）、单文件 exe 打包、通用监督人格模板、DPI 感知修复。下载 DaFeiYu.exe 双击即用，无需安装 Python。"
    }
}

Write-Host ""
Write-Host "完成: https://github.com/$User/$Repo" -ForegroundColor Green
& $gh repo view "$User/$Repo" --web
