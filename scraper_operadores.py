"""
============================================================================
  ARCHIVO:    scraper_operadores.py
  PROPÓSITO:  Scraper que extrae información de los principales operadores
              de telecomunicaciones de Colombia desde Wikipedia y la
              almacena en la base de datos TeleConecta_Churn.
  PROYECTO:   EA2 - CRISP-DM Fase 3 (Preparación de Datos vía Web Scraping)
  AUTOR:      [Nombre del estudiante]
  FECHA:      2026
============================================================================

  ESTRATEGIA:
    1. Recorre la lista URLS_OPERADORES (paginación entre 5 páginas)
    2. Para cada operador: descarga HTML, parsea con BeautifulSoup,
       extrae datos del 'infobox' lateral de Wikipedia
    3. Limpia y normaliza los datos extraídos
    4. (En la Etapa B) Inserta cada registro en SQL Server

  HERRAMIENTAS:
    - requests: peticiones HTTP
    - BeautifulSoup4: parseo de HTML
    - lxml: motor de parseo eficiente
============================================================================
"""

import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import URLS_OPERADORES, HEADERS, DELAY_ENTRE_PETICIONES


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def descargar_pagina(url):
    """
    Descarga el HTML de una URL.
    Maneja errores comunes (timeout, conexión, status code).
    Devuelve el HTML como string, o None si falla.
    """
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=15)
        respuesta.raise_for_status()  # lanza excepción si status no es 2xx
        return respuesta.text
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error al descargar {url}")
        print(f"    Detalle: {e}")
        return None


def extraer_infobox(soup):
    """
    Localiza el 'infobox' lateral de Wikipedia (tabla con datos clave del
    operador) y lo devuelve como un diccionario {etiqueta: valor}.

    Wikipedia usa la clase 'infobox' para estas tablas. Cada fila tiene:
      - <th> con la etiqueta (ej: 'Fundación', 'Sede')
      - <td> con el valor
    """
    infobox = soup.find("table", class_=lambda c: c and "infobox" in c)
    if infobox is None:
        return {}

    datos = {}
    for fila in infobox.find_all("tr"):
        th = fila.find("th")
        td = fila.find("td")
        if th and td:
            etiqueta = th.get_text(strip=True).lower()
            # Limpia saltos de línea y referencias [1], [2], etc.
            valor = td.get_text(separator=" ", strip=True)
            valor = " ".join(valor.split())  # colapsa espacios múltiples
            if etiqueta and valor:
                datos[etiqueta] = valor
    return datos


def obtener_valor(infobox, posibles_claves):
    """
    Busca un valor en el infobox probando varias claves posibles.
    Devuelve el primer valor encontrado o None.

    Esto es útil porque Wikipedia no es consistente con las etiquetas:
    a veces dice 'Fundación', a veces 'Fundada', a veces 'Creación', etc.
    """
    for clave in posibles_claves:
        for etiqueta, valor in infobox.items():
            if clave.lower() in etiqueta:
                return valor
    return None


def limpiar_anio(texto):
    """
    Extrae el año (4 dígitos) de un texto como 'Fundada en 1993 en Bogotá'.
    Devuelve None si no encuentra ningún año válido.
    """
    if not texto:
        return None
    import re
    coincidencia = re.search(r"\b(1[89]\d{2}|20\d{2})\b", texto)
    if coincidencia:
        return int(coincidencia.group(1))
    return None


def extraer_nombre_operador(soup, url):
    """
    Extrae el nombre del operador desde el título principal de la página.
    """
    titulo = soup.find("h1", id="firstHeading")
    if titulo:
        return titulo.get_text(strip=True)
    # Fallback: usar el último segmento de la URL
    return url.split("/")[-1].replace("_", " ")


# ============================================================================
# FUNCIÓN PRINCIPAL DE SCRAPING
# ============================================================================

def scrapear_operador(url):
    """
    Scrapea una página de Wikipedia de un operador y devuelve un diccionario
    con los 11 campos definidos en el modelo de datos.
    """
    print(f"  → Descargando: {url}")
    html = descargar_pagina(url)
    if html is None:
        return None

    soup = BeautifulSoup(html, "lxml")
    infobox = extraer_infobox(soup)

    # Si no encontramos infobox, no podemos extraer datos útiles
    if not infobox:
        print("    ⚠ No se encontró infobox en esta página.")

    datos = {
        "nombre_operador":       extraer_nombre_operador(soup, url),
        "tipo_empresa":          obtener_valor(infobox, ["tipo"]),
        "sector":                obtener_valor(infobox, ["industria", "sector"]),
        "sede_principal":        obtener_valor(infobox, ["sede", "domicilio"]),
        "anio_fundacion":        limpiar_anio(
                                    obtener_valor(infobox, ["fundación", "fundada", "creación"])
                                 ),
        "pais_origen":           obtener_valor(infobox, ["país", "ubicación"]),
        "sitio_web":             obtener_valor(infobox, ["sitio web", "web"]),
        "servicios_principales": obtener_valor(infobox, ["productos", "servicios"]),
        "empresa_matriz":        obtener_valor(infobox, ["empresa matriz", "matriz", "propietario"]),
        "url_wikipedia":         url,
        "fecha_extraccion":      datetime.now(),
    }
    return datos


# ============================================================================
# ORQUESTACIÓN: recorrer todas las URLs (PAGINACIÓN)
# ============================================================================

def main():
    print("=" * 70)
    print("SCRAPER DE OPERADORES DE TELECOMUNICACIONES - WIKIPEDIA")
    print("=" * 70)
    print(f"Total de operadores a procesar: {len(URLS_OPERADORES)}")
    print(f"Delay entre peticiones: {DELAY_ENTRE_PETICIONES}s")
    print("=" * 70)

    resultados = []
    for i, url in enumerate(URLS_OPERADORES, 1):
        print(f"\n[{i}/{len(URLS_OPERADORES)}] Procesando operador...")
        datos = scrapear_operador(url)
        if datos:
            resultados.append(datos)
            print(f"  ✓ {datos['nombre_operador']}")
            print(f"    Sede:          {datos['sede_principal']}")
            print(f"    Fundación:     {datos['anio_fundacion']}")
            print(f"    Empresa matriz:{datos['empresa_matriz']}")
        else:
            print("  ✗ No se pudo extraer información.")

        # Pausa entre peticiones para no saturar el servidor
        if i < len(URLS_OPERADORES):
            time.sleep(DELAY_ENTRE_PETICIONES)

    # Resumen final
    print("\n" + "=" * 70)
    print(f"SCRAPING COMPLETADO")
    print(f"  Operadores procesados con éxito: {len(resultados)}/{len(URLS_OPERADORES)}")
    print("=" * 70)

    # Mostrar todos los datos extraídos
    print("\nDATOS EXTRAÍDOS:")
    print("-" * 70)
    for d in resultados:
        print(f"\n• {d['nombre_operador']}")
        for clave, valor in d.items():
            if clave != "nombre_operador":
                print(f"    {clave:25s}: {valor}")

    return resultados


if __name__ == "__main__":
    main()