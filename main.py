from collections import Counter
from fastapi import FastAPI, HTTPException
import re
from bs4 import BeautifulSoup
from pydantic import BaseModel
import requests

app = FastAPI(
    title="DevBoost Utility Suite API",
    description="Next-gen utility API with disposable email detection, smart intent text analysis, and OpenGraph web scraping.",
    version="2.0.0",
)

# 1. Endpoint de Validación Avanzada (Anti-Spam & Data Cleaning)
class DataRequest(BaseModel):
  email: str
  phone: str


DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "10minutemail.com",
    "tempmail.com",
    "guerrillamail.com",
    "yopmail.com",
    "sharklasers.com",
}


@app.post("/validate-data")
def validate_data(payload: DataRequest):
  email = payload.email.strip().lower()
  phone = payload.phone.strip()

  email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
  is_format_valid = bool(re.match(email_regex, email))

  domain = email.split("@")[-1] if "@" in email else ""
  is_disposable = domain in DISPOSABLE_DOMAINS

  clean_phone = re.sub(r"[^\d+]", "", phone)
  is_paraguay = clean_phone.startswith("+595") or (
      clean_phone.startswith("09") and len(clean_phone) >= 10
  )

  return {
      "status": "success",
      "data": {
          "email": email,
          "is_format_valid": is_format_valid,
          "is_disposable_email": is_disposable,
          "clean_phone": clean_phone,
          "likely_paraguay_number": is_paraguay,
      },
  }


# 2. Endpoint de Análisis de Texto Inteligente (Sentimiento + Intento + Keywords)
class TextRequest(BaseModel):
  text: str


@app.post("/analyze-text")
def analyze_text(payload: TextRequest):
  content = payload.text.strip()
  if not content:
    raise HTTPException(
        status_code=400, detail="El campo 'text' no puede estar vacío."
    )

  words = content.split()
  lower_text = content.lower()

  # Análisis de Sentimiento
  sentiment = "neutral"
  if any(
      w in lower_text
      for w in [
          "excelente",
          "bueno",
          "genial",
          "feliz",
          "recomiendo",
          "perfecto",
          "maravilloso",
      ]
  ):
    sentiment = "positivo"
  elif any(
      w in lower_text
      for w in [
          "malo",
          "pésimo",
          "horrible",
          "falla",
          "lento",
          "terrible",
          "estafa",
          "basura",
      ]
  ):
    sentiment = "negativo"

  # Detección de Intención de Negocio
  intent = "general"
  if "?" in content or any(
      w in lower_text for w in ["cómo", "dónde", "cuánto", "ayuda", "precio"]
  ):
    intent = "consulta"
  elif sentiment == "negativo" or any(
      w in lower_text for w in ["reclamo", "problema", "falla", "error"]
  ):
    intent = "reclamo"
  elif sentiment == "positivo":
    intent = "elogio"

  # Extracción de palabras clave principales
  stop_words = {
      "el",
      "la",
      "los",
      "las",
      "un",
      "una",
      "de",
      "del",
      "a",
      "en",
      "y",
      "o",
      "que",
      "es",
      "por",
      "con",
      "para",
  }
  filtered_words = [
      re.sub(r"[^\w]", "", w.lower())
      for w in words
      if len(w) > 3 and w.lower() not in stop_words
  ]
  common_keywords = [
      word for word, count in Counter(filtered_words).most_common(3)
  ]

  return {
      "status": "success",
      "metrics": {
          "word_count": len(words),
          "char_count": len(content),
          "sentiment": sentiment,
          "detected_intent": intent,
          "top_keywords": common_keywords,
      },
  }


# 3. Endpoint de Web Scraping con Metadatos OpenGraph (Para Previews)
class ScrapeRequest(BaseModel):
  url: str


@app.post("/scrape-url")
def scrape_url(payload: ScrapeRequest):
  url = payload.url.strip()
  if not url.startswith("http"):
    raise HTTPException(
        status_code=400,
        detail="URL inválida. Debe comenzar con http:// o https://",
    )

  try:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=5)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = (
        soup.title.string.strip() if soup.title and soup.title.string else "Sin título"
    )

    # Extracción OpenGraph (Metadatos de redes sociales)
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    og_img = soup.find("meta", property="og:image")

    open_graph = {
        "og_title": og_title["content"] if og_title else None,
        "og_description": og_desc["content"] if og_desc else None,
        "og_image": og_img["content"] if og_img else None,
    }

    # Limpieza de elementos innecesarios para el snippet de texto
    for element in soup(["script", "style", "nav", "footer", "header"]):
      element.extract()
    snippet = soup.get_text(separator=" ", strip=True)[:800]

    return {
        "status": "success",
        "url": url,
        "title": title,
        "open_graph": open_graph,
        "content_snippet": snippet,
    }
  except requests.exceptions.Timeout:
    raise HTTPException(
        status_code=504,
        detail="El tiempo de espera para conectar con la URL ha expirado.",
    )
  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error al procesar la URL: {str(e)}"
    )


@app.get("/")
def root():
  return {"message": "DevBoost Utility Suite API (v2.0) activa y funcionando 24/7."}