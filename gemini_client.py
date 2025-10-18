# gemini_client.py
"""
Robust Gemini integration using google-genai SDK with safe fallback.
- Tries to call client.models.generate_content(...)
- Extracts text from common response shapes
- Strips markdown code fences and parses JSON when possible
- Falls back to deterministic mock when the live call fails
"""

import json
import re
from utils import get_env

GEMINI_API_KEY = get_env("GEMINI_API_KEY")

# Try import of google-genai SDK
try:
    from google import genai
    HAS_GENAI = True
except Exception:
    HAS_GENAI = False

def build_prompt(fragment: str) -> str:
    return f"""
You are an expert at reconstructing fragmentary informal text into a coherent modern English sentence or two.
Return EXACTLY valid JSON with keys:
- reconstructed_text (string)
- explanations (list of strings)
- keywords (list of strings)
- confidence (float 0-1)

Only output valid JSON and nothing else.

Fragment:
\"\"\"{fragment}\"\"\"
"""

def _strip_code_fence(text: str) -> str:
    """Remove common markdown code fences like ```json ... ``` or ``` ... ```"""
    if not text:
        return text
    # remove triple-backtick fences possibly with `json` label
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text, flags=re.IGNORECASE)
    return text.strip()

def parse_model_text_to_json(text: str):
    """
    Robust parse: strip markdown fences, try JSON, otherwise return a safe dict.
    """
    if not text:
        return {"reconstructed_text":"", "explanations":[], "keywords":[], "confidence":0.0}

    cleaned = _strip_code_fence(text)

    # try parsing cleaned text as JSON
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "reconstructed_text" in parsed:
            # normalize and ensure types
            try:
                parsed["confidence"] = float(parsed.get("confidence", 0.5))
            except Exception:
                parsed["confidence"] = 0.5
            parsed.setdefault("explanations", [])
            parsed.setdefault("keywords", [])
            return parsed
    except Exception:
        pass

    # fallback: treat the cleaned text as reconstructed_text
    return {
        "reconstructed_text": cleaned.strip(),
        "explanations": [],
        "keywords": [],
        "confidence": 0.5
    }

def mock_reconstruction(fragment: str):
    """Deterministic mock used when live call isn't available or fails."""
    lower = fragment.lower()
    if "smh" in lower:
        return {
            "reconstructed_text": "Shaking my head at the drama about the 'Top 8' friends list on MySpace. People need to calm down; I have to go — talk to you later.",
            "explanations": ["smh -> 'shaking my head' (slang)", "ppl -> 'people'", "g2g -> 'got to go'"],
            "keywords": ["MySpace", "Top 8", "smh"],
            "confidence": 0.86
        }
    return {
        "reconstructed_text": fragment.strip(),
        "explanations": [],
        "keywords": [w.strip(".,!?") for w in fragment.split()[:5]],
        "confidence": 0.6
    }

def _extract_text_from_response(response):
    """
    Try several known response shapes used by google-genai SDKs and return a text string.
    """
    # 1) common documented property
    model_text = getattr(response, "text", None)
    if model_text:
        return model_text

    # 2) response.output -> list -> content -> text
    try:
        out = getattr(response, "output", None)
        if out and isinstance(out, (list, tuple)) and len(out) > 0:
            first = out[0]
            if isinstance(first, dict) and "content" in first:
                content = first["content"]
                if isinstance(content, (list, tuple)) and len(content) > 0:
                    c0 = content[0]
                    if isinstance(c0, dict) and "text" in c0:
                        return c0["text"]
                    elif isinstance(c0, str):
                        return c0
    except Exception:
        pass

    # 3) 'candidates' style
    try:
        cand = getattr(response, "candidates", None)
        if cand and isinstance(cand, (list, tuple)) and len(cand) > 0:
            first = cand[0]
            if isinstance(first, dict) and "content" in first:
                content = first["content"]
                if isinstance(content, (list, tuple)) and len(content) > 0:
                    c0 = content[0]
                    if isinstance(c0, dict) and "text" in c0:
                        return c0["text"]
                    elif isinstance(c0, str):
                        return c0
    except Exception:
        pass

    # 4) fallback to str()
    try:
        return str(response)
    except Exception:
        return None

def reconstruct(fragment: str):
    """
    Returns a dict with keys: reconstructed_text, explanations, keywords, confidence
    """
    # Early mock fallback
    if not HAS_GENAI or not GEMINI_API_KEY:
        if not HAS_GENAI:
            print("Notice: google-genai SDK not available; using mock reconstruction.")
        else:
            print("Notice: GEMINI_API_KEY not found; using mock reconstruction.")
        return mock_reconstruction(fragment)

    try:
        # Some SDKs support genai.configure(api_key=...), others read env automatically.
        try:
            if hasattr(genai, "configure"):
                genai.configure(api_key=GEMINI_API_KEY)
        except Exception:
            pass

        client = genai.Client()
        prompt = build_prompt(fragment)

        # Use the documented method without version-specific kwargs for broad compatibility.
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        model_text = _extract_text_from_response(response)
        if model_text is None:
            raise RuntimeError("Could not extract text from Gemini response.")

        parsed = parse_model_text_to_json(model_text)
        return parsed

    except Exception as e:
        print("Warning: Gemini live call failed — falling back to mock. Error:", e)
        return mock_reconstruction(fragment)
