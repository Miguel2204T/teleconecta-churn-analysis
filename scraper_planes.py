"""
============================================================================
  ARCHIVO:    scraper_planes.py
  PROPÓSITO:  Scraper que extrae los planes de internet de operadores
              colombianos desde mejorplan.com.co.
  PROYECTO:   EA2 - CRISP-DM Fase 3
  VERSIÓN:    2.0 - Basado en estructura real del sitio (h3 + contenedor)
============================================================================
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import URLS_PAGINAS, HEADERS, DELAY_ENTRE_PETICIONES


def limpiar_precio(texto):
    """Convierte '$ 79.900/mes' a 79900 (int). Devuelve None si falla."""
    if not texto:
        return None
    # Tomar SOLO la primera ocurrencia de un precio (no concatenar varios)
    match = re.search(r"\$\s*[\d.,]+", texto)
    if not match:
        return None
    solo_numero = re.sub(r"[^\d]", "", match.group(0))
    return int(solo_numero) if solo_numero else None


def limpiar_velocidad(texto):
    """Extrae la velocidad numérica del primer 'XXXMbps' encontrado."""
    if not texto:
        return None
    coincidencia = re.search(r"(\d+)\s*Mbps", texto, flags=re.IGNORECASE)
    return int(coincidencia.group(1)) if coincidencia else None


def limpiar_permanencia(texto):
    """'Sin contrato' -> 0; 'Permanencia mínima: 12 meses' -> 12; None si no aplica."""
    if not texto:
        return None
    texto_lower = texto.lower()
    if "sin contrato" in texto_lower or "sin permanencia" in texto_lower:
        return 0
    coincidencia = re.search(r"(\d+)\s*mes", texto_lower)
    return int(coincidencia.group(1)) if coincidencia else None


def descargar_pagina(url):
    """Descarga HTML con manejo de errores. Devuelve string o None."""
    try:
        respuesta = requests.get(url, headers=HEADERS, timeout=15)
        respuesta.raise_for_status()
        return respuesta.text
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error al descargar {url}")
        print(f"    Detalle: {e}")
        return None



def es_h3_de_plan(h3):
    """
    Determina si un <h3> corresponde a un plan (no a un encabezado del sitio).
    Los h3 de planes contienen palabras como 'Internet', 'Combo', 'Fibrazo', etc.
    Los h3 de UI son cortos: 'Operador', 'Velocidad mínima', etc.
    """
    texto = h3.get_text(strip=True)
    if len(texto) < 12:  # Los nombres reales de planes son más largos
        return False
    palabras_clave = ["internet", "combo", "fibrazo", "fiesta", "megas",
                       "fibra", "plan", "starlink"]
    return any(p in texto.lower() for p in palabras_clave)


def extraer_planes_de_pagina(html, url_pagina):
    """
    Extrae todos los planes de una página parseando los <h3> de cada tarjeta.
    Para cada h3 válido, sube al contenedor padre y extrae operador, precio,
    tecnología, velocidad, permanencia y servicios adicionales.
    """
    soup = BeautifulSoup(html, "lxml")
    planes = []

    # Buscar todos los h3 que parezcan nombres de planes
    h3_planes = [h for h in soup.find_all("h3") if es_h3_de_plan(h)]

    print(f"    Detectados {len(h3_planes)} bloques <h3> de planes.")

    for h3 in h3_planes:
        nombre_plan = h3.get_text(strip=True)

        # Subimos en el árbol DOM hasta encontrar un contenedor que tenga
        # toda la información (precio, velocidad, tecnología)
        contenedor = h3
        for _ in range(8):
            contenedor = contenedor.find_parent()
            if contenedor is None:
                break
            texto_completo = contenedor.get_text(" ", strip=True)
            # El contenedor debe tener al menos el precio y Mbps
            if "/mes" in texto_completo and "Mbps" in texto_completo:
                break

        if contenedor is None:
            continue

        texto = contenedor.get_text(" ", strip=True)

        # Extraer cada dato del plan
        precio    = limpiar_precio(texto)
        velocidad = limpiar_velocidad(texto)
        permanencia = limpiar_permanencia(texto)
        tecnologia = detectar_tecnologia(texto)
        operador   = inferir_operador(nombre_plan, contenedor)
        servicios  = extraer_servicios_adicionales(texto)
        url_fuente = obtener_url_operador(contenedor, url_pagina)

        # Solo guardamos si tenemos lo mínimo
        if nombre_plan and precio:
            planes.append({
                "operador":              operador,
                "nombre_plan":           nombre_plan,
                "tecnologia":            tecnologia,
                "velocidad_mbps":        velocidad,
                "precio_cop":            precio,
                "permanencia_meses":     permanencia,
                "servicios_adicionales": servicios,
                "url_fuente":            url_fuente,
                "fecha_extraccion":      datetime.now(),
            })

    return planes


def detectar_tecnologia(texto):
    """Detecta la tecnología en el texto: Fibra óptica, Cable o Satelital."""
    texto_lower = texto.lower()
    if "fibra" in texto_lower:
        return "Fibra óptica"
    if "cable" in texto_lower or "hfc" in texto_lower:
        return "Cable"
    if "satelital" in texto_lower or "starlink" in texto_lower:
        return "Satelital"
    return None


def inferir_operador(nombre_plan, contenedor):
    """Identifica el operador a partir del nombre del plan o del contenedor."""
    operadores = {
        "claro":      "Claro Colombia",
        "movistar":   "Movistar Colombia",
        "tigo":       "Tigo Colombia",
        "etb":        "ETB",
        "une":        "UNE EPM",
        "wom":        "WOM Colombia",
        "celsia":     "Celsia Internet",
        "emcali":     "EMCALI",
        "fiesta":     "Fiesta Telecomunicaciones",
        "hv":         "HV Multiplay",
        "fibrazo":    "Fibrazo",
        "starlink":   "Starlink",
    }
    texto = (nombre_plan or "").lower()
    if contenedor is not None:
        texto += " " + contenedor.get_text(" ", strip=True).lower()
    for clave, valor in operadores.items():
        if clave in texto:
            return valor
    return "Desconocido"


def extraer_servicios_adicionales(texto):
    """Detecta servicios como Amazon Prime, HBO Max, etc."""
    servicios = []
    candidatos = ["Amazon Prime", "HBO Max", "Paramount+", "DGO", "Universal+",
                  "Win Play", "Hot Go", "Max", "Win+", "Netflix"]
    for s in candidatos:
        if s.lower() in texto.lower():
            servicios.append(s)
    return ", ".join(servicios) if servicios else None


def obtener_url_operador(contenedor, url_pagina):
    """Busca el primer enlace externo dentro del contenedor del plan."""
    if contenedor is None:
        return url_pagina
    for enlace in contenedor.find_all("a", href=True):
        href = enlace["href"]
        if href.startswith("http") and "mejorplan.com.co" not in href:
            return href
    return url_pagina


# ============================================================================
# ORQUESTACIÓN PRINCIPAL
# ============================================================================

def main():
    print("=" * 70)
    print("SCRAPER DE PLANES DE INTERNET - mejorplan.com.co")
    print("=" * 70)
    print(f"Total de páginas a procesar: {len(URLS_PAGINAS)}")
    print(f"Delay entre peticiones: {DELAY_ENTRE_PETICIONES}s")
    print("=" * 70)

    todos_los_planes = []

    for i, url in enumerate(URLS_PAGINAS, 1):
        print(f"\n[Página {i}/{len(URLS_PAGINAS)}] {url}")
        html = descargar_pagina(url)
        if html is None:
            continue

        planes = extraer_planes_de_pagina(html, url)
        print(f"  ✓ {len(planes)} planes extraídos correctamente.")
        todos_los_planes.extend(planes)

        if i < len(URLS_PAGINAS):
            time.sleep(DELAY_ENTRE_PETICIONES)

    # Resumen
    print("\n" + "=" * 70)
    print(f"SCRAPING COMPLETADO")
    print(f"  Total de planes extraídos: {len(todos_los_planes)}")
    print("=" * 70)

    if not todos_los_planes:
        print("\n⚠ No se extrajo ningún plan. Revisa el diagnóstico.")
        return []

    # Mostrar muestra
    print("\nMUESTRA DE LOS PRIMEROS 10 PLANES:")
    print("-" * 70)
    for p in todos_los_planes[:10]:
        print(f"\n• {p['operador']} | {p['nombre_plan']}")
        print(f"    Tecnología:    {p['tecnologia']}")
        print(f"    Velocidad:     {p['velocidad_mbps']} Mbps")
        print(f"    Precio:        ${p['precio_cop']:,} COP/mes")
        print(f"    Permanencia:   {p['permanencia_meses']} meses")
        if p['servicios_adicionales']:
            print(f"    Servicios:     {p['servicios_adicionales']}")

    # Estadística por operador
    print("\n" + "=" * 70)
    print("ESTADÍSTICA - Planes por operador:")
    print("-" * 70)
    operadores = {}
    for p in todos_los_planes:
        operadores[p['operador']] = operadores.get(p['operador'], 0) + 1
    for op, cant in sorted(operadores.items(), key=lambda x: -x[1]):
        print(f"  {op:35s}: {cant} planes")

    return todos_los_planes


if __name__ == "__main__":
    main()