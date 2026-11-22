<#
Sube a Azure Blob Storage una copia de los datos, reportes, figuras y modelos.
No modifica ni borra nada del repositorio.

Ejemplo:
  .\deployment\azure\subir_datos.ps1 -AccountName stnhanesdemoabc123
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$AccountName,
  [string]$ResourceGroup = "rg-nhanes-demo",
  [string]$Container = "nhanes",
  [switch]$OmitirLogin
)

$ErrorActionPreference = "Stop"

if (-not $OmitirLogin) {
  az login
}

az group create --name $ResourceGroup --location eastus | Out-Null

az storage container create `
  --name $Container `
  --account-name $AccountName `
  --auth-mode login | Out-Null

$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$artefactos = Join-Path $PSScriptRoot "artefactos"

if (-not (Test-Path $artefactos)) {
  Write-Host "No hay artefactos. Generando con exportar_modelo.py…"
  python (Join-Path $PSScriptRoot "exportar_modelo.py")
}

Write-Host "Subiendo artefactos de deployment/azure/artefactos…"
az storage blob upload-batch `
  --account-name $AccountName `
  --destination $Container `
  --source $artefactos `
  --auth-mode login `
  --overwrite | Out-Null

Write-Host "Subiendo los datos originales como copia…"
$datos = Join-Path $raiz "outputs\transformed"
az storage blob upload --account-name $AccountName --container-name $Container --auth-mode login --overwrite `
  --file (Join-Path $datos "X_nhanes.csv") --name "datos/X_nhanes.csv" | Out-Null
az storage blob upload --account-name $AccountName --container-name $Container --auth-mode login --overwrite `
  --file (Join-Path $datos "y_nhanes.csv") --name "datos/y_nhanes.csv" | Out-Null

Write-Host "`nListo. Cadena de conexión para Render:"
az storage account show-connection-string `
  --name $AccountName `
  --resource-group $ResourceGroup `
  --query connectionString -o tsv
