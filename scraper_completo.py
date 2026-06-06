"""
============================================================================
  ARCHIVO:    scraper_completo.py
  PROPÓSITO:  Versión completa del scraper que extrae planes de
              mejorplan.com.co Y los inserta en SQL Server (tabla
              Planes_Sector de la base de datos TeleConecta_Churn).
  PROYECTO:   EA2 - CRISP-DM Fase 3 (Web Scraping + Carga a BD)

  FLUJO:
    1. Extraer planes con el scraper (importado de scraper_planes.py)
    2. Conectar a SQL Server
    3. Vaciar la tabla Planes_Sector (para evitar duplicados)
    4. Insertar todos los planes en lote
    5. Verificar la carga ejecutando una consulta de conteo

  HERRAMIENTAS:
    - scraper_planes (módulo propio)
    - pyodbc - conexión a SQL Server
============================================================================
"""

import pyodbc
from datetime import datetime

from config import get_connection_string
from scraper_planes import main as ejecutar_scraping


# ============================================================================
# FUNCIONES DE BASE DE DATOS
# ============================================================================

def conectar_sql_server():
    """
    Establece la conexión a SQL Server usando los parámetros de config.py
    Devuelve el objeto conexión o None si falla.
    """
    try:
        cadena = get_connection_string()
        conexion = pyodbc.connect(cadena, timeout=10)
        return conexion
    except pyodbc.Error as e:
        print(f"✗ Error al conectar a SQL Server: {e}")
        return None


def vaciar_tabla(conexion):
    """
    Vacía la tabla Planes_Sector para permitir una carga limpia.
    Resetea el contador IDENTITY a 0.
    """
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM dbo.Planes_Sector;")
    cursor.execute("DBCC CHECKIDENT ('dbo.Planes_Sector', RESEED, 0);")
    conexion.commit()
    cursor.close()


def insertar_planes(conexion, planes):
    """
    Inserta una lista de planes en la tabla Planes_Sector usando
    executemany para mayor eficiencia. Retorna el número de filas insertadas.
    """
    cursor = conexion.cursor()

    # SQL parametrizado: previene SQL injection y es más eficiente
    sql_insert = """
        INSERT INTO dbo.Planes_Sector (
            operador, nombre_plan, tecnologia, velocidad_mbps,
            precio_cop, permanencia_meses, servicios_adicionales,
            url_fuente, fecha_extraccion
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    # Construir la lista de tuplas a insertar
    datos = [
        (
            p["operador"],
            p["nombre_plan"],
            p["tecnologia"],
            p["velocidad_mbps"],
            p["precio_cop"],
            p["permanencia_meses"],
            p["servicios_adicionales"],
            p["url_fuente"],
            p["fecha_extraccion"],
        )
        for p in planes
    ]

    # Inserción en lote
    cursor.fast_executemany = True  # acelera la inserción masiva
    cursor.executemany(sql_insert, datos)
    conexion.commit()
    filas_insertadas = cursor.rowcount
    cursor.close()
    return filas_insertadas


def verificar_carga(conexion):
    """
    Ejecuta consultas de verificación para confirmar que los datos
    quedaron correctamente cargados.
    """
    cursor = conexion.cursor()

    # 1. Conteo total
    cursor.execute("SELECT COUNT(*) FROM dbo.Planes_Sector;")
    total = cursor.fetchone()[0]
    print(f"\n  Total de registros en Planes_Sector: {total}")

    # 2. Conteo por operador
    print("\n  Distribución por operador:")
    cursor.execute("""
        SELECT operador, COUNT(*) AS Total
          FROM dbo.Planes_Sector
         GROUP BY operador
         ORDER BY Total DESC;
    """)
    for fila in cursor.fetchall():
        print(f"    {fila.operador:35s}: {fila.Total} planes")

    # 3. Estadísticas de precio
    print("\n  Estadísticas de precio (COP):")
    cursor.execute("""
        SELECT MIN(precio_cop) AS Minimo,
               MAX(precio_cop) AS Maximo,
               AVG(precio_cop) AS Promedio
          FROM dbo.Planes_Sector;
    """)
    fila = cursor.fetchone()
    print(f"    Mínimo:   ${fila.Minimo:,}")
    print(f"    Máximo:   ${fila.Maximo:,}")
    print(f"    Promedio: ${int(fila.Promedio):,}")

    # 4. Muestra de los 5 planes más económicos
    print("\n  Top 5 planes más económicos:")
    cursor.execute("""
        SELECT TOP 5 operador, nombre_plan, velocidad_mbps, precio_cop
          FROM dbo.Planes_Sector
         ORDER BY precio_cop ASC;
    """)
    for fila in cursor.fetchall():
        print(f"    {fila.operador:30s} | {fila.nombre_plan:40s} | "
              f"{fila.velocidad_mbps or 'N/A'} Mbps | ${fila.precio_cop:,}")

    cursor.close()


# ============================================================================
# ORQUESTACIÓN PRINCIPAL
# ============================================================================

def main():
    print("\n" + "=" * 70)
    print("EA2 - SCRAPING + CARGA A SQL SERVER")
    print("=" * 70)

    # === FASE 1: Ejecutar el scraper ===
    print("\n>>> FASE 1: Extracción de datos desde mejorplan.com.co <<<")
    planes = ejecutar_scraping()

    if not planes:
        print("\n✗ No se extrajeron planes. Se aborta la carga a BD.")
        return

    # === FASE 2: Conexión a SQL Server ===
    print("\n\n>>> FASE 2: Carga a SQL Server <<<")
    print("\n[1] Conectando a SQL Server...")
    conexion = conectar_sql_server()
    if conexion is None:
        return
    print("    ✓ Conexión exitosa.")

    try:
        # === FASE 3: Vaciar la tabla ===
        print("\n[2] Vaciando la tabla Planes_Sector...")
        vaciar_tabla(conexion)
        print("    ✓ Tabla vaciada (contador IDENTITY reseteado).")

        # === FASE 4: Inserción ===
        print(f"\n[3] Insertando {len(planes)} planes en lote...")
        filas = insertar_planes(conexion, planes)
        print(f"    ✓ {filas} planes insertados correctamente.")

        # === FASE 5: Verificación ===
        print("\n[4] Verificación post-inserción:")
        verificar_carga(conexion)

        print("\n" + "=" * 70)
        print(" ✓ PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        print("\nPuedes verificar los datos en SSMS con la consulta:")
        print("    SELECT * FROM TeleConecta_Churn.dbo.Planes_Sector;")

    except pyodbc.Error as e:
        print(f"\n✗ Error durante la inserción: {e}")
        conexion.rollback()
    finally:
        conexion.close()
        print("\n[5] Conexión cerrada.")


if __name__ == "__main__":
    main()