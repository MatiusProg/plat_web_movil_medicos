# Exporta un .docx a PDF con Microsoft Word (COM), sin modificar el .docx.
# Uso:  powershell -File exportar_pdf.ps1 -Entrada "ruta\doc.docx" -Salida "ruta\doc.pdf"
# Abre el documento en sólo lectura y no muestra diálogos. Tarda ~1 minuto con este documento.
param(
    [Parameter(Mandatory = $true)][string]$Entrada,
    [Parameter(Mandatory = $true)][string]$Salida
)
$Entrada = (Resolve-Path $Entrada).Path
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
    $doc = $w.Documents.Open($Entrada, $false, $true)
    $doc.ExportAsFixedFormat($Salida, 17)   # 17 = wdExportFormatPDF
    $doc.Close(0)
} finally {
    $w.Quit()
}
Write-Output "PDF: $Salida"
