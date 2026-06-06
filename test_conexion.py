"""
============================================================================
  ARCHIVO:    test_conexion.py
  PROPÓSITO:  Probar la conexión a SQL Server desde Python antes de
              ejecutar el scraper. Verifica que pyodbc, el driver ODBC
              y la base de datos TeleConecta_Churn estén funcionando.
============================================================================
"""

import pyodbc
from config import get_connection_string

print("=" * 60)
print("PRUEBA DE CONEXIÓN A SQL SERVER")
print("=" * 60)

# Paso 1: Mostrar la cadena de conexión
cadena = get_connection_string()
print(f"\n[1] Cadena de conexión:\n    {cadena}")

# Paso 2: Intentar conectar
try:
    print("\n[2] Conectando a SQL Server...")
    conexion = pyodbc.connect(cadena, timeout=10)
    print("    ✓ Conexión exitosa.")

    # Paso 3: Ejecutar una consulta simple
    print("\n[3] Ejecutando consulta de prueba...")
    cursor = conexion.cursor()
    cursor.execute("SELECT @@SERVERNAME AS Servidor, DB_NAME() AS BaseDatos;")
    fila = cursor.fetchone()
    print(f"    ✓ Servidor:    {fila.Servidor}")
    print(f"    ✓ Base datos:  {fila.BaseDatos}")

    # Paso 4: Verificar que la tabla Operadores_Sector existe
    print("\n[4] Verificando la tabla Operadores_Sector...")
    cursor.execute("""
        SELECT COUNT(*) AS Total_Columnas
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_NAME = 'Operadores_Sector';
    """)
    total = cursor.fetchone().Total_Columnas
    if total == 12:
        print(f"    ✓ Tabla Operadores_Sector existe con {total} columnas.")
    elif total > 0:
        print(f"    ⚠ Tabla existe pero tiene {total} columnas (se esperaban 12).")
    else:
        print("    ✗ Tabla Operadores_Sector NO existe. Ejecuta el script 05 en SSMS.")

    # Paso 5: Cerrar conexión
    cursor.close()
    conexion.close()
    print("\n[5] Conexión cerrada correctamente.")
    print("\n" + "=" * 60)
    print(" ✓ TODO OK - PYTHON Y SQL SERVER SE COMUNICAN CORRECTAMENTE")
    print("=" * 60)

except pyodbc.Error as ex:
    sqlstate = ex.args[0] if ex.args else 'desconocido'
    print(f"\n✗ ERROR DE CONEXIÓN")
    print(f"    Código:  {sqlstate}")
    print(f"    Detalle: {ex}")
    print("\nRevisa que:")
    print("  - SQL Server esté corriendo")
    print("  - El nombre del servidor en config.py sea correcto")
    print("  - La base de datos TeleConecta_Churn exista")