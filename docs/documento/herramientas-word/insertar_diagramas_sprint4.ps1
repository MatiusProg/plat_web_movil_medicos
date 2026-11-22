# Inserta los PNG de los diagramas del Sprint 4 debajo de cada subtítulo, con Word por COM.
# Uso:  powershell -File insertar_diagramas_sprint4.ps1 -Entrada "doc.docx" -Salida "doc2.docx" -Png "...\png\Sprint4"
#
# Recorre el capítulo del Sprint 4 (desde su título «Sprint 4» con estilo de título) y, dentro de
# cada sección de diagramas (2.1.3.1, 2.1.4.1 a 2.1.4.5, y 1.3 Contexto del Sistema), pone la
# imagen en el párrafo vacío que sigue al subtítulo del CU. Ancho: el del texto (o menos, si la
# imagen es más chica); el alto, proporcional. No toca ninguna otra imagen.
param(
    [Parameter(Mandatory = $true)][string]$Entrada,
    [Parameter(Mandatory = $true)][string]$Salida,
    [Parameter(Mandatory = $true)][string]$Png
)
$ErrorActionPreference = 'Stop'
$carpeta = @{
    '2.1.3.1' = 'Comunicación'; '2.1.4.1' = 'Diseño de clase'; '2.1.4.2' = 'Secuencia'
    '2.1.4.3' = 'Estado'; '2.1.4.4' = 'Tiempo'; '2.1.4.5' = 'Navegación'; '1.3' = 'Casos de Uso'
}
function Buscar-Png([string]$seccion, [string]$titulo) {
    $dir = Join-Path $Png $carpeta[$seccion]
    if (-not (Test-Path $dir)) { return $null }
    if ($seccion -eq '2.1.4.5') {
        $clave = ($titulo -split ' ')[0]           # Sistema, P5, P6...
        $f = Get-ChildItem $dir -Filter '*.png' | Where-Object { $_.BaseName -match "^Navegación - $([regex]::Escape($clave))( |$)" } | Select-Object -First 1
    } elseif ($seccion -eq '1.3') {
        $f = Get-ChildItem $dir -Filter '*.png' | Select-Object -First 1
    } else {
        $cu = [regex]::Match($titulo, '^CU\d+').Value
        if (-not $cu) { return $null }
        $f = Get-ChildItem $dir -Filter '*.png' | Where-Object { $_.BaseName -match "(^| )$cu " } | Select-Object -First 1
    }
    if ($f) { return $f.FullName } else { return $null }
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($Entrada, $false, $false)
    $sec = $doc.Sections.Item(1)
    $ancho = $sec.PageSetup.PageWidth - $sec.PageSetup.LeftMargin - $sec.PageSetup.RightMargin
    $p = $doc.Paragraphs.First
    $enSprint4 = $false; $seccion = $null; $puestas = 0; $faltan = @()
    while ($p -ne $null) {
        $t = $p.Range.Text.Trim()
        $estilo = $p.Style.NameLocal
        if (-not $enSprint4) {
            if ($t -eq 'Sprint 4' -and $estilo -match 'tulo') { $enSprint4 = $true }
            $p = $p.Next(); continue
        }
        if ($t -match '^5\. Artefactos Final') { break }
        if ($t -match '^(2\.1\.3\.1|2\.1\.4\.[1-5]) ') { $seccion = $Matches[1]; $p = $p.Next(); continue }
        if ($t -match '^1\.3 Contexto del Sistema') { $seccion = '1.3' }
        if ($t -match '^(2\.1\.3\.2|2\.2 |2\.1\.4 |1\.4 )') { $seccion = $null }
        $esSub = ($seccion -in @('2.1.3.1','2.1.4.1','2.1.4.2','2.1.4.3','2.1.4.4') -and $t -match '^CU\d+') -or
                 ($seccion -eq '2.1.4.5' -and $estilo -match 'tulo' -and $t.Length -gt 0) -or
                 ($seccion -eq '1.3' -and $t -match '^1\.3 Contexto del Sistema')
        if ($esSub) {
            $archivo = Buscar-Png $seccion $t
            $sig = $p.Next()
            if ($archivo -and $sig -ne $null -and $sig.Range.Text.Trim().Length -eq 0 -and $sig.Range.InlineShapes.Count -eq 0) {
                $r = $sig.Range; $r.Collapse(1)
                $img = $doc.InlineShapes.AddPicture($archivo, $false, $true, $r)
                if ($img.Width -gt $ancho) {
                    $prop = $img.Height / $img.Width
                    $img.Width = $ancho; $img.Height = $ancho * $prop
                }
                $puestas++
                $p = $sig.Next(); continue
            } elseif (-not $archivo) { $faltan += "$seccion · $t" }
        }
        $p = $p.Next()
    }
    $doc.SaveAs2($Salida, 16)
    $doc.Close($false)
    Write-Output "Imágenes puestas: $puestas"
    if ($faltan.Count) { Write-Output "Sin PNG:"; $faltan | ForEach-Object { Write-Output "  $_" } }
} finally {
    $word.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
