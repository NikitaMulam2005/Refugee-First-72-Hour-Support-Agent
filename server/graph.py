# backend/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator
import uuid
import logging
from langgraph.graph import StateGraph, END
from agents.classifier import classify_message
from agents.translator import translate_text
from agents.planner import generate_survival_plan
from agents.booking_helper import get_booking_guidance
from rag.retrieve import build_session_vectorstore, search_relevant_chunks
from tools.osm_utils import fetch_city_resources
from tools.pdf_generator import generate_pdf
from config import config

logger = logging.getLogger(__name__)

# Allow keys to be added gradually
class AgentState(TypedDict, total=False):
    raw_message: str
    session_id: str
    detected_city: str
    detected_language: str
    urgency: str
    needs: List[str]
    translated_message: str
    rag_context: str
    survival_plan_en: str
    final_response: str
    pdf_url: str
    status_updates: Annotated[List[str], operator.add]


async def greeting_node(state: AgentState) -> dict:
    """
    Simple multilingual greeting fast-path.
    Responds to Hi / हाय / سلام etc. with a friendly hello — NO city mention.
    """
    message = state["raw_message"].strip()

    GREETINGS = {
        "en": ["hi", "hello", "hey", "hii", "hiii", "helo", "good morning", "good evening", "gm", "ge"],
        "hi": ["हाय", "नमस्ते", "हेलो", "हॅलो", "namaste", "namaskar", "हाय्या"],
        "mr": ["नमस्कार", "हाय", "हॅलो"],
        "ar": ["مرحبا", "السلام عليكم", "سلام", "هلا", "مرحباً"],
        "ur": ["ہیلو", "السلام علیکم", "ہائے", "سلام"],
        "fa": ["سلام", "درود"],
        "pl": ["cześć", "dzień dobry", "hej", "cześć!"],
        "uk": ["привіт", "добрий день", "здравствуйте", "привет"],
        "ru": ["привет", "здравствуйте", "добрый день"],
    }

    lower = message.lower()
    detected_lang = "en"
    is_greeting = len(message) <= 6

    if not is_greeting:
        for lang, words in GREETINGS.items():
            if any(g in lower for g in [w.lower() for w in words]):
                detected_lang = lang
                is_greeting = True
                break

    if not is_greeting:
        return {}  # Not a greeting → continue to classifier

    # SIMPLE, CLEAN GREETINGS — NO CITY AT ALL
    simple_greetings = {
        "en": "Hello! How can I help you today?",
        "hi": "नमस्ते! कैसे मदद कर सकता हूँ?",
        "mr": "नमस्कार! कशी मदत करू शकतो?",
        "ar": "مرحبا! كيف يمكنني مساعدتك؟",
        "ur": "ہیلو! کیسے مدد کر سکتا ہوں؟",
        "fa": "سلام! چطور می‌توانم کمک کنم؟",
        "pl": "Cześć! Jak mogę pomóc?",
        "uk": "Привіт! Як я можу допомогти?",
        "ru": "Привет! Чем могу помочь?",
    }

    reply = simple_greetings.get(detected_lang, simple_greetings["en"])

    return {
        "detected_language": detected_lang,
        "final_response": reply,
        "status_updates": ["Greeting sent"],
    }

async def classifier_node(state: AgentState) -> dict:
    raw = state["raw_message"]
    classification = classify_message(raw)  # ← uses the bullet-proof prompt
    session_id = state.get("session_id") or str(uuid.uuid4())


    detected_lang = classification.language.lower()  # ← "en", "hi", "ar", etc.
    city_raw = classification.city if not classification.city_unknown else "Unknown"

    # Log clearly what we detected
    logger.info(f"Session {session_id[:8]} → City: '{city_raw}' | Language: '{detected_lang}' | Unknown: {classification.city_unknown}")

    # 1. City is unknown → ask for it (in user's actual language later)
    if classification.city_unknown:
        return {
            "session_id": session_id,
            "detected_language": detected_lang,
            "final_response": "Which city are you in right now?",
            "status_updates": ["City needed"],
        }

    # 2. City found → normalize for OSM lookup only
    city_key = city_raw.strip().lower().replace(" ", "_")
    
    # Fetch local resources
    markdown = fetch_city_resources(city_key)
    if not markdown.strip():
        return {
            "session_id": session_id,
            "detected_city": city_key,
            "detected_language": detected_lang,
            "final_response": f"I found {city_raw}, but no local data yet. Try asking general questions.",
            "status_updates": ["No OSM data"],
        }

    # Build RAG index for this city
    build_session_vectorstore(session_id, markdown)

 
    return {
        "session_id": session_id,
        "detected_city": city_key,
        "detected_language": detected_lang,         
        "urgency": classification.urgency,
        "needs": classification.needs or [],
        "status_updates": [f"You're in {city_raw} ({detected_lang})"]
    }

async def translator_node(state: AgentState) -> dict:
    if state["detected_language"] == "en":
        translated = state["raw_message"]
    else:
        try:
            translated = translate_text(state["raw_message"], target="en")
        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            translated = state["raw_message"]
    return {"translated_message": translated, "status_updates": ["Translating..."]}


async def planner_node(state: AgentState) -> dict:
    session_id = state["session_id"]
    query = state["translated_message"]

    try:
        docs = search_relevant_chunks(session_id, query, k=8)
        context = "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        logger.error(f"RAG failed: {e}")
        context = "No local information available."

    plan_en = generate_survival_plan(
        city=state["detected_city"],
        language="en",
        urgency=state["urgency"],
        needs=state["needs"],
        user_message=query,
        local_context=context,
    )

    return {
        "survival_plan_en": plan_en,
        "rag_context": context,
        "status_updates": ["Creating your plan..."],
    }

from tools.pdf_generator import generate_pdf   # ← our fixed version


async def final_node(state: AgentState) -> dict:
    user_lang = state["detected_language"]      # "en", "hi", "ja", etc.
    city = state["detected_city"]
    english_plan = state["survival_plan_en"]
    session_id = state["session_id"]            # usually the phone number like "+919137398912"

    logger.info(f"FINAL_NODE → Language: '{user_lang}' | City: {city} | Session: {session_id}")

    # 1. Get the plan in the user's language
    if user_lang == "en":
        full_plan = english_plan.strip()
    else:
        full_plan = get_booking_guidance(
            city=city,
            user_language=user_lang,
            english_survival_plan=english_plan,
        ).strip()

    # 2. Generate PDF + get the correct public URL path
    pdf_url = None
    try:
        # This now returns "/downloads/wa_plus919137398912.pdf"
        relative_pdf_path = generate_pdf(
            content=state["survival_plan_en"],
            city=city,
            session_id=session_id,       # can be phone number with +
        )
        pdf_url = f"{config.PUBLIC_URL}{relative_pdf_path}"
        logger.info(f"PDF generated successfully → {pdf_url}")
    except Exception as e:
        logger.error(f"PDF generation failed for {session_id}: {e}", exc_info=True)

    # 3. Append PDF link at the end (only if generated)
    if pdf_url:
        full_plan += f"\n\nYour Full Survival Guide (PDF with maps):\n{pdf_url}"

    # 4. Auto-split very long messages for WhatsApp (max ~1600 chars per message)
    if len(full_plan) > 1400 or full_plan.count("\n") > 35:
        # Find a good breaking point (paragraph or line break)
        cutoff = 1350
        split_point = max(
            full_plan.rfind("\n\n", 600, cutoff),
            full_plan.rfind("\n", 600, cutoff),
            600,
        )
        part1 = full_plan[:split_point].strip()
        part2 = full_plan[split_point:].strip()

        final_response = [
            part1,
            "(...continued)\n\n" + part2
        ]
    else:
        final_response = full_plan

    return {
        "final_response": final_response,
        "pdf_url": pdf_url,                    # useful for logging/analytics
        "status_updates": ["Response ready"],
    }


def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("greeting", greeting_node)      # ← ADD THIS
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("translator", translator_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("final", final_node)

    workflow.set_entry_point("greeting")            

   
    workflow.add_conditional_edges(
        "greeting",
        lambda s: bool(s.get("final_response")),
        {True: END, False: "classifier"}
    )

    # Rest of your graph stays 100% unchanged
    workflow.add_edge("classifier", "translator")
    workflow.add_edge("translator", "planner")
    workflow.add_edge("planner", "final")
    workflow.add_edge("final", END)

    workflow.add_conditional_edges(
        "classifier",
        lambda s: bool(s.get("final_response")),
        {True: END, False: "translator"},
    )

    return workflow.compile()