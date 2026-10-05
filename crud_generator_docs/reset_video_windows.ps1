# Deja devdb (PostgreSQL 18 local, 127.0.0.1:5432) como al inicio del video:
# roles crud_* + esquema lab con 6 tablas, sin datos generados, sin rutinas y
# SIN la extension crud_generator (CREATE EXTENSION forma parte de la grabacion).
# La clave no se escribe aqui: psql la pide o se toma de $env:PGPASSWORD.
#
# Uso (desde la raiz del repo):
#   powershell -ExecutionPolicy Bypass -File crud_generator_docs\reset_video_windows.ps1

$ErrorActionPreference = 'Stop'
$psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
$repo = Split-Path -Parent $PSScriptRoot
$conn = @('-h', '127.0.0.1', '-U', 'postgres', '-d', 'devdb', '-v', 'ON_ERROR_STOP=1', '-q')

& $psql @conn -c 'DROP SCHEMA IF EXISTS lab CASCADE;' `
              -c 'DROP EXTENSION IF EXISTS crud_generator CASCADE;' `
              -c 'DROP SCHEMA IF EXISTS crud_generator CASCADE;'
& $psql @conn -f (Join-Path $repo 'tests\fixtures\01_roles.sql')
& $psql @conn -f (Join-Path $repo 'tests\fixtures\02_schema.sql')
& $psql @conn -c "SELECT count(*) AS tablas_lab FROM pg_tables WHERE schemaname = 'lab';"
Write-Host 'Laboratorio listo para grabar.'
