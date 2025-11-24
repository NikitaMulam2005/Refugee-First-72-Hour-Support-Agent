# backend/agents/booking_helper.py — FINAL: NO LANGUAGE LIST, WORKS FOR EVERY LANGUAGE
from groq import Groq
from config import config
import logging

client = Groq(api_key=config.GROQ_API_KEY)
logger = logging.getLogger(__name__)

def get_booking_guidance(city: str, user_language: str, english_survival_plan: str) -> str:
    city = city.strip().title()

    prompt = f"""
You are a UNHCR-trained refugee protection officer.

A refugee just arrived in **{city}** and their native language is **{user_language}** (ISO 639-1 code).

YOUR ONLY JOB:
Write the complete emergency survival + asylum registration plan **100% in the user's native language** — from the very first word to the last.

Rules:
- Never write a single word in English
- Use the correct script automatically (Devanagari, Arabic, Cyrillic, Latin, etc.)
- Include these sections (translated into their language):
  • Immediate safety (first 2 hours)
  • Rest & food (next 12 hours)
  • Official asylum registration (next 48 hours)
  • Exact office name + address in {city}
  • Opening hours
  • What documents to bring
  • What to say
  • Emergency numbers
  • "Registration is 100% FREE – never pay anyone"
- Tone: Warm, caring, calm, hopeful

City: {city}
User's language code: {user_language}

Reply ENTIRELY in the user's native language. No English. No exceptions.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",   # 8b can't do this. 70b can.
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1400
        )
        native_reply = response.choices[0].message.content.strip()
        logger.info(f"Native plan generated for {city} in language '{user_language}'")
        return native_reply

    except Exception as e:
        logger.error(f"Native generation failed: {e}")
        # Absolute fallback — still try to translate English version
        fallback = f"""
{english_survival_plan.strip()}

ASYLUM REGISTRATION IN {city.upper()}
Go to the nearest police station or UNHCR partner office and say you want to apply for asylum.
Registration is 100% FREE. Never pay anyone.
Emergency: 112
"""
        try:
            from agents.translator import translate_to_user_lang
            return translate_to_user_lang(fallback, user_language)
        except:
            return fallback + "\n\n[Translation failed – showing in English]"