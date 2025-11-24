# backend/agents/translator.py
import logging
from typing import Optional

logger = logging.getLogger(__name__)

translator_client = None
try:
    from google.cloud import translate_v2 as translate
    # NO 'project' arg — uses GOOGLE_APPLICATION_CREDENTIALS env
    translator_client = translate.Client()
    logger.info("Google Translate ready")
except Exception as e:
    logger.error(f"Translate init failed: {e}")
    translator_client = None

def translate_text(text: str, target: str = "en", source: Optional[str] = None) -> str:
    if not text or not text.strip():
        return text
    if not translator_client:
        return text.strip()
    try:
        result = translator_client.translate(
            text, target_language=target, source_language=source, format_="text"
        )
        return result["translatedText"].strip()
    except Exception as e:
        logger.warning(f"Translate error: {e}")
        return text.strip()

def translate_to_user_lang(text: str, user_language: str) -> str:
    if user_language == "en":
        return text
    return translate_text(text, target=user_language)