# search_client.py
"""
Search client — stricter token matching to avoid noisy unrelated matches.
Signature:
    search(original_fragment, reconstructed_text, keywords, top_n=5)
"""

import time
import re
import urllib.parse
import requests
from pathlib import Path
from utils import get_env

SEARCH_API_KEY = get_env("SEARCH_API_KEY")
SEARCH_ENGINE_CX = get_env("SEARCH_ENGINE_CX")
DEBUG = get_env("DEBUG_SEARCH", "") == "1"

# Tunables
MAX_RESULTS_PER_QUERY = 6
DEEP_RESULTS_PER_QUERY = 12
SLOT_PAUSE = 0.12
MAX_TOKEN_SLOTS = 4
TOP_N_DEFAULT = 5

# Built-in lists
SLANG_TOKENS = {
    "wtf","smh","g2g","ttyl","brb","lol","omg","lmao","bro","bruh","uhh","uh","ppl"
}
PLATFORM_KEYWORDS = {"myspace","tiktok","twitter","x","reddit","tumblr","facebook","instagram","snapchat","youtube","spotify","discord"}
AUTHORITATIVE_DOMAINS = ["wiktionary.org","wikipedia.org","dictionary.com","merriam-webster.com","oxforddictionaries.com"]
URBAN_DOMAIN = "urbandictionary.com"
STOPWORDS = {"the","a","an","and","or","in","on","at","to","for","of","is","it","i","you","we","they","this","that","these","those","are","was","were","be","been","with","as","by","about","from","what","who","how","when","why"}

GAZ_PATH = Path("data/culture_gazetteer.txt")
def _load_gazetteer():
    if not GAZ_PATH.exists():
        return set()
    return {l.strip().lower() for l in GAZ_PATH.read_text(encoding="utf-8").splitlines() if l.strip()}
_GAZ = _load_gazetteer()

def _clean(s: str) -> str:
    if not s: return ""
    s = s.replace("`"," ").replace("\n"," ").strip()
    s = re.sub(r"[^\w\s'-]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _tokenize(s: str):
    return [t for t in _clean(s).lower().split() if t and t not in STOPWORDS]

def _ngrams(tokens, n):
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)] if len(tokens) >= n else []

def detect_dynamic_tokens(original_fragment: str, reconstructed_text: str, keywords: list, max_tokens=MAX_TOKEN_SLOTS):
    found = []
    seen = set()
    def push(tok):
        t = tok.strip().lower()
        if not t or t in seen or len(t) <= 1:
            return
        seen.add(t); found.append(t)

    of = (original_fragment or "").strip()
    rf = (reconstructed_text or "").strip()
    kw_text = " ".join([k for k in (keywords or []) if isinstance(k,str)]).strip().lower()

    # 1) slang tokens as whole words
    for s in SLANG_TOKENS:
        if re.search(r"\b" + re.escape(s) + r"\b", of, flags=re.I) or re.search(r"\b" + re.escape(s) + r"\b", kw_text, flags=re.I):
            push(s)

    # 2) gazetteer
    for g in _GAZ:
        if g in of.lower() or g in kw_text or g in rf.lower():
            push(g)

    # 3) platform keywords as whole words
    for p in PLATFORM_KEYWORDS:
        if re.search(r"\b" + re.escape(p) + r"\b", of, flags=re.I) or re.search(r"\b" + re.escape(p) + r"\b", kw_text, flags=re.I):
            push(p)

    # 4) numeric ranks like top 8
    m = re.search(r"\btop[- ]?\d{1,2}\b", of.lower())
    if m: push(m.group(0))

    # 5) quoted phrases in original fragment
    for q in re.findall(r'"([^"]+)"', of):
        push(q)
    for q in re.findall(r"'([^']+)'", of):
        push(q)

    # 6) n-grams heuristic from original first, then keywords, then reconstructed
    def extract_from(text):
        tokens = _tokenize(text)
        for n in (3,2,1):
            for ng in _ngrams(tokens, n):
                if re.fullmatch(r"\d+", ng): continue
                push(ng)
    extract_from(of); extract_from(kw_text); extract_from(rf)

    return found[:max_tokens]

TOKEN_TEMPLATES = {
    "wtf": ["what does wtf mean","wtf meaning","wtf slang meaning","wtf site:urbandictionary.com","wtf site:wiktionary.org"],
    "smh": ["what does smh mean","smh meaning","smh slang meaning","smh site:urbandictionary.com","smh site:merriam-webster.com"],
    "g2g": ["what does g2g mean","g2g meaning","g2g site:urbandictionary.com"],
    "ttyl": ["what does ttyl mean","ttyl meaning","ttyl site:urbandictionary.com"],
    "brb": ["what does brb mean","brb meaning","brb site:urbandictionary.com"],
    "lol": ["what does lol mean","lol meaning","lol site:urbandictionary.com"],
    "omg": ["what does omg mean","omg meaning","omg site:urbandictionary.com"],
    "lmao": ["what does lmao mean","lmao meaning","lmao site:urbandictionary.com"],
    "bro": ["bro meaning slang","bro slang meaning","bro meaning","bro site:urbandictionary.com","bro site:wiktionary.org"],
    "uh": ["uh meaning interjection","uh filler word meaning","uh site:wiktionary.org","uh site:merriam-webster.com"],
    "uhh": ["uhh meaning","uhh filler word meaning","uhh site:urbandictionary.com","uhh site:wiktionary.org"],
    "ppl": ["ppl meaning texting","ppl slang meaning","ppl stands for people"],
    "top 8": ['"Top 8" MySpace friends list explanation','MySpace "Top 8" feature explanation','MySpace Top 8 site:wikipedia.org'],
    "myspace": ['MySpace Top 8 feature','MySpace Top 8 site:wikipedia.org','MySpace friends list Top 8 explanation']
}
DEFAULT_TOKEN_TEMPLATES = ["what does {token} mean","{token} meaning","{token} slang meaning","{token} site:urbandictionary.com","{token} site:wiktionary.org"]
def _templates_for_token(token):
    t = token.lower()
    if t in TOKEN_TEMPLATES:
        return TOKEN_TEMPLATES[t]
    return [tpl.format(token=token) for tpl in DEFAULT_TOKEN_TEMPLATES]

def _call_cse(query, num=MAX_RESULTS_PER_QUERY):
    if DEBUG: print("[DEBUG] QUERY ->", query)
    base = "https://www.googleapis.com/customsearch/v1"
    params = {"key": SEARCH_API_KEY, "cx": SEARCH_ENGINE_CX, "q": query, "num": num}
    r = requests.get(base, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", []) or []
    out=[]
    for it in items:
        out.append({"title": it.get("title"), "url": it.get("link") or it.get("formattedUrl"), "snippet": it.get("snippet") or ""})
    if DEBUG:
        print("[DEBUG]  -> returned urls:", [o["url"] for o in out[:6]])
    return out

def _is_authoritative(url: str) -> bool:
    if not url: return False
    u = url.lower()
    return any(d in u for d in AUTHORITATIVE_DOMAINS)

def _is_urban(url: str) -> bool:
    if not url: return False
    return URBAN_DOMAIN in url.lower()

def _token_in_item_whole(token: str, item: dict) -> bool:
    """Require whole-word match for single-word tokens; substring match for multiword tokens."""
    if not token or not item:
        return False
    tok = token.lower()
    combined = " ".join([(item.get("title") or ""), (item.get("snippet") or ""), (item.get("url") or "")]).lower()
    if " " in tok:
        # multiword token: substring match
        return tok in combined
    # single-word token: require whole-word boundary
    return re.search(r"\b" + re.escape(tok) + r"\b", combined) is not None

def _pick_best_for_token(items, token):
    if not items: return None
    tok = (token or "").lower()
    def score(it):
        s = 0
        url = (it.get("url") or "").lower()
        if _is_authoritative(url): s += 100
        if _is_urban(url): s += 80
        if tok and _token_in_item_whole(tok, it): s += 30
        if it.get("snippet"): s += 3
        return s
    items_sorted = sorted(items, key=score, reverse=True)
    best = items_sorted[0]
    # Acceptance: require whole-token presence OR authoritative OR urban (with reasonable score)
    if tok and _token_in_item_whole(tok, best):
        return best
    # only accept authoritative if it's actually about the token
    if _is_authoritative(best.get("url")) and _token_in_item_whole(tok, best):
        return best
    # accept Urban Dictionary only if the token appears in title/snippet/url
    if _is_urban(best.get("url")) and _token_in_item_whole(tok, best):
        return best
    return None


def _keyword_overlap_score(item, keywords):
    if not keywords: return 0
    combined = " ".join([ item.get("title","") or "", item.get("snippet","") or "", item.get("url","") or "" ]).lower()
    score = 0
    for kw in (keywords or []):
        if not isinstance(kw,str): continue
        k = kw.lower().strip()
        if not k: continue
        if k in combined: score += 3
        for part in k.split():
            if part and part in combined: score += 1
    return score

def _mock_search(queries, top_n=TOP_N_DEFAULT):
    out=[]
    for q in queries:
        qq=q.lower()
        if "wtf" in qq: out.append({"title":"WTF - UrbanDictionary","url":"https://www.urbandictionary.com/define.php?term=wtf","snippet":"UrbanDictionary"})
        elif "bro" in qq: out.append({"title":"Bro - Wiktionary","url":"https://en.wiktionary.org/wiki/bro","snippet":"Wiktionary"})
        elif "uh" in qq or "uhh" in qq: out.append({"title":"UH - Merriam-Webster","url":"https://www.merriam-webster.com/dictionary/uh","snippet":"Merriam-Webster"})
        else: out.append({"title":f"Search results for {q[:40]}","url":f"https://www.google.com/search?q={urllib.parse.quote(q)}","snippet":""})
        if len(out) >= top_n: break
    return out[:top_n]

def search(original_fragment, reconstructed_text, keywords, top_n=TOP_N_DEFAULT):
    if not SEARCH_API_KEY or not SEARCH_ENGINE_CX:
        tokens = detect_dynamic_tokens(original_fragment, reconstructed_text, keywords, max_tokens=MAX_TOKEN_SLOTS)
        qlist=[]
        for t in tokens:
            for tpl in _templates_for_token(t)[:3]:
                qlist.append(tpl if '{token}' not in tpl else tpl.format(token=t))
        if not qlist:
            qlist = [k for k in (keywords or []) if isinstance(k,str)] or [original_fragment[:140]]
        return _mock_search(qlist, top_n=top_n)

    final=[]; seen_urls=set()
    tokens = detect_dynamic_tokens(original_fragment, reconstructed_text, keywords, max_tokens=MAX_TOKEN_SLOTS)
    if DEBUG: print("[DEBUG] tokens:", tokens)

    # Reserve token slots
    for tok in tokens:
        if len(final) >= top_n: break
        templates = _templates_for_token(tok)
        for tpl in templates:
            q = tpl if '{token}' not in tpl else tpl.format(token=tok)
            try:
                items = _call_cse(q, num=MAX_RESULTS_PER_QUERY)
            except Exception as e:
                if DEBUG: print("[DEBUG] error token query:", q, "->", repr(e))
                items=[]
            best = _pick_best_for_token(items, tok)
            if best and best.get("url") and best["url"] not in seen_urls:
                final.append(best); seen_urls.add(best["url"]); break
            time.sleep(SLOT_PAUSE)

    # Deepen per-token if still need slots; accept only whole-token presence OR authoritative/urban
    if len(final) < top_n:
        for tok in tokens:
            if len(final) >= top_n: break
            deep_queries = [f"{tok} meaning", f"{tok} slang", f"{tok}", f"{tok} site:urbandictionary.com"]
            seen_q=set(); dq=[]
            for q in deep_queries:
                if q in seen_q: continue
                seen_q.add(q); dq.append(q)
            for q in dq:
                try:
                    items = _call_cse(q, num=DEEP_RESULTS_PER_QUERY)
                except Exception as e:
                    if DEBUG: print("[DEBUG] error deep token query:", q, "->", repr(e))
                    items=[]
                for it in items:
                    url = it.get("url")
                    if not url or url in seen_urls: continue
                    # strictly require whole-token presence OR authoritative OR urban
                    if _token_in_item_whole(tok, it) or _is_authoritative(url) or _is_urban(url):
                        final.append(it); seen_urls.add(url)
                        if len(final) >= top_n: break
                time.sleep(SLOT_PAUSE)
                if len(final) >= top_n: break

    # Deepen per-keyword if necessary
    if len(final) < top_n and keywords:
        for kw in (keywords or []):
            if len(final) >= top_n: break
            q_plain = kw.strip()
            try:
                items = _call_cse(q_plain, num=DEEP_RESULTS_PER_QUERY)
            except Exception as e:
                if DEBUG: print("[DEBUG] error deep keyword query:", q_plain, "->", repr(e))
                items=[]
            for it in items:
                url = it.get("url")
                if not url or url in seen_urls: continue
                overlap = _keyword_overlap_score(it, keywords)
                if overlap > 0 or _is_authoritative(url) or _is_urban(url):
                    final.append(it); seen_urls.add(url)
                    if len(final) >= top_n: break
            time.sleep(SLOT_PAUSE)

    # Final snippet fallback (strict relevance)
    if len(final) < top_n:
        snippet_q = original_fragment[:140] if original_fragment else (reconstructed_text[:140] if reconstructed_text else "")
        if snippet_q:
            try:
                items = _call_cse(snippet_q, num=DEEP_RESULTS_PER_QUERY)
            except Exception as e:
                if DEBUG: print("[DEBUG] error snippet query:", snippet_q, "->", repr(e))
                items=[]
            for it in items:
                url = it.get("url")
                if not url or url in seen_urls: continue
                overlap = _keyword_overlap_score(it, keywords)
                if overlap > 0 or _is_authoritative(url) or _is_urban(url):
                    final.append(it); seen_urls.add(url)
                    if len(final) >= top_n: break
            time.sleep(SLOT_PAUSE)

    return final[:top_n]
