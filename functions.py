import unicodedata
import re
import httpx
from dotenv import load_dotenv
import time
from urllib.parse import urlparse,urlunparse
import http.client
import json
import trafilatura

load_dotenv()

STOP_CONJ = {
    "și","sau","ori","fie","nici","dar","iar","însă","ci","ba","decât",
    "decât","deci","căci","deoarece","fiindcă","întrucât","dacă","deși",
    "precum","precum și","astfel încât","ca să","respectiv","care"
}
STOP_CONJ |= {"si","insa","intrucat","desi","precum","astfel","respectiv","ca","caci","decat"}

STOP_PREP = {
    "de","din","la","pe","cu","fără","pentru","prin","către","spre","după",
    "înainte de","până","până la","între","dintre","sub","peste","asupra",
    "împotriva","lângă","printre","potrivit","conform","despre","într"
}
STOP_PREP |= {"fara","pana","inainte","impotriva","langa"}

# Articole / determinanți / demonstrative
STOP_ART_DET = {
    "un","o","niște","al","a","ai","ale",
    "cel","cea","cei","cele",
    "acel","aceea","acei","acele",
    "acest","această","acești","aceste",
    "ăsta","asta","ăștia","astea","ăla","aia","ăia","alea","asta","asta-i"
}
STOP_ART_DET |= {"niste","aceasta","aceste","asta","astia","alea","ala","aia","astia"}

# PRONUME (inclusiv forme clitice frecvente)
STOP_PRON = {
    "eu","tu","el","ea","noi","voi","ei","ele",
    "mine","tine","dânsul","dânsa","dânșii","dânsele",
    "meu","mea","mei","mele","tău","ta","tăi","tale",
    "său","sa","săi","sale","nostru","noastră","noștri","noastre",
    "vostru","voastră","voștri","voastre",
    # clitice/forme scurte
    "mă","ma","mi","m","m-ai","m-a","m-am",
    "te","ți","ti","t","t-ai","t-a","t-am",
    "îl","il","l","l-a","l-am","l-ai",
    "o","i","îi","ii","le","li","ne","vă","va",
    "și-și","și-l","și-i","și-o","si-si","si-l","si-i","si-o"
}

# Verbe auxiliare / foarte comune (nu informative)
STOP_VERBS = {
    "sunt","e","este","eşti","esti","suntem","sunteţi","sunteti",
    "era","erau","fost","fiind","fi","am","ai","are","avem","aveţi","aveti","au",
    "avea","avut","trebuie","pot","poate","putem","puteţi","puteti","pot",
    "fie","pare","par","dă","da","dau","dădea","dadea","spune","spun","zice","zic"
}

# Adverbe / particule uzuale
STOP_ADV = {
    "mai","doar","foarte","încă","inca","tot","totuși","totusi","chiar","aproape","abia",
    "mereu","niciodată","niciodata","întotdeauna","intotdeauna","aici","acolo",
    "astfel","altfel","deja","iarăși","iarasi","numai","cam","destul",
    "acum","atunci","când","cand","unde","cum","cât","cat","deci"
}

# Timp / zile / luni (adesea zgomot)
STOP_TIME = {
    "azi","ieri","mâine","maine","acum","recent","astăzi","astazi",
    "luni","marți","marti","miercuri","joi","vineri","sâmbătă","sambata","duminică","duminica",
    "ianuarie","februarie","martie","aprilie","mai","iunie","iulie","august",
    "septembrie","octombrie","noiembrie","decembrie","anul","luna","ziua"
}

# Numerale în cuvinte (păstrezi dacă nu vrei să numeri cifrele)
STOP_NUM_WORDS = {
    "zero","unu","una","doi","două","trei","patru","cinci","șase","sase",
    "șapte","sapte","opt","nouă","noua","zece","unsprezece","doisprezece",
    "zeci","sută","suta","mie","mii","milion","milioane","miliard","miliarde"
}

# Boilerplate media/web
STOP_WEB = {
    "video","foto","galerie","articol","știre","știri","stire","stiri",
    "update","exclusiv","live","breaking","sursa","redacția","redactia",
    "autor","comentarii","cookie","cookies","gdpr","newsletter","abonare",
    "accept","politica","termeni","confidențialitate","confidentialitate",
    "previzualizare","click","citește","citeste","continuare","urmărește","urmareste"
}

# Variante fără diacritice pentru cele mai frecvente stopwords
STOP_NO_DIA = {
    "si","in","pe","la","cu","din","de","ca","este","sunt","un","o",
    "pentru","prin","catre","al","a","ai","ale","acest","aceasta","aceste",
    "acel","aceea","acelasi","aceiasi","iti","ti","lui","ei","ele","voi","noi",
}

# Unificare
STOPWORDS_RO = set().union(
    STOP_CONJ, STOP_PREP, STOP_ART_DET, STOP_PRON,
    STOP_VERBS, STOP_ADV, STOP_TIME, STOP_NUM_WORDS,
    STOP_WEB, STOP_NO_DIA
)

RE_URL=re.compile(r"https?://\S+|www\.\S+",flags=re.IGNORECASE)
RE_EMAIL=re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", flags=re.IGNORECASE)
RE_TAGS=re.compile(r"<[^>]+>")
RE_JS=re.compile(r"\b(function|var|let|const)\b.*?;", flags=re.IGNORECASE | re.DOTALL)
RE_NUM=re.compile(r"\b\d+(?:[\.,]\d+)?\b")
RE_MULTI=re.compile(r"\s+")
RE_TOKEN = re.compile(r"[a-zăâîșț]+", flags=re.IGNORECASE)
def get_serper_page(query: str, page: int, api_key: str) -> list[str]:
    links = []
    request_dict= {
    "q": query,
    "results_num": 5, #->Rezultate pe o singura pagina
    "page": page,
    "gl": "ro",
    "hl": "ro"

    } #->Informatie sub forma de dictionar PYTHON
    request_body = json.dumps(request_dict).encode("utf-8") #string -> bytes, asa vrea http.client
    print(request_body)
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    backoff_base=0.8
    status=None
    last_error=None
    response_body=None
    for attempt in range(1,4):
        try:
            conn = http.client.HTTPSConnection("google.serper.dev", timeout=10)
            conn.request("POST", "/search", request_body, headers)
            res = conn.getresponse()
            status=res.status
            raw = res.read().decode()
            response = json.loads(raw)
            response_body=raw

            if status == 200:
                break

            elif 500<= status < 600:
                sleep_s=backoff_base*(2**(attempt-1))
                time.sleep(sleep_s)
                continue
            elif status == 429:
                sleep_s=backoff_base*(2**(attempt))
                time.sleep(sleep_s)
            raise RuntimeError(f"HTTP {status} - {response_body[:200]}")

        except OSError as e:
            last_error=e
            sleep_s=backoff_base * (2**(attempt-1))
            time.sleep(sleep_s)
        finally:
            try:
                conn.close()
            except Exception:
                pass


        print(f"Error, trying again..{attempt}")

    if status != 200:
        if last_error:
            raise RuntimeError(f"Request failed after 3 tries due to error: {last_error}")
    else:
        #Despachetare raspuns



        #In raspuns, linkurile sunt in lista organic
        organic = response.get("organic",[])
        for item in organic:
            link = item.get("link")
            if not link:
                continue
            link_curat = clean_url(link)
            if link_curat and not link_curat.lower().endswith(".pdf"):
                links.append(link_curat)
    return links

def validate_api_key(api_key):
    if not api_key:
        raise ValueError("SERPER_API_KEY key is wrong")
    return api_key


def clean_url(url:str):
    url = url.strip()
    BLOCKLIST = {"facebook.com", "t.me", "instagram.com","emag.ro"}
    if not url:
        return ""
    parts = urlparse(url) # ai câmpuri: scheme, netloc, path, query, fragment
    if parts.scheme not in {"http","https"}:
        return ""
    if not parts.netloc:
        return ""
    if parts.netloc in BLOCKLIST:
        return None
    clean_parts = parts._replace(fragment="")
    final_url = urlunparse(clean_parts)
    return final_url

def search_urls(query: str, num_pages: int, api_key: str, timeout_s: float = 10.0) -> list[str]:
    query=query.strip()
    max_pages = 5
    all_links=[]
    api_key = validate_api_key(api_key)

    if num_pages < 1:
        raise ValueError("Input valid number of pages")
    elif num_pages > max_pages:
        num_pages=max_pages

    if query == "":
        raise ValueError("Invalid query!")

    for page in range(1,num_pages+1):
        page_links=get_serper_page(query,page,api_key)
        all_links.extend(page_links)
        time.sleep(1)

    #Eliminam duplicatele si neinteresante
    seen=set()
    unique_links=[]
    for u in all_links:
        if u in seen:
            continue
        seen.add(u)
        unique_links.append(u)
    return unique_links

def fetch_html(url):
    url=clean_url(url)
    if not url:
        return None
    backoff_base=0.8
    last_error=None
    headers = {
        "User-Agent":"keyword-miner/0.1"
    }
    max_attemps=3
    for attempt in range(1,max_attemps+1):
        try:
            with httpx.Client(timeout=10,headers=headers) as client:
                r=client.get(url)
            status=r.status_code
            ctype=(r.headers.get("Content-Type") or "").lower()
            is_html="text/html" in ctype
            if status == 200 and is_html:
                return r.text
            elif status == 429:
                sleep=backoff_base*(2**(attempt))
                time.sleep(sleep)
                continue
            elif 500 <= status < 600:
                sleep = backoff_base * (2 ** (attempt - 1))
                time.sleep(sleep)
                continue
            elif 400<= status < 500:
                sleep = backoff_base * (2 ** (attempt - 1))
                time.sleep(sleep)
                continue
        except OSError or httpx.RequestError as e:
            last_error=e
            sleep_s = backoff_base * (2 ** (attempt - 1))
            time.sleep(sleep_s)
            continue
    return None

def extract_main_text(html,base_url):
    if not html or not isinstance(html,str):
        return None
    try:
        text=trafilatura.extract(html,url=base_url,include_comments=False)
        if text is None or len(text) < 500:
            return None
    except Exception as e:
        print(e)
    text = unicodedata.normalize("NFC", text).strip()
    return text

def get_page_text(url):
    html=fetch_html(url)
    if html is None:
        return None
    text=extract_main_text(html,url)
    return text

def text_filter(text):
    text=RE_URL.sub(" ",text)
    text=RE_EMAIL.sub(" ",text)
    text = RE_TAGS.sub(" ", text)
    text = RE_JS.sub(" ", text)
    text = RE_NUM.sub(" ", text)
    text = RE_MULTI.sub(" ", text).strip()
    tokens=RE_TOKEN.findall(text.lower())
    filtered_tokens=[t for t in tokens if len(t) >= 3 and t not in STOPWORDS_RO]
    return filtered_tokens or None
