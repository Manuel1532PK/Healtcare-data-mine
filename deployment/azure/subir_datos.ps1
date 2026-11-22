<#
Sube a Azure Blob Storage una copia de los datos, reportes, figuras y modelos.
No modifica ni borra nada del repositorio.

La cuenta de almacenamiento y el contenedor ya deben existir.
Si no se pasa -ConnectionString, se toma la cadena de la propia cuenta con az.

Ejemplo:
  .\deployment\azure\subir_datos.ps1 -AccountName stnhanesdemoabc123 -ConnectionString "DefaultEndpointsProtocol=..."
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$AccountName,
  [string]$ResourceGroup = "rg-nhanes-demo",
  [string]$Container = "nhanes",
  [string]$ConnectionString = "",
  [switch]$OmitirLogin
)

$ErrorActionPreference = "Stop"

if (-not $ConnectionString) {
  if (-not $OmitirLogin) {
    az login
  }

  Write-Host "Leyendo la cadena de conexion de la cuenta..."
  $ConnectionString = az storage account show-connection-string `
    --name $AccountName `
    --resource-group $ResourceGroup `
    --query connectionString -o tsv

  if (-not $ConnectionString) {
    throw "No pudimos leer la cadena de conexion. Copiala desde Azure Portal > Access keys y pasala con -ConnectionString."
  }
}

$comun = @("--connection-string", $ConnectionString)

Write-Host "Asegurando el contenedor $Container..."
az storage container create --name $Container @comun | Out-Null

$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$artefactos = Join-Path $PSScriptRoot "artefactos"

if (-not (Test-Path $artefactos)) {
  Write-Host "No hay artefactos. Generando con exportar_modelo.py..."
  python (Join-Path $PSScriptRoot "exportar_modelo.py")
}

Write-Host "Subiendo artefactos de deployment/azure/artefactos..."
az storage blob upload-batch `
  --destination $Container `
  --source $artefactos `
  @comun `
  --overwrite | Out-Null

Write-Host "Subiendo los datos originales como copia..."
$datos = Join-Path $raiz "outputs\transformed"
az storage blob upload @comun --container-name $Container --overwrite `
  --file (Join-Path $datos "X_nhanes.csv") --name "datos/X_nhanes.csv" | Out-Null
az storage blob upload @comun --container-name $Container --overwrite `
  --file (Join-Path $datos "y_nhanes.csv") --name "datos/y_nhanes.csv" | Out-Null

Write-Host "`nListo. Cadena de conexion para Render:"
Write-Host $ConnectionString
