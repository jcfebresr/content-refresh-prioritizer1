"""
Local SEO Geo-Gap Analyzer v2.3
Sprint 3.1 - Filtros Interactivos + UI Mejorada
- Filtros por prioridad, competidores y zona
- Búsqueda en tiempo real
- Ordenamiento clickeable
- Preparado para integración API (próximo sprint)
"""

import streamlit as st
import pandas as pd
import advertools as adv
import re
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode
from urllib.parse import urlparse, urljoin
from rapidfuzz import fuzz
import time

# ============================================
# CONFIGURACIÓN MULTIIDIOMA
# ============================================

TRANSLATIONS = {
    "es": {
        "title": "🎯 Local SEO Geo-Gap Analyzer",
        "language": "Idioma / Language",
        "service": "Servicio",
        "your_domain": "Tu dominio",
        "competitor": "Competidor",
        "domain_placeholder": "ejemplo.com (sin https://)",
        "analyze_button": "🚀 Analizar Gaps",
        "min_competitors": "❌ Debes ingresar exactamente 3 competidores",
        "invalid_domain": "❌ Dominio inválido",
        "home_zone_detected": "🏠 Zona base detectada",
        "is_correct": "¿Es correcto?",
        "yes": "✓ Sí",
        "no": "✗ No, cambiar",
        "select_city": "Selecciona tu ciudad principal",
        "sitemap_found": "✅ Sitemap detectado",
        "sitemap_robots": "✅ Sitemap en robots.txt",
        "no_sitemap": "⚠️ Sin sitemap (crawling fallback)",
        "domain_error": "❌ No accesible, verifica dominio",
        "analyzing": "Analizando",
        "extracting_urls": "Extrayendo URLs",
        "processing": "Procesando",
        "gaps_found": "Gaps Detectados",
        "strengths_found": "Tus Fortalezas",
        "ties_found": "Empates",
        "low_confidence": "Baja Confianza - Revisar",
        "zone": "Zona",
        "slug": "Slug Sugerido",
        "competitors_count": "Nº Comps",
        "confidence": "Confianza",
        "advantage": "Ventaja",
        "strategy": "Estrategia",
        "priority": "Prioridad",
        "confirm": "Confirmar",
        "required_field": "Campo obligatorio",
        "duplicate_domains": "Los dominios deben ser diferentes entre sí",
        "urls_filtered": "URLs filtradas por servicio diferente",
        "high_priority": "ALTA",
        "medium_priority": "MEDIA",
        "low_priority": "BAJA",
        "max_advantage": "MÁXIMA (zona única)",
        "medium_advantage": "MEDIA (baja competencia)",
        "maintain_dominance": "Mantener dominancia. Reforzar contenido y backlinks.",
        "early_advantage": "Ventaja temprana. Invertir en diferenciación.",
        "competitive_market": "Mercado competitivo. Mantener posición con contenido de calidad.",
        "validated_opportunity": "Oportunidad Validada - todos los competidores están ahí",
        "emerging_niche": "Nicho Emergente - mayoría presente",
        "long_tail": "Larga Cola / Experimental - solo uno lo tiene",
        "filter_by_priority": "Filtrar por prioridad",
        "filter_by_competitors": "Filtrar por Nº competidores",
        "search_zone": "Buscar zona",
        "all": "Todas",
        "show_results": "Mostrando",
        "of": "de",
        "results": "resultados",
        "no_gaps_filter": "No hay gaps que coincidan con los filtros",
        "export_csv": "📥 Exportar CSV",
        "export_json": "📥 Exportar JSON",
        "export_markdown": "📥 Exportar Markdown",
        "copy_slugs": "📋 Copiar Slugs",
    },
    "en": {
        "title": "🎯 Local SEO Geo-Gap Analyzer",
        "language": "Idioma / Language",
        "service": "Service",
        "your_domain": "Your domain",
        "competitor": "Competitor",
        "domain_placeholder": "example.com (without https://)",
        "analyze_button": "🚀 Analyze Gaps",
        "min_competitors": "❌ You must enter exactly 3 competitors",
        "invalid_domain": "❌ Invalid domain",
        "home_zone_detected": "🏠 Home zone detected",
        "is_correct": "Is this correct?",
        "yes": "✓ Yes",
        "no": "✗ No, change",
        "select_city": "Select your main city",
        "sitemap_found": "✅ Sitemap detected",
        "sitemap_robots": "✅ Sitemap in robots.txt",
        "no_sitemap": "⚠️ No sitemap (crawling fallback)",
        "domain_error": "❌ Not accessible, verify domain",
        "analyzing": "Analyzing",
        "extracting_urls": "Extracting URLs",
        "processing": "Processing",
        "gaps_found": "Gaps Detected",
        "strengths_found": "Your Strengths",
        "ties_found": "Ties",
        "low_confidence": "Low Confidence - Review",
        "zone": "Zone",
        "slug": "Suggested Slug",
        "competitors_count": "# Comps",
        "confidence": "Confidence",
        "advantage": "Advantage",
        "strategy": "Strategy",
        "priority": "Priority",
        "confirm": "Confirm",
        "required_field": "Required field",
        "duplicate_domains": "Domains must be different from each other",
        "urls_filtered": "URLs filtered by different service",
        "high_priority": "HIGH",
        "medium_priority": "MEDIUM",
        "low_priority": "LOW",
        "max_advantage": "MAXIMUM (unique zone)",
        "medium_advantage": "MEDIUM (low competition)",
        "maintain_dominance": "Maintain dominance. Reinforce content and backlinks.",
        "early_advantage": "Early advantage. Invest in differentiation.",
        "competitive_market": "Competitive market. Maintain position with quality content.",
        "validated_opportunity": "Validated Opportunity - all competitors are there",
        "emerging_niche": "Emerging Niche - majority present",
        "long_tail": "Long Tail / Experimental - only one has it",
        "filter_by_priority": "Filter by priority",
        "filter_by_competitors": "Filter by # competitors",
        "search_zone": "Search zone",
        "all": "All",
        "show_results": "Showing",
        "of": "of",
        "results": "results",
        "no_gaps_filter": "No gaps match the filters",
        "export_csv": "📥 Export CSV",
        "export_json": "📥 Export JSON",
        "export_markdown": "📥 Export Markdown",
        "copy_slugs": "📋 Copy Slugs",
    }
}

SERVICES = {
    "es": {
        "cerrajero": "Cerrajero",
        "fontanero": "Fontanero",
        "electricista": "Electricista",
        "pintor": "Pintor",
        "carpintero": "Carpintero",
        "cristalero": "Cristalero",
        "reformas": "Reformas",
        "mudanzas": "Mudanzas",
        "limpieza": "Limpieza",
        "jardinero": "Jardinero",
        "aire-acondicionado": "Aire Acondicionado",
        "albañil": "Albañil",
        "tecnico-climatizacion": "Técnico Climatización",
        "instalador-gas": "Instalador Gas",
        "tapicero": "Tapicero",
    },
    "en": {
        "locksmith": "Locksmith",
        "plumber": "Plumber",
        "electrician": "Electrician",
        "painter": "Painter",
        "carpenter": "Carpenter",
        "glazier": "Glazier",
        "remodeling": "Remodeling",
        "moving": "Moving",
        "cleaning": "Cleaning",
        "gardener": "Gardener",
        "hvac": "HVAC",
        "handyman": "Handyman",
        "roofer": "Roofer",
        "mason": "Mason",
        "pest-control": "Pest Control",
    }
}

EXCLUSION_DICTIONARY = {
    "es": {
        "cerrajero": ["fontanero", "fontaneria", "electricista", "electrico", "pintor", "pintura", "reformas", "obra", "limpieza", "mudanzas", "carpintero", "carpinteria", "cristalero", "jardinero", "jardineria", "aire", "climatizacion", "albañil", "albanileria", "gas", "tapicero"],
        "fontanero": ["cerrajero", "cerrajeria", "electricista", "electrico", "pintor", "pintura", "reformas", "obra", "limpieza", "mudanzas", "carpintero", "cristalero", "jardinero", "aire", "climatizacion", "albañil", "tapicero"],
        "electricista": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "pintor", "pintura", "reformas", "obra", "limpieza", "mudanzas", "carpintero", "cristalero", "jardinero", "aire", "climatizacion", "albañil", "tapicero"],
        "pintor": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "electricista", "electrico", "reformas", "limpieza", "mudanzas", "carpintero", "cristalero", "jardinero", "aire", "climatizacion", "albañil", "tapicero"],
        "carpintero": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "electricista", "electrico", "pintor", "pintura", "reformas", "limpieza", "mudanzas", "cristalero", "jardinero", "aire", "climatizacion", "albañil", "tapicero"],
        "cristalero": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "electricista", "electrico", "pintor", "pintura", "reformas", "limpieza", "mudanzas", "carpintero", "jardinero", "aire", "climatizacion", "albañil", "tapicero"],
        "reformas": ["cerrajero", "fontanero", "electricista", "pintor", "limpieza", "mudanzas", "cristalero", "jardinero", "aire", "tapicero"],
        "mudanzas": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "electricista", "electrico", "pintor", "pintura", "reformas", "limpieza", "carpintero", "cristalero", "jardinero", "aire", "climatizacion", "albañil", "tapicero"],
        "limpieza": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "electricista", "electrico", "pintor", "pintura", "reformas", "mudanzas", "carpintero", "cristalero", "jardinero", "aire", "climatizacion", "albañil", "tapicero"],
        "jardinero": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "electricista", "electrico", "pintor", "pintura", "reformas", "mudanzas", "carpintero", "cristalero", "limpieza", "aire", "climatizacion", "albañil", "tapicero"],
        "aire-acondicionado": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "pintor", "pintura", "reformas", "mudanzas", "carpintero", "cristalero", "limpieza", "jardinero", "albañil", "tapicero"],
        "albañil": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "electricista", "electrico", "pintor", "pintura", "mudanzas", "carpintero", "cristalero", "limpieza", "jardinero", "aire", "tapicero"],
        "tecnico-climatizacion": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "pintor", "pintura", "reformas", "mudanzas", "carpintero", "cristalero", "limpieza", "jardinero", "albañil", "tapicero"],
        "instalador-gas": ["cerrajero", "cerrajeria", "electricista", "electrico", "pintor", "pintura", "reformas", "mudanzas", "carpintero", "cristalero", "limpieza", "jardinero", "aire", "albañil", "tapicero"],
        "tapicero": ["cerrajero", "cerrajeria", "fontanero", "fontaneria", "electricista", "electrico", "reformas", "mudanzas", "cristalero", "limpieza", "jardinero", "aire", "climatizacion", "albañil"],
    },
    "en": {
        "locksmith": ["plumber", "plumbing", "electrician", "electrical", "painter", "painting", "remodeling", "renovation", "cleaning", "moving", "carpenter", "glazier", "gardener", "hvac", "handyman", "mason", "pest"],
        "plumber": ["locksmith", "locks", "electrician", "electrical", "painter", "painting", "remodeling", "renovation", "cleaning", "moving", "carpenter", "glazier", "gardener", "hvac", "handyman", "mason", "pest"],
        "electrician": ["locksmith", "locks", "plumber", "plumbing", "painter", "painting", "remodeling", "renovation", "cleaning", "moving", "carpenter", "glazier", "gardener", "hvac", "handyman", "mason", "pest"],
        "painter": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "remodeling", "cleaning", "moving", "carpenter", "glazier", "gardener", "hvac", "handyman", "mason", "pest"],
        "carpenter": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "painter", "painting", "remodeling", "cleaning", "moving", "glazier", "gardener", "hvac", "handyman", "mason", "pest"],
        "glazier": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "painter", "painting", "remodeling", "cleaning", "moving", "carpenter", "gardener", "hvac", "handyman", "mason", "pest"],
        "remodeling": ["locksmith", "plumber", "electrician", "painter", "cleaning", "moving", "glazier", "gardener", "hvac", "pest"],
        "moving": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "painter", "painting", "remodeling", "cleaning", "carpenter", "glazier", "gardener", "hvac", "handyman", "mason", "pest"],
        "cleaning": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "painter", "painting", "remodeling", "moving", "carpenter", "glazier", "gardener", "hvac", "handyman", "mason", "pest"],
        "gardener": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "painter", "painting", "remodeling", "moving", "carpenter", "glazier", "cleaning", "hvac", "handyman", "mason", "pest"],
        "hvac": ["locksmith", "locks", "plumber", "plumbing", "painter", "painting", "remodeling", "moving", "carpenter", "glazier", "cleaning", "gardener", "handyman", "mason", "pest"],
        "handyman": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "painter", "painting", "moving", "carpenter", "glazier", "cleaning", "gardener", "hvac", "mason", "pest"],
        "roofer": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "painter", "painting", "remodeling", "moving", "carpenter", "glazier", "cleaning", "gardener", "hvac", "pest"],
        "mason": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "painter", "painting", "moving", "carpenter", "glazier", "cleaning", "gardener", "hvac", "pest"],
        "pest-control": ["locksmith", "locks", "plumber", "plumbing", "electrician", "electrical", "painter", "painting", "remodeling", "moving", "carpenter", "glazier", "gardener", "hvac", "handyman", "mason"],
    }
}

TOP_CITIES = {
    "es": [
        "madrid", "barcelona", "valencia", "sevilla", "zaragoza", "malaga", 
        "murcia", "palma", "bilbao", "alicante", "cordoba", "valladolid",
        "vigo", "gijon", "hospitalet", "vitoria", "coruña", "granada", 
        "elche", "oviedo", "terrassa", "badalona", "cartagena", "sabadell",
        "jerez", "mostoles", "santa-cruz", "pamplona", "almeria", "fuenlabrada",
        "leganes", "san-sebastian", "santander", "burgos", "castellon", "albacete",
        "alcorcon", "getafe", "salamanca", "logroño", "huelva", "tarragona",
        "leon", "cadiz", "marbella", "badajoz", "lleida", "torrevieja",
        "chamberi", "retiro", "tetuan", "fuencarral", "moncloa", "carabanchel",
        "usera", "puente-vallecas", "moratalaz", "ciudad-lineal", "hortaleza",
        "villaverde", "villa-vallecas", "vicalvaro", "san-blas", "barajas",
    ],
    "en": [
        "new-york", "los-angeles", "chicago", "houston", "phoenix", "philadelphia",
        "san-antonio", "san-diego", "dallas", "san-jose", "austin", "jacksonville",
        "fort-worth", "columbus", "charlotte", "san-francisco", "indianapolis", "seattle",
        "denver", "washington", "boston", "el-paso", "nashville", "detroit",
        "oklahoma-city", "portland", "las-vegas", "memphis", "louisville", "baltimore",
        "milwaukee", "albuquerque", "tucson", "fresno", "mesa", "sacramento",
        "atlanta", "kansas-city", "colorado-springs", "omaha", "raleigh", "miami",
        "long-beach", "virginia-beach", "oakland", "minneapolis", "tulsa", "tampa",
        "brooklyn", "manhattan", "queens", "bronx", "staten-island",
    ]
}

STOP_WORDS = {
    "es": [
        "en", "a", "de", "la", "el", "los", "las", "para", "con", "por", "sin",
        "del", "al", "y", "o", "un", "una", "unos", "unas",
        "urgente", "urgentes", "barato", "baratos", "barata", "baratas",
        "economico", "economicos", "economica", "economicas",
        "mejor", "mejores", "rapido", "rapidos", "rapida", "rapidas",
        "profesional", "profesionales", "calidad", "confianza",
        "garantizado", "garantizada", "certificado", "certificada",
        "24h", "24-horas", "24horas", "24-h", "24hs",
        "servicio", "servicios", "precio", "precios", "presupuesto",
        "gratis", "gratuito", "oferta", "ofertas", "descuento",
        "cerca", "cercano", "cercana", "zona", "zonas",
    ],
    "en": [
        "in", "at", "on", "of", "the", "a", "an", "for", "with", "by", "to",
        "and", "or", "near", "around",
        "urgent", "cheap", "affordable", "economical", "economy",
        "best", "top", "fast", "quick", "rapid", "professional",
        "quality", "trusted", "certified", "guaranteed",
        "24h", "24-hour", "24-hours", "24hr", "24hrs",
        "emergency", "same-day", "sameday",
        "service", "services", "price", "prices", "quote", "free",
        "discount", "offer", "deals",
        "near", "nearby", "local", "area", "areas",
    ]
}

def get_text(key, lang="es"):
    return TRANSLATIONS.get(lang, TRANSLATIONS["es"]).get(key, key)

def get_services(lang="es"):
    return SERVICES.get(lang, SERVICES["es"])

def get_cities(lang="es"):
    return TOP_CITIES.get(lang, TOP_CITIES["es"])

def get_stop_words(lang="es"):
    return STOP_WORDS.get(lang, STOP_WORDS["es"])

def get_exclusion_list(service_key, lang="es"):
    return EXCLUSION_DICTIONARY.get(lang, {}).get(service_key, [])

def get_service_variations(service_key, lang="es"):
    variations = {service_key}
    
    if lang == "es":
        if service_key.endswith('o'):
            variations.add(service_key + 's')
        elif service_key.endswith('a'):
            variations.add(service_key + 's')
        
        if service_key.endswith('ero'):
            base = service_key[:-3]
            variations.add(base + 'eria')
            variations.add(base + 'erias')
        
        special_variations = {
            "pintor": ["pintura", "pinturas"],
            "limpieza": ["limpiezas"],
            "reformas": ["reforma"],
            "mudanzas": ["mudanza"],
            "electricista": ["electrico", "electricos", "electricidad"],
            "fontanero": ["fontaneria", "fontanerias"],
            "carpintero": ["carpinteria", "carpinterias"],
            "cristalero": ["cristaleria", "cristalerias"],
            "jardinero": ["jardineria", "jardinerias"],
            "aire-acondicionado": ["aire", "climatizacion", "clima"],
            "albañil": ["albanileria", "albaniles"],
            "tecnico-climatizacion": ["climatizacion", "clima", "aire"],
            "instalador-gas": ["gas", "instalacion-gas"],
            "tapicero": ["tapiceria", "tapicerias"],
        }
        
        if service_key in special_variations:
            variations.update(special_variations[service_key])
    
    elif lang == "en":
        variations.add(service_key + 's')
        
        special_variations = {
            "locksmith": ["locks", "locksmithing"],
            "plumber": ["plumbing"],
            "electrician": ["electrical", "electric"],
            "painter": ["painting"],
            "carpenter": ["carpentry"],
            "glazier": ["glazing", "glass"],
            "remodeling": ["renovation", "renovations", "remodel"],
            "moving": ["movers", "relocation"],
            "cleaning": ["cleaners", "clean"],
            "gardener": ["gardening", "landscaping"],
            "hvac": ["heating", "cooling", "air-conditioning"],
            "handyman": ["handymen", "repair", "repairs"],
            "roofer": ["roofing"],
            "mason": ["masonry", "bricklayer"],
            "pest-control": ["pest", "exterminator"],
        }
        
        if service_key in special_variations:
            variations.update(special_variations[service_key])
    
    return list(variations)

def normalize_domain(domain_input):
    if not domain_input:
        return None
    
    try:
        domain = domain_input.strip().lower()
        
        if domain.startswith(('http://', 'https://')):
            parsed = urlparse(domain)
            domain = parsed.netloc or parsed.path.split('/')[0]
        
        domain = domain.split('/')[0]
        
        if domain.startswith('www.'):
            domain = domain[4:]
        
        if not is_valid_domain(domain):
            return None
        
        return domain
    except:
        return None

def is_valid_domain(domain):
    pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$'
    
    if not re.match(pattern, domain):
        return False
    
    if ' ' in domain or any(c in domain for c in ['ñ', 'á', 'é', 'í', 'ó', 'ú']):
        return False
    
    if '.' not in domain:
        return False
    
    return True

def validate_domains(user_domain, comp1, comp2, comp3, lang="es"):
    domains = {
        'user': normalize_domain(user_domain),
        'comp1': normalize_domain(comp1),
        'comp2': normalize_domain(comp2),
        'comp3': normalize_domain(comp3),
    }
    
    invalid = [k for k, v in domains.items() if v is None]
    if invalid:
        error = get_text('invalid_domain', lang)
        labels = {
            'user': get_text('your_domain', lang),
            'comp1': f"{get_text('competitor', lang)} 1",
            'comp2': f"{get_text('competitor', lang)} 2",
            'comp3': f"{get_text('competitor', lang)} 3",
        }
        invalid_labels = [labels[k] for k in invalid]
        return False, {}, f"{error}: {', '.join(invalid_labels)}"
    
    domain_list = list(domains.values())
    if len(domain_list) != len(set(domain_list)):
        return False, {}, f"❌ {get_text('duplicate_domains', lang)}"
    
    return True, domains, ""

def find_sitemap(domain, timeout=15):
    base_url = f"https://{domain}"
    
    sitemap_paths = [
        '/sitemap_index.xml',
        '/sitemap.xml',
        '/sitemap-index.xml',
        '/wp-sitemap.xml',
        '/post-sitemap.xml',
        '/page-sitemap.xml',
        '/sitemap.php',
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (LocalSEOGapAnalyzer/2.3; +https://github.com/user/local-seo-gap)'
    }
    
    for path in sitemap_paths:
        try:
            url = urljoin(base_url, path)
            
            try:
                response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'xml' in content_type or path.endswith('.xml'):
                        return {
                            'sitemap_url': url,
                            'method': 'direct',
                            'success': True,
                            'message': f"✅ {path}"
                        }
            except:
                try:
                    response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
                    
                    if response.status_code == 200:
                        content_start = next(response.iter_content(200), b'').decode('utf-8', errors='ignore')
                        
                        if '<?xml' in content_start or '<urlset' in content_start or '<sitemapindex' in content_start:
                            return {
                                'sitemap_url': url,
                                'method': 'direct',
                                'success': True,
                                'message': f"✅ {path}"
                            }
                except:
                    pass
        except Exception as e:
            continue
    
    try:
        robots_url = urljoin(base_url, '/robots.txt')
        response = requests.get(robots_url, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            for line in response.text.split('\n'):
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    
                    try:
                        check = requests.head(sitemap_url, headers=headers, timeout=timeout, allow_redirects=True)
                        if check.status_code == 200:
                            return {
                                'sitemap_url': sitemap_url,
                                'method': 'robots',
                                'success': True,
                                'message': "✅ robots.txt"
                            }
                    except:
                        try:
                            check = requests.get(sitemap_url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
                            if check.status_code == 200:
                                return {
                                    'sitemap_url': sitemap_url,
                                    'method': 'robots',
                                    'success': True,
                                    'message': "✅ robots.txt"
                                }
                        except:
                            continue
    except:
        pass
    
    return {
        'sitemap_url': None,
        'method': 'none',
        'success': False,
        'message': "⚠️ Sin sitemap"
    }

def find_all_sitemaps(domains_dict):
    results = {}
    for key, domain in domains_dict.items():
        if domain:
            results[key] = find_sitemap(domain)
    return results

def detect_home_zone_from_domain(domain, service_key, lang="es"):
    domain_lower = domain.lower()
    cities = get_cities(lang)
    
    subdomain_match = re.match(r'^([a-z-]+)\.', domain_lower)
    if subdomain_match:
        potential_zone = subdomain_match.group(1)
        if potential_zone in cities:
            return potential_zone
    
    service_variations = get_service_variations(service_key, lang)
    
    for city in cities:
        for service_var in service_variations:
            patterns = [
                f"{service_var}{city}",
                f"{city}{service_var}",
                f"{service_var}-{city}",
                f"{city}-{service_var}",
            ]
            
            for pattern in patterns:
                if pattern in domain_lower:
                    return city
    
    return None

def detect_home_zone_from_homepage(domain, lang="es", timeout=10):
    try:
        url = f"https://{domain}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (LocalSEOGapAnalyzer/2.3)'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        
        if len(response.text) < 500:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        cities = get_cities(lang)
        
        title = soup.find('title')
        if title:
            title_text = unidecode(title.get_text().lower())
            for city in cities:
                if city in title_text:
                    return city
        
        h1 = soup.find('h1')
        if h1:
            h1_text = unidecode(h1.get_text().lower())
            for city in cities:
                if city in h1_text:
                    return city
        
        return None
    except:
        return None

def detect_home_zone(domain, service_key, lang="es"):
    zone_from_domain = detect_home_zone_from_domain(domain, service_key, lang)
    if zone_from_domain:
        return {
            'zone': zone_from_domain,
            'method': 'domain',
            'confidence': 90
        }
    
    zone_from_homepage = detect_home_zone_from_homepage(domain, lang)
    if zone_from_homepage:
        return {
            'zone': zone_from_homepage,
            'method': 'homepage',
            'confidence': 70
        }
    
    return {
        'zone': None,
        'method': 'manual',
        'confidence': 0
    }

def clean_slug(slug, stop_words, lang="es"):
    slug = slug.strip('/')
    slug = unidecode(slug)
    slug = slug.lower()
    
    parts = slug.split('-')
    cleaned_parts = [p for p in parts if p not in stop_words and p.strip()]
    
    cleaned = '-'.join(cleaned_parts)
    
    while '--' in cleaned:
        cleaned = cleaned.replace('--', '-')
    
    return cleaned.strip('-')

def normalize_multi_word_zones(slug, lang="es"):
    connectors = {
        "es": ["el", "la", "los", "las", "de"],
        "en": ["the", "of"]
    }
    
    parts = slug.split('-')
    cleaned_parts = [p for p in parts if p not in connectors.get(lang, [])]
    
    return '-'.join(cleaned_parts)

def is_url_valid_for_service(url, service_key, lang="es", threshold=80):
    exclusion_list = get_exclusion_list(service_key, lang)
    service_variations = get_service_variations(service_key, lang)
    
    url_lower = url.lower()
    
    has_service = any(
        var in url_lower or fuzz.partial_ratio(var, url_lower) > threshold
        for var in service_variations
    )
    
    if not has_service:
        return False
    
    for excluded_service in exclusion_list:
        if fuzz.partial_ratio(excluded_service, url_lower) > threshold:
            return False
    
    return True

def calculate_confidence(zone, cities, url, lang="es"):
    validations = {
        'regex': False,
        'top_cities': False,
    }
    
    if zone and len(zone) > 2:
        validations['regex'] = True
    
    if zone in cities:
        validations['top_cities'] = True
    
    passed = sum(validations.values())
    total = len(validations)
    score = int((passed / total) * 100)
    
    return {
        'score': score,
        'validations': validations
    }

def detect_url_pattern(url, zone, service):
    path = urlparse(url).path.strip('/').lower()
    
    zone_norm = zone.lower()
    service_norm = service.lower()
    
    if path == zone_norm:
        return 'zone_only'
    
    if path == f"{service_norm}-{zone_norm}":
        return 'service_zone'
    
    if path == f"{zone_norm}/{service_norm}":
        return 'zone_service'
    
    if path == f"{zone_norm}-{service_norm}":
        return 'zone_service_dash'
    
    return 'other'

def suggest_best_slug(gap_zone, service_key, comp_zones_data_list, lang="es"):
    competitor_urls = []
    
    for comp_data in comp_zones_data_list:
        for zone, conf, url in comp_data:
            if zone == gap_zone:
                competitor_urls.append(url)
    
    if not competitor_urls:
        return {
            'slug': f"/{service_key}-{gap_zone}/",
            'pattern': 'service_zone',
            'confidence': None
        }
    
    patterns = {}
    for url in competitor_urls:
        pattern = detect_url_pattern(url, gap_zone, service_key)
        patterns[pattern] = patterns.get(pattern, 0) + 1
    
    most_common_pattern = max(patterns, key=patterns.get)
    count = patterns[most_common_pattern]
    total = len(competitor_urls)
    
    if most_common_pattern == 'zone_only':
        slug = f"/{gap_zone}/"
    elif most_common_pattern == 'service_zone':
        slug = f"/{service_key}-{gap_zone}/"
    elif most_common_pattern == 'zone_service':
        slug = f"/{gap_zone}/{service_key}/"
    elif most_common_pattern == 'zone_service_dash':
        slug = f"/{gap_zone}-{service_key}/"
    else:
        slug = f"/{service_key}-{gap_zone}/"
    
    return {
        'slug': slug,
        'pattern': most_common_pattern,
        'confidence': f"{count}/{total}"
    }

def extract_urls_from_sitemap(sitemap_url, max_urls=5000):
    try:
        df = adv.sitemap_to_df(sitemap_url)
        urls = df['loc'].tolist()
        
        if len(urls) > max_urls:
            import random
            urls = random.sample(urls, max_urls)
        
        return urls, len(df)
    except Exception as e:
        return [], 0

def filter_urls(urls, lang="es"):
    discard_patterns = [
        '/blog/', '/tag/', '/tags/', '/category/', '/categories/',
        '/author/', '/page/', '/search/',
        '/wp-content/', '/wp-admin/', '/wp-includes/',
        '/feed/', '/rss/', '/sitemap/',
    ]
    
    extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.css', '.js', '.pdf']
    
    filtered = []
    for url in urls:
        if any(pattern in url.lower() for pattern in discard_patterns):
            continue
        
        if any(url.lower().endswith(ext) for ext in extensions):
            continue
        
        if '?' in url:
            continue
        
        path = urlparse(url).path
        depth = len([p for p in path.split('/') if p])
        if depth > 3:
            continue
        
        filtered.append(url)
    
    return filtered

def extract_zone_from_url(url, cities, service_key, stop_words, lang="es"):
    try:
        if not is_url_valid_for_service(url, service_key, lang):
            return None, None
        
        path = urlparse(url).path
        slug = path.strip('/').split('/')[-1]
        
        if not slug:
            return None, None
        
        cleaned = clean_slug(slug, stop_words, lang)
        cleaned = normalize_multi_word_zones(cleaned, lang)
        
        for city in cities:
            if city in cleaned:
                confidence = calculate_confidence(city, cities, url, lang)
                return city, confidence
        
        return None, None
    except:
        return None, None

def analyze_comprehensive(user_zones_data, comp_zones_data_list, home_zone):
    user_zones = set([z for z, _, _ in user_zones_data if z])
    user_zones.discard(home_zone)
    
    all_comp_zones = set()
    comp_zones_lists = []
    
    for comp_data in comp_zones_data_list:
        comp_zones = set([z for z, _, _ in comp_data if z])
        comp_zones.discard(home_zone)
        comp_zones_lists.append(comp_zones)
        all_comp_zones.update(comp_zones)
    
    gaps = all_comp_zones - user_zones
    
    strengths = {
        'tier_1': [],
        'tier_2': []
    }
    
    for zone in user_zones:
        comp_count = sum([1 for comp_zones in comp_zones_lists if zone in comp_zones])
        
        if comp_count == 0:
            strengths['tier_1'].append(zone)
        elif comp_count == 1:
            strengths['tier_2'].append(zone)
    
    ties = []
    for zone in user_zones:
        comp_count = sum([1 for comp_zones in comp_zones_lists if zone in comp_zones])
        if comp_count >= 2:
            ties.append(zone)
    
    return {
        'gaps': list(gaps),
        'strengths': strengths,
        'ties': ties
    }

# ============================================
# FUNCIONES DE EXPORTACIÓN
# ============================================

def export_to_csv(gaps_data, lang="es"):
    """Genera CSV con datos de gaps"""
    import io
    
    output = io.StringIO()
    df = pd.DataFrame(gaps_data)
    df.to_csv(output, index=False, encoding='utf-8-sig')
    
    return output.getvalue()

def export_to_json(gaps_data):
    """Genera JSON estructurado"""
    import json
    return json.dumps(gaps_data, indent=2, ensure_ascii=False)

def export_to_markdown(gaps_data, lang="es"):
    """Genera checklist Markdown para Notion/Obsidian"""
    lines = ["# SEO Gaps - Checklist\n"]
    
    for gap in gaps_data:
        priority_icon = {
            "ALTA": "🔴",
            "MEDIA": "🟡",
            "BAJA": "🟢",
            "HIGH": "🔴",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }
        
        priority_key = get_text('priority', lang)
        zone_key = get_text('zone', lang)
        slug_key = get_text('slug', lang)
        comps_key = get_text('competitors_count', lang)
        
        priority_raw = gap.get(priority_key, "")
        priority = priority_raw.split()[-1] if priority_raw else ""
        icon = priority_icon.get(priority, "⚪")
        
        zone = gap.get(zone_key, "")
        slug = gap.get(slug_key, "")
        comps = gap.get(comps_key, 0)
        
        line = f"- [ ] {icon} {priority} | Crear página: `{slug}` | Zona: {zone} | {comps} competidores\n"
        lines.append(line)
    
    return "".join(lines)

# ============================================
# STREAMLIT UI
# ============================================

st.set_page_config(
    page_title="Local SEO Geo-Gap Analyzer",
    page_icon="🎯",
    layout="wide"
)

if 'lang' not in st.session_state:
    st.session_state.lang = 'es'

if 'home_zone_confirmed' not in st.session_state:
    st.session_state.home_zone_confirmed = False

if 'show_city_selector' not in st.session_state:
    st.session_state.show_city_selector = False

st.title(get_text('title', st.session_state.lang))

with st.sidebar:
    st.subheader(get_text('language', st.session_state.lang))
    lang_option = st.radio(
        "Language selector",
        options=['🇪🇸 Español', '🇬🇧 English'],
        index=0 if st.session_state.lang == 'es' else 1,
        label_visibility='collapsed'
    )
    
    new_lang = 'es' if '🇪🇸' in lang_option else 'en'
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.session_state.home_zone_confirmed = False
        st.rerun()

lang = st.session_state.lang

st.header("⚙️ " + ("Configuración" if lang == "es" else "Configuration"))

services_dict = get_services(lang)
service_label = get_text('service', lang)
selected_service_display = st.selectbox(
    service_label,
    options=list(services_dict.values()),
    index=0
)
selected_service = [k for k, v in services_dict.items() if v == selected_service_display][0]

st.divider()

col1, col2 = st.columns(2)

with col1:
    user_domain_input = st.text_input(
        f"🏠 {get_text('your_domain', lang)} *",
        placeholder=get_text('domain_placeholder', lang),
        help="Solo el dominio, sin https:// ni rutas"
    )
    
    user_sitemap_input = st.text_input(
        f"📄 Sitemap URL (opcional)",
        placeholder="https://tudominio.com/sitemap.xml",
        help="Si tu sitemap no se detecta automáticamente, pégalo aquí"
    )

with col2:
    if user_domain_input:
        normalized = normalize_domain(user_domain_input)
        if normalized:
            st.success(f"✅ {normalized}")
        else:
            st.error(get_text('invalid_domain', lang))

st.divider()

st.subheader(f"🔍 {get_text('competitor', lang)}s")

col1, col2 = st.columns(2)
with col1:
    comp1_input = st.text_input(
        f"{get_text('competitor', lang)} 1 *",
        placeholder=get_text('domain_placeholder', lang)
    )
    comp2_input = st.text_input(
        f"{get_text('competitor', lang)} 2 *",
        placeholder=get_text('domain_placeholder', lang)
    )

with col2:
    comp3_input = st.text_input(
        f"{get_text('competitor', lang)} 3 *",
        placeholder=get_text('domain_placeholder', lang)
    )
    
    valid_comps = sum([
        bool(normalize_domain(comp1_input)),
        bool(normalize_domain(comp2_input)),
        bool(normalize_domain(comp3_input))
    ])
    
    if valid_comps < 3:
        st.warning(f"⚠️ {valid_comps}/3 " + ("competidores válidos" if lang == "es" else "valid competitors"))
    else:
        st.success(f"✅ {valid_comps}/3 " + ("competidores válidos" if lang == "es" else "valid competitors"))

st.divider()

analyze_button = st.button(
    get_text('analyze_button', lang),
    type="primary",
    use_container_width=True,
    disabled=not all([user_domain_input, comp1_input, comp2_input, comp3_input])
)

if analyze_button:
    success, normalized_domains, error_msg = validate_domains(
        user_domain_input, comp1_input, comp2_input, comp3_input, lang
    )
    
    if not success:
        st.error(error_msg)
        st.stop()
    
    st.subheader("🔍 " + get_text('extracting_urls', lang))
    
    if user_sitemap_input and user_sitemap_input.strip():
        sitemap_results = {
            'user': {
                'sitemap_url': user_sitemap_input.strip(),
                'method': 'manual',
                'success': True,
                'message': '✅ Manual'
            }
        }
        
        with st.spinner(''):
            comp_sitemaps = find_all_sitemaps({
                'comp1': normalized_domains['comp1'],
                'comp2': normalized_domains['comp2'],
                'comp3': normalized_domains['comp3']
            })
        
        sitemap_results.update(comp_sitemaps)
    else:
        with st.spinner(''):
            sitemap_results = find_all_sitemaps(normalized_domains)
    
    for key in ['user', 'comp1', 'comp2', 'comp3']:
        result = sitemap_results[key]
        domain = normalized_domains[key]
        
        if key == 'user':
            label = get_text('your_domain', lang)
        else:
            label = f"{get_text('competitor', lang)} {key[-1]}"
        
        if result['success']:
            st.success(f"{label}: **{domain}** → {result['message']}")
        else:
            st.warning(f"{label}: **{domain}** → {result['message']}")
    
    st.divider()
    
    if 'home_zone' not in st.session_state:
        st.subheader("🏠 " + get_text('home_zone_detected', lang))
        
        with st.spinner(''):
            home_zone_result = detect_home_zone(
                normalized_domains['user'],
                selected_service,
                lang
            )
        
        if home_zone_result['zone']:
            st.session_state.home_zone = home_zone_result['zone']
            st.success(f"✅ {get_text('home_zone_detected', lang)}: **{home_zone_result['zone'].title()}** (auto-detectada)")
        else:
            cities = get_cities(lang)
            manual_zone = st.selectbox(
                get_text('select_city', lang),
                options=cities,
                index=0
            )
            st.session_state.home_zone = manual_zone
            st.info(f"ℹ️ Zona seleccionada manualmente: **{manual_zone.title()}**")
    else:
        st.success(f"✅ " + get_text('home_zone_detected', lang) + f": **{st.session_state.home_zone.title()}**")
    
    st.subheader("📊 " + get_text('processing', lang))
    
    all_urls = {}
    all_counts = {}
    filtered_counts = {}
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    timer_placeholder = st.empty()
    start_time = time.time()
    
    for idx, key in enumerate(['user', 'comp1', 'comp2', 'comp3']):
        domain = normalized_domains[key]
        sitemap_result = sitemap_results[key]
        
        elapsed = int(time.time() - start_time)
        timer_placeholder.caption(f"⏱️ Tiempo transcurrido: {elapsed}s")
        
        status_text.text(f"{get_text('processing', lang)}: {domain}")
        
        if sitemap_result['success']:
            urls, total = extract_urls_from_sitemap(sitemap_result['sitemap_url'])
            all_urls[key] = urls
            all_counts[key] = {'extracted': len(urls), 'total': total}
        else:
            all_urls[key] = []
            all_counts[key] = {'extracted': 0, 'total': 0}
        
        progress_bar.progress((idx + 1) / 4)
    
    status_text.empty()
    progress_bar.empty()
    timer_placeholder.empty()
    
    cities = get_cities(lang)
    stop_words = get_stop_words(lang)
    
    timer_placeholder = st.empty()
    start_time = time.time()
    
    all_zones_data = {}
    for key, urls in all_urls.items():
        elapsed = int(time.time() - start_time)
        timer_placeholder.caption(f"⏱️ {get_text('processing', lang)}: {elapsed}s")
        
        filtered = filter_urls(urls, lang)
        zones_data = []
        filtered_by_service = 0
        
        for url in filtered:
            zone, confidence = extract_zone_from_url(url, cities, selected_service, stop_words, lang)
            if zone:
                zones_data.append((zone, confidence, url))
            elif not is_url_valid_for_service(url, selected_service, lang):
                filtered_by_service += 1
        
        all_zones_data[key] = zones_data
        filtered_counts[key] = filtered_by_service
    
    timer_placeholder.empty()
    
    analysis = analyze_comprehensive(
        all_zones_data['user'],
        [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']],
        st.session_state.home_zone
    )
    
    st.divider()
    
    st.subheader("📊 " + ("Resumen del Análisis" if lang == "es" else "Analysis Summary"))
    
    high_priority = sum([1 for gap in analysis['gaps'] if sum([1 for comp_data in [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']] if any(z == gap for z, _, _ in comp_data)]) == 3])
    
    medium_priority = sum([1 for gap in analysis['gaps'] if sum([1 for comp_data in [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']] if any(z == gap for z, _, _ in comp_data)]) == 2])
    
    low_priority = sum([1 for gap in analysis['gaps'] if sum([1 for comp_data in [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']] if any(z == gap for z, _, _ in comp_data)]) == 1])
    
    low_conf_count = 0
    for gap in analysis['gaps']:
        confidences = []
        for comp_data in [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']]:
            for z, conf, _ in comp_data:
                if z == gap and conf:
                    confidences.append(conf['score'])
        avg_conf = int(sum(confidences) / len(confidences)) if confidences else 0
        if avg_conf < 67:
            low_conf_count += 1
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🎯 " + ("Total Gaps" if lang == "en" else "Total Gaps"),
            value=len(analysis['gaps']),
            delta=None
        )
    
    with col2:
        st.metric(
            label="💪 " + get_text('strengths_found', lang),
            value=len(analysis['strengths']['tier_1']) + len(analysis['strengths']['tier_2']),
            delta=None
        )
    
    with col3:
        st.metric(
            label="🏠 " + get_text('home_zone_detected', lang),
            value=st.session_state.home_zone.title(),
            delta=None
        )
    
    with col4:
        st.metric(
            label="⚖️ " + get_text('ties_found', lang),
            value=len(analysis['ties']),
            delta=None
        )
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🔴 " + get_text('high_priority', lang),
            value=f"{high_priority} gaps",
            delta=None,
            help=get_text('validated_opportunity', lang)
        )
    
    with col2:
        st.metric(
            label="🟡 " + get_text('medium_priority', lang),
            value=f"{medium_priority} gaps",
            delta=None,
            help=get_text('emerging_niche', lang)
        )
    
    with col3:
        st.metric(
            label="🟢 " + get_text('low_priority', lang),
            value=f"{low_priority} gaps",
            delta=None,
            help=get_text('long_tail', lang)
        )
    
    with col4:
        st.metric(
            label="⚠️ " + ("Revisar" if lang == "es" else "Review"),
            value=f"{low_conf_count} gaps",
            delta=None,
            help="Confidence <67%"
        )
    
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs([
        f"🎯 {get_text('gaps_found', lang)} ({len(analysis['gaps'])})",
        f"💪 {get_text('strengths_found', lang)} ({len(analysis['strengths']['tier_1']) + len(analysis['strengths']['tier_2'])})",
        f"⚖️ {get_text('ties_found', lang)} ({len(analysis['ties'])})",
        f"⚠️ {get_text('low_confidence', lang)}"
    ])
    
    with tab1:
        st.subheader(get_text('gaps_found', lang))
        
        if analysis['gaps']:
            # ============================================
            # FILTROS INTERACTIVOS (SPRINT 3.1)
            # ============================================
            
            col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
            
            with col_f1:
                all_text = get_text('all', lang)
                priority_options = [
                    all_text,
                    get_text('high_priority', lang),
                    get_text('medium_priority', lang),
                    get_text('low_priority', lang)
                ]
                selected_priority = st.selectbox(
                    get_text('filter_by_priority', lang),
                    options=priority_options,
                    index=0
                )
            
            with col_f2:
                comp_options = [all_text, "3", "2", "1"]
                selected_comps = st.selectbox(
                    get_text('filter_by_competitors', lang),
                    options=comp_options,
                    index=0
                )
            
            with col_f3:
                search_query = st.text_input(
                    get_text('search_zone', lang),
                    placeholder="Madrid, Barcelona, Chamberí..."
                )
            
            st.divider()
            
            # ============================================
            # CONSTRUCCIÓN DE GAPS DATA
            # ============================================
            
            gaps_data = []
            
            for gap in sorted(analysis['gaps']):
                comp_count = sum([
                    1 for comp_data in [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']]
                    if any(z == gap for z, _, _ in comp_data)
                ])
                
                confidences = []
                for comp_data in [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']]:
                    for z, conf, _ in comp_data:
                        if z == gap and conf:
                            confidences.append(conf['score'])
                
                avg_conf = int(sum(confidences) / len(confidences)) if confidences else 0
                
                if comp_count == 3:
                    priority = get_text('high_priority', lang)
                    color = "🔴"
                elif comp_count == 2:
                    priority = get_text('medium_priority', lang)
                    color = "🟡"
                else:
                    priority = get_text('low_priority', lang)
                    color = "🟢"
                
                slug_suggestion = suggest_best_slug(
                    gap, 
                    selected_service, 
                    [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']],
                    lang
                )
                
                if avg_conf >= 67:
                    gap_row = {
                        get_text('priority', lang): f"{color} {priority}",
                        get_text('zone', lang): gap.title(),
                        get_text('slug', lang): slug_suggestion['slug'],
                        get_text('competitors_count', lang): comp_count,
                        get_text('confidence', lang): f"{avg_conf}%",
                        '_priority_raw': priority,
                        '_comp_count_raw': comp_count,
                        '_zone_raw': gap.lower()
                    }
                    
                    if slug_suggestion['confidence']:
                        if lang == "es":
                            gap_row['Patrón'] = f"{slug_suggestion['confidence']} usan {slug_suggestion['pattern']}"
                        else:
                            gap_row['Pattern'] = f"{slug_suggestion['confidence']} use {slug_suggestion['pattern']}"
                    
                    gaps_data.append(gap_row)
            
            # ============================================
            # APLICAR FILTROS
            # ============================================
            
            filtered_gaps = gaps_data.copy()
            
            # Filtro por prioridad
            if selected_priority != all_text:
                filtered_gaps = [g for g in filtered_gaps if g['_priority_raw'] == selected_priority]
            
            # Filtro por N° competidores
            if selected_comps != all_text:
                filtered_gaps = [g for g in filtered_gaps if g['_comp_count_raw'] == int(selected_comps)]
            
            # Filtro por búsqueda
            if search_query:
                search_lower = unidecode(search_query.lower())
                filtered_gaps = [g for g in filtered_gaps if search_lower in g['_zone_raw']]
            
            # ============================================
            # MOSTRAR RESULTADOS
            # ============================================
            
            if filtered_gaps:
                # Remover campos auxiliares
                display_gaps = []
                for gap in filtered_gaps:
                    display_gap = {k: v for k, v in gap.items() if not k.startswith('_')}
                    display_gaps.append(display_gap)
                
                st.caption(f"{get_text('show_results', lang)}: **{len(display_gaps)}** {get_text('of', lang)} **{len(gaps_data)}** {get_text('results', lang)}")
                
                df_gaps = pd.DataFrame(display_gaps)
                st.dataframe(df_gaps, use_container_width=True, hide_index=True)
                
                # ============================================
                # BOTONES DE EXPORTACIÓN
                # ============================================
                
                st.divider()
                
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                
                with col_e1:
                    all_slugs = '\n'.join([row[get_text('slug', lang)] for row in display_gaps])
                    st.download_button(
                        get_text('copy_slugs', lang),
                        data=all_slugs,
                        file_name="gaps_slugs.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col_e2:
                    csv_data = export_to_csv(display_gaps, lang)
                    st.download_button(
                        get_text('export_csv', lang),
                        data=csv_data,
                        file_name="gaps_analysis.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_e3:
                    json_data = export_to_json(display_gaps)
                    st.download_button(
                        get_text('export_json', lang),
                        data=json_data,
                        file_name="gaps_analysis.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col_e4:
                    md_data = export_to_markdown(display_gaps, lang)
                    st.download_button(
                        get_text('export_markdown', lang),
                        data=md_data,
                        file_name="gaps_checklist.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
            else:
                st.info(f"ℹ️ {get_text('no_gaps_filter', lang)}")
        else:
            st.success("🎉 " + ("¡Ya cubres todas las zonas de tus competidores!" if lang == "es" else "You already cover all competitor zones!"))
    
    with tab2:
        st.subheader(get_text('strengths_found', lang))
        
        strengths_data = []
        
        for zone in analysis['strengths']['tier_1']:
            strengths_data.append({
                get_text('zone', lang): zone.title(),
                get_text('advantage', lang): get_text('max_advantage', lang),
                get_text('competitors_count', lang): 0,
                get_text('strategy', lang): get_text('maintain_dominance', lang)
            })
        
        for zone in analysis['strengths']['tier_2']:
            strengths_data.append({
                get_text('zone', lang): zone.title(),
                get_text('advantage', lang): get_text('medium_advantage', lang),
                get_text('competitors_count', lang): 1,
                get_text('strategy', lang): get_text('early_advantage', lang)
            })
        
        if strengths_data:
            df_strengths = pd.DataFrame(strengths_data)
            st.dataframe(df_strengths, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ " + ("No se detectaron fortalezas únicas" if lang == "es" else "No unique strengths detected"))
    
    with tab3:
        st.subheader(get_text('ties_found', lang))
        
        if analysis['ties']:
            ties_data = []
            
            for zone in sorted(analysis['ties']):
                comp_count = sum([
                    1 for comp_data in [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']]
                    if any(z == zone for z, _, _ in comp_data)
                ])
                
                ties_data.append({
                    get_text('zone', lang): zone.title(),
                    get_text('competitors_count', lang): comp_count,
                    get_text('strategy', lang): get_text('competitive_market', lang)
                })
            
            df_ties = pd.DataFrame(ties_data)
            st.dataframe(df_ties, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ " + ("No hay mercados saturados" if lang == "es" else "No saturated markets"))
    
    with tab4:
        st.subheader(get_text('low_confidence', lang))
        
        low_conf_gaps = []
        
        for gap in analysis['gaps']:
            confidences = []
            for comp_data in [all_zones_data['comp1'], all_zones_data['comp2'], all_zones_data['comp3']]:
                for z, conf, _ in comp_data:
                    if z == gap and conf:
                        confidences.append(conf['score'])
            
            avg_conf = int(sum(confidences) / len(confidences)) if confidences else 0
            
            if avg_conf < 67:
                low_conf_gaps.append({
                    get_text('zone', lang): gap.title(),
                    get_text('confidence', lang): f"{avg_conf}%",
                    get_text('slug', lang): f"/{selected_service}-{gap}/"
                })
        
        if low_conf_gaps:
            st.warning("⚠️ " + ("Estas zonas requieren verificación manual antes de crear contenido" if lang == "es" else "These zones require manual verification before creating content"))
            df_low = pd.DataFrame(low_conf_gaps)
            st.dataframe(df_low, use_container_width=True, hide_index=True)
        else:
            st.success("✅ " + ("Todos los gaps tienen alta confianza" if lang == "es" else "All gaps have high confidence"))
