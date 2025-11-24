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


async def classifier_node(state: AgentState) -> dict:
    raw = state["raw_message"]
    classification = classify_message(raw)
    session_id = state.get("session_id") or str(uuid.uuid4())

    if classification.city_unknown:
        return {
            "session_id": session_id,
            "detected_language": classification.language,
            "final_response": "Which city are you in right now?",
            "status_updates": ["City needed"],
        }

    city_key = classification.city.lower().replace(" ", "_")
    logger.info(f"Session {session_id[:8]} → City: {city_key}")

    markdown = fetch_city_resources(city_key)
    if not markdown.strip():
        return {
            "session_id": session_id,
            "detected_city": city_key,
            "final_response": f"I found {classification.city}, but no local data yet. Try asking general questions.",
            "status_updates": ["No OSM data"],
        }

    # THIS IS THE ONLY CHANGE YOU NEED
    build_session_vectorstore(session_id, markdown)

    return {
        "session_id": session_id,
        "detected_city": city_key,
        "detected_language": classification.language,
        "urgency": classification.urgency,
        "needs": classification.needs or [],
        "status_updates": [f"You're in {classification.city}"],
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


    
async def final_node(state: AgentState) -> dict:
    user_lang = state["detected_language"]
    city = state["detected_city"]

    # Generate full plan in user's native language
    full_plan = get_booking_guidance(
        city=city,
        user_language=user_lang,
        english_survival_plan=state["survival_plan_en"],
    ).strip()

    # Generate PDF
    pdf_url = None
    try:
        generate_pdf(content=full_plan, city=city, session_id=state["session_id"])
        pdf_url = f"{config.PUBLIC_URL}/downloads/{state['session_id']}.pdf"
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")

    # Attach PDF link
    if pdf_url:
        full_plan += f"\n\nYour Full Guide (PDF + maps):\n{pdf_url}"

    # Prevent WhatsApp cutting — auto-split long messages
    if len(full_plan) > 1400 or full_plan.count("\n") > 30:
        cutoff = 1350
        split_point = max(
            full_plan.rfind("\n\n", 800, cutoff),
            full_plan.rfind("\n", 800, cutoff),
            800
        )
        part1 = full_plan[:split_point].strip()
        part2 = "(continued...)\n\n" + full_plan[split_point:].strip()
        final_response = [part1, part2]
    else:
        final_response = full_plan

    return {
        "final_response": final_response,
        "pdf_url": pdf_url,
        "status_updates": ["Response ready"],
    }

    full_response_user_lang = get_booking_guidance(
        city=state["detected_city"],
        user_language=user_lang,
        english_survival_plan=state["survival_plan_en"],
    )

    pdf_url = None
    try:
        generate_pdf(
            content=full_response_user_lang,
            city=state["detected_city"],
            session_id=state["session_id"],
        )
        pdf_url = f"{config.PUBLIC_URL}/downloads/{state['session_id']}.pdf"
    except Exception as e:
        logger.error(f"PDF failed: {e}")

    # EMBED PDF URL DIRECTLY IN TEXT — 100% RELIABLE
    final_text = full_response_user_lang.strip()
    if pdf_url:
        final_text += f"\n\nYour Full Guide (PDF + maps):\n{pdf_url}"

    return {
        "final_response": final_text,
        "status_updates": ["Ready!"],
    }


def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("classifier", classifier_node)
    workflow.add_node("translator", translator_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("final", final_node)

    workflow.set_entry_point("classifier")

    workflow.add_edge("classifier", "translator")
    workflow.add_edge("translator", "planner")
    workflow.add_edge("planner", "final")
    workflow.add_edge("final", END)

    # Critical: short-circuit if city unknown
    workflow.add_conditional_edges(
        "classifier",
        lambda s: bool(s.get("final_response")),
        {True: END, False: "translator"},
    )

    return workflow.compile()