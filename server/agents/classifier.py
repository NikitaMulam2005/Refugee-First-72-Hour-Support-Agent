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
    prompt = f"""
You are an expert multilingual refugee message classifier.

User message (any language/script):  
"{message}"

TASKS — BE VERY STRICT:

1. CITY DETECTION (MOST IMPORTANT):
   - ONLY accept a real city name if the user explicitly mentions it
     Examples that count as city:
       "मुंबई", "Mumbai", "Delhi", "वॉर्सॉ", "Warszawa", "Berlin", "Kyiv", "Lviv" → use exact
   - If user only mentions a COUNTRY (even in any language):
       India, Poland, Germany, USA, Ukraine, Turkey, France, etc. → city = "Unknown"
   - "मी भारतात आहे", "أنا في بولندا", "I'm in Poland" → city = "Unknown"

2. Language code (ISO 639-1): hi, mr, ar, ur, fa, uk, ru, pl, en, etc.

3. Urgency: low, medium, high, critical

4. Needs: shelter, food, medical, registration, children, elderly, safety

RULES — NEVER BREAK THESE:
- If no city is mentioned → city = "Unknown", city_unknown = true
- If only country is mentioned → city = "Unknown", city_unknown = true
- If specific city mentioned → city = correct name, city_unknown = false
- Never assume or guess a city from country

Return ONLY valid JSON. No explanations.

{{
  "city": "Unknown",
  "language": "mr",
  "urgency": "high",
  "needs": ["shelter"],
  "city_unknown": true
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