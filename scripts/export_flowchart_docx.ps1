param(
    [string]$SourcePath = "docs/markdown/BUFIA_System_Detailed_Flowchart.md",
    [string]$OutputPath = "docs/flowcahrt.docx"
)

$ErrorActionPreference = "Stop"

function Escape-XmlText {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return [System.Security.SecurityElement]::Escape($Value)
}

function New-ParagraphXml {
    param(
        [string]$Text,
        [switch]$Bold,
        [int]$FontSizeHalfPoints = 22
    )

    $escaped = Escape-XmlText $Text
    $runProps = "<w:sz w:val=`"$FontSizeHalfPoints`"/>"
    if ($Bold) {
        $runProps = "<w:b/>$runProps"
    }

    return "<w:p><w:r><w:rPr>$runProps</w:rPr><w:t xml:space=`"preserve`">$escaped</w:t></w:r></w:p>"
}

function New-BlankParagraphXml {
    return "<w:p/>"
}

$sourceFullPath = Join-Path (Get-Location) $SourcePath
$outputFullPath = Join-Path (Get-Location) $OutputPath
$outputDirectory = Split-Path -Parent $outputFullPath

if (-not (Test-Path $sourceFullPath)) {
    throw "Source file not found: $sourceFullPath"
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

$lines = Get-Content -Path $sourceFullPath
$paragraphs = New-Object System.Collections.Generic.List[string]

foreach ($line in $lines) {
    $trimmed = $line.TrimEnd()

    if ($trimmed -match '^# ') {
        $paragraphs.Add((New-ParagraphXml -Text ($trimmed -replace '^# ', '') -Bold -FontSizeHalfPoints 32))
        continue
    }

    if ($trimmed -match '^## ') {
        $paragraphs.Add((New-ParagraphXml -Text ($trimmed -replace '^## ', '') -Bold -FontSizeHalfPoints 28))
        continue
    }

    if ($trimmed -match '^### ') {
        $paragraphs.Add((New-ParagraphXml -Text ($trimmed -replace '^### ', '') -Bold -FontSizeHalfPoints 24))
        continue
    }

    if ($trimmed -eq '---') {
        $paragraphs.Add((New-BlankParagraphXml))
        continue
    }

    if ($trimmed -eq '```mermaid' -or $trimmed -eq '```') {
        continue
    }

    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        $paragraphs.Add((New-BlankParagraphXml))
        continue
    }

    if ($trimmed -match '^- ') {
        $paragraphs.Add((New-ParagraphXml -Text ("• " + ($trimmed -replace '^- ', '')) -FontSizeHalfPoints 22))
        continue
    }

    $paragraphs.Add((New-ParagraphXml -Text $trimmed -FontSizeHalfPoints 22))
}

$documentXml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:o="urn:schemas-microsoft-com:office:office"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
    xmlns:v="urn:schemas-microsoft-com:vml"
    xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
    xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    xmlns:w10="urn:schemas-microsoft-com:office:word"
    xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
    xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
    xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
    xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml"
    xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    mc:Ignorable="w14 wp14">
  <w:body>
    $($paragraphs -join "`r`n    ")
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"@

$contentTypesXml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"@

$rootRelsXml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"@

$documentRelsXml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"@

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$coreXml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:dcmitype="http://purl.org/dc/dcmitype/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>BUFIA System Detailed Flowchart</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">$timestamp</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">$timestamp</dcterms:modified>
</cp:coreProperties>
"@

$appXml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
    xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Office Word</Application>
</Properties>
"@

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

if (Test-Path $outputFullPath) {
    Remove-Item -LiteralPath $outputFullPath -Force
}

$fileStream = [System.IO.File]::Open($outputFullPath, [System.IO.FileMode]::CreateNew)
try {
    $archive = New-Object System.IO.Compression.ZipArchive($fileStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
    try {
        $entries = @(
            @{ Path = "[Content_Types].xml"; Content = $contentTypesXml },
            @{ Path = "_rels/.rels"; Content = $rootRelsXml },
            @{ Path = "word/document.xml"; Content = $documentXml },
            @{ Path = "word/_rels/document.xml.rels"; Content = $documentRelsXml },
            @{ Path = "docProps/core.xml"; Content = $coreXml },
            @{ Path = "docProps/app.xml"; Content = $appXml }
        )

        foreach ($entry in $entries) {
            $zipEntry = $archive.CreateEntry($entry.Path)
            $stream = $zipEntry.Open()
            $writer = New-Object System.IO.StreamWriter($stream, [System.Text.UTF8Encoding]::new($false))
            try {
                $writer.Write($entry.Content)
            }
            finally {
                $writer.Dispose()
            }
        }
    }
    finally {
        $archive.Dispose()
    }
}
finally {
    $fileStream.Dispose()
}

Write-Output "Created $outputFullPath"
