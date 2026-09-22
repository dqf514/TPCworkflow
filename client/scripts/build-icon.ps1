# 将正方形 PNG 转为 ICO（供 ApplicationIcon / 任务栏使用）
param(
    [string]$SourcePng = (Join-Path $PSScriptRoot "..\Assets\app-icon.png"),
    [string]$OutputIco = (Join-Path $PSScriptRoot "..\Assets\app.ico")
)

Add-Type -AssemblyName System.Drawing

if (-not (Test-Path $SourcePng)) {
    Write-Error "找不到源图: $SourcePng"
    exit 1
}

$src = [System.Drawing.Image]::FromFile((Resolve-Path $SourcePng))
$size = 256

$bmp = New-Object System.Drawing.Bitmap $size, $size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($bmp)
try {
    $g.Clear([System.Drawing.Color]::Transparent)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.DrawImage($src, 0, 0, $size, $size)
}
finally {
    $g.Dispose()
    $src.Dispose()
}

$hIcon = $bmp.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($hIcon)
try {
    $fs = [System.IO.File]::Open($OutputIco, [System.IO.FileMode]::Create)
    try {
        $icon.Save($fs)
    }
    finally {
        $fs.Close()
    }
    Write-Host "已生成: $OutputIco"
}
finally {
    $icon.Dispose()
    $bmp.Dispose()
}
