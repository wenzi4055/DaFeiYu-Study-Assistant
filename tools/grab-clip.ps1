<#
    抓剪贴板图片 -> 落盘为 PNG。
    QQ 聊天里右键图片「复制」，然后跑这个，图就进 raw_shots\ 了。

    单次抓取：
        powershell.exe -Sta -File tools\grab-clip.ps1
    监听模式（每 1.5 秒看一次剪贴板，有新图就存，Ctrl+C 停）：
        powershell.exe -Sta -File tools\grab-clip.ps1 -Watch

    必须在 Windows PowerShell 5.1 下带 -Sta 跑：pwsh 7 是 MTA，剪贴板 API 会抛错。
#>
param(
    [string]$OutDir = (Join-Path $PSScriptRoot '..\raw_shots'),
    [switch]$Watch,
    [int]$IntervalMs = 1500
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$dir = [System.IO.Path]::GetFullPath($OutDir)
if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

function Get-ClipDigest {
    if (-not [System.Windows.Forms.Clipboard]::ContainsImage()) { return $null }
    $img = [System.Windows.Forms.Clipboard]::GetImage()
    if ($null -eq $img) { return $null }
    try {
        $ms = New-Object System.IO.MemoryStream
        $img.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        $bytes = $ms.ToArray()
        $ms.Dispose()
        $md5 = [System.Security.Cryptography.MD5]::Create()
        $hash = [System.BitConverter]::ToString($md5.ComputeHash($bytes))
        return [pscustomobject]@{ Hash = $hash; Bytes = $bytes; Width = $img.Width; Height = $img.Height }
    } finally {
        $img.Dispose()
    }
}

function Save-Digest($digest) {
    $name = 'clip-{0}.png' -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
    $path = Join-Path $dir $name
    [System.IO.File]::WriteAllBytes($path, $digest.Bytes)
    Write-Output $path
}

$last = $null

if (-not $Watch) {
    $d = Get-ClipDigest
    if ($null -eq $d) {
        Write-Output 'CLIPBOARD_EMPTY: 剪贴板里没有图片'
        exit 1
    }
    Save-Digest $d
    exit 0
}

Write-Output "WATCHING: $dir  (Ctrl+C 停止)"
while ($true) {
    $d = Get-ClipDigest
    if ($null -ne $d -and $d.Hash -ne $last) {
        $p = Save-Digest $d
        $last = $d.Hash
        Write-Output ("SAVED {0}  {1}x{2}" -f $p, $d.Width, $d.Height)
    }
    Start-Sleep -Milliseconds $IntervalMs
}
