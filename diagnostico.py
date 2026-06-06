"""
============================================================================
  ARCHIVO:    diagnostico.py
  PROPÓSITO:  Diagnosticar por qué el scraper no encuentra los planes.
              Muestra el HTML recibido y prueba diferentes selectores.
============================================================================
"""
import requests
from bs4 import BeautifulSoup
from config import HEADERS

URL = "https://www.mejorplan.com.co/internet-hogar"

print("=" * 70)
print("DIAGNÓSTICO DEL SCRAPER")
print("=" * 70)

# Paso 1: Descargar la página
print(f"\n[1] Descargando: {URL}")
respuesta = requests.get(URL, headers=HEADERS, timeout=15)
print(f"    Status code: {respuesta.status_code}")
print(f"    Tamaño HTML: {len(respuesta.text):,} caracteres")

# Paso 2: Verificar si recibimos contenido útil
html = respuesta.text
print(f"\n[2] ¿Contiene la palabra 'Mbps' en el HTML?")
print(f"    → {'SÍ' if 'Mbps' in html else 'NO'}")

print(f"\n[3] ¿Contiene la palabra 'plan' (en lowercase)?")
print(f"    → {'SÍ' if 'plan' in html.lower() else 'NO'}")

print(f"\n[4] ¿Contiene precios ($)?")
print(f"    → {'SÍ' if '$' in html else 'NO'}")

# Paso 3: Buscar enlaces "Ver plan"
soup = BeautifulSoup(html, "lxml")
import re
enlaces_ver_plan = soup.find_all("a", string=re.compile(r"Ver\s+plan", re.IGNORECASE))
print(f"\n[5] Enlaces 'Ver plan' encontrados: {len(enlaces_ver_plan)}")

# Paso 4: Mostrar primeros 3000 caracteres del HTML para inspeccionar
print(f"\n[6] PRIMEROS 3000 CARACTERES DEL HTML:")
print("-" * 70)
print(html[:3000])
print("-" * 70)

# Paso 5: Buscar otros elementos posibles
print(f"\n[7] Análisis de estructura HTML:")
print(f"    Total de <div>:     {len(soup.find_all('div'))}")
print(f"    Total de <article>: {len(soup.find_all('article'))}")
print(f"    Total de <a>:       {len(soup.find_all('a'))}")
print(f"    Total de <h3>:      {len(soup.find_all('h3'))}")

# Mostrar texto de los primeros h3 (probables nombres de plan)
print(f"\n[8] Primeros 10 elementos <h3>:")
for i, h3 in enumerate(soup.find_all('h3')[:10], 1):
    texto = h3.get_text(strip=True)
    print(f"    {i}. {texto[:80]}")

# Buscar el primer precio
print(f"\n[9] Primer precio encontrado en el HTML:")
match = re.search(r'\$\s*[\d.,]+\s*/?\s*mes', html)
if match:
    print(f"    → '{match.group(0)}'")
    posicion = match.start()
    print(f"    → Contexto: ...{html[max(0,posicion-100):posicion+100]}...")
else:
    print(f"    → NO se encontró ningún precio con el patrón esperado")