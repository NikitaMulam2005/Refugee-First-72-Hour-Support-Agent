# backend/agents/classifier.py
from groq import Groq
from pydantic import BaseModel
from typing import List, Optional
from config import config
import json
import re

client = Groq(api_key=config.GROQ_API_KEY)

class Classification(BaseModel):
    city: str
    language: str
    urgency: str
    needs: List[str]
    city_unknown: Optional[bool] = False  # New flag

def classify_message(message: str) -> Classification:
    """
    Enhanced classifier that detects missing city and asks for it.
    Returns structured output + special flag if city is unknown.
    """
    prompt = CLASSIFIER_PROMPT = f"""
You are an expert refugee message classifier. Analyze ONLY the current message. Never use history.

MESSAGE: "{message}"

RULES (NEVER BREAK):

1. CITY:
   - Return city only if explicitly written in THIS message
   - Use EXACT spelling the user typed (Mumbai, मुंबई, mumbai, etc.)
   - "i am in mumbai" → city = "mumbai"
   - "main mumbai ja raha hun" → city = "mumbai"
   - Only country → "Unknown"

2. LANGUAGE (MOST IMPORTANT):
   - Detect the language the user actually wrote in (ISO 639-1)
   - Script first, then vocabulary:
        • Any Devanagari → "hi"
        • Romanised Hindi ("main", "mein", "hu", "hoon", "mumbai ja raha") → "hi"
        • Pure English ("i am in mumbai", "help me") → "en"
        • Arabic script → "ar"
        • Cyrillic → "uk" or "ru"
   - City names do NOT affect language detection

3. urgency: low | medium | high | critical
4. needs: shelter, food, medical, registration, children, elderly, safety

Return ONLY valid JSON:

{{
  "city": "Unknown",
  "city_unknown": true,
  "language": "en",
  "urgency": "low",
  "needs": []
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=180
        )

        content = response.choices[0].message.content.strip()
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group())
            # Ensure city_unknown exists
            city_unknown = data.get("city_unknown", False)
            if data.get("city", "").strip() in ["", "Unknown", "unknown", "null"]:
                data["city"] = "Unknown"
                data["city_unknown"] = True
            
            return Classification(
                city=data.get("city", "Unknown"),
                language=data.get("language", "en"),
                urgency=data.get("urgency", "medium"),
                needs=data.get("needs", ["shelter"]),
                city_unknown=city_unknown
            )

    except Exception as e:
        print(f"Classification error: {e}")

    # Final fallback
    return Classification(
        city="Unknown",
        language="en",
        urgency="medium",
        needs=["shelter"],
        city_unknown=True
    )