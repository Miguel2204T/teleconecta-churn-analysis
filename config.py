
# ============================================================================
# CONFIGURACIÓN DE LA CONEXIÓN A SQL SERVER
# ============================================================================
# Estos valores corresponden a la instancia local de SQL Server.
# Para usar autenticación de Windows, dejamos TRUSTED_CONNECTION en True
# y NO se requieren usuario ni contraseña.

DB_CONFIG = {
    "driver":   "{ODBC Driver 17 for SQL Server}",
    "server":   "MIGUEL",            # Nombre de tu servidor (visto en SSMS)
    "database": "TeleConecta_Churn", # Base de datos creada en la EA1
    "trusted_connection": "yes",     # Autenticación de Windows
}


def get_connection_string():
    """
    Construye la cadena de conexión ODBC a SQL Server.
    Retorna un string en formato compatible con pyodbc.
    """
    return (
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection={DB_CONFIG['trusted_connection']};"
    )


# ============================================================================
# CONFIGURACIÓN DEL SCRAPER
# ============================================================================
# URL base del sitio: comparador de planes de internet en Colombia.
# El sitio expone los planes en HTML estático, ideal para BeautifulSoup.
# Tiene paginación nativa con el parámetro ?page=N

URL_BASE = "https://www.mejorplan.com.co/internet-hogar"

# Lista de URLs paginadas. El sitio tiene 2 páginas con 36 planes en total.
URLS_PAGINAS = [
    "https://www.mejorplan.com.co/internet-hogar?page=1",
    "https://www.mejorplan.com.co/internet-hogar?page=2",
]


# Headers HTTP: identifican al scraper de forma transparente.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
}


# Tiempo de espera entre peticiones (en segundos) para no saturar el servidor.
DELAY_ENTRE_PETICIONES = 2