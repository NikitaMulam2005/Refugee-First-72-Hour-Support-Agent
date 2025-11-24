# tools/whatsapp.py — FINAL FIXED VERSION (Supports split messages + never cuts)
from fastapi import APIRouter, Request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from typing import Optional, Dict, List
import logging
import re

from config import config
from graph import create_graph

graph = create_graph()
logger = logging.getLogger("whatsapp")
router = APIRouter()

twilio_client = None
if config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
    twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

USER_PDF_STORE: Dict[str, str] = {}
MAX_CHARS = 1590

async def process_message(session_id: str, message: str) -> tuple[any, Optional[str]]:
    try:
        async for event in graph.astream_events(
            input={"raw_message": message, "session_id": session_id},
            version="v2",
            config={"recursion_limit": 50},
        ):
            if event["event"] == "on_chain_end":
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict) and "final_response" in output:
                    response = output["final_response"]
                    pdf_url = output.get("pdf_url")
                    logger.info("Graph completed → response ready")
                    return response, pdf_url
    except Exception as e:
        logger.error(f"Graph error: {e}", exc_info=True)
    return "I'm preparing your help plan...", None
    

def make_public_url(url: str) -> str:
    if not getattr(config, "PUBLIC_URL", None):
        return url
    for local in ["http://localhost:8000", "http://127.0.0.1:8000", "http://0.0.0.0:8000"]:
        url = url.replace(local, config.PUBLIC_URL.rstrip("/"))
    return url


def send_proactive(to: str, text: str):
    if not twilio_client:
        return
    try:
        clean = text.encode("utf-8", "ignore").decode("utf-8")[:MAX_CHARS]
        twilio_client.messages.create(
            from_=config.TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to}",
            body=clean
        )
        logger.info(f"Proactive sent to {to}")
    except Exception as e:
        logger.error(f"Proactive failed: {e}")


@router.post("/")
async def whatsapp_webhook(request: Request):
    global USER_PDF_STORE

    try:
        form = await request.form()
        from_number = form.get("From", "").replace("whatsapp:", "")
        body = (form.get("Body") or "").strip()

        if not from_number or not body:
            return "", 400

        expected = config.TWILIO_WHATSAPP_NUMBER.replace("whatsapp:", "").replace("+", "")
        to_number = form.get("To", "").replace("whatsapp:", "").replace("+", "")
        if expected not in to_number:
            return "", 200

        logger.info(f"WhatsApp ← {from_number}: {body[:60]}")
        session_id = f"wa_{from_number}"

        # ——— AUTO SEND PDF ON "PDF" ———
        if re.search(r"\bpdf\b", body, re.IGNORECASE):
            pdf_url = USER_PDF_STORE.get(from_number)
            if pdf_url:
                send_proactive(from_number, f"Here is your complete guide:\n\n{pdf_url}")
                resp = MessagingResponse()
                resp.message("PDF sent!")
                return Response(content=str(resp), media_type="text/xml")
            else:
                resp = MessagingResponse()
                resp.message("No PDF available yet.")
                return Response(content=str(resp), media_type="text/xml")

        # ——— MAIN FLOW ———
        response_obj, pdf_url = await process_message(session_id, body)

        # Save PDF URL for later
        public_pdf_url = None
        if pdf_url:
            public_pdf_url = make_public_url(pdf_url)
            USER_PDF_STORE[from_number] = public_pdf_url

        # ——— SEND ONE OR MULTIPLE MESSAGES ———
        resp = MessagingResponse()

        # Convert to list if single string
        messages: List[str] = (
            response_obj if isinstance(response_obj, list) else [response_obj]
        )

        for i, msg_text in enumerate(messages):
            clean_msg = msg_text.strip().encode("utf-8", "ignore").decode("utf-8")

            # Add PDF link only to first message
            if i == 0 and public_pdf_url:
                pdf_line = f"\n\nYour Full Guide (PDF + maps):\n{public_pdf_url}"
                if len(clean_msg + pdf_line) <= MAX_CHARS:
                    clean_msg += pdf_line
                else:
                    clean_msg += "\n\nReply “PDF” to get your full guide."

            resp.message(clean_msg)

        logger.info(f"WhatsApp → {from_number}: Sent {len(messages)} message(s)")
        return Response(content=str(resp), media_type="text/xml")

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        resp = MessagingResponse()
        resp.message("Sorry, something went wrong. Try again.")
        return Response(content=str(resp), media_type="text/xml"), 200


@router.get("/")
async def status():
    return {
        "status": "LIVE – Split messages + Auto PDF",
        "number": config.TWILIO_WHATSAPP_NUMBER,
        "active_users_with_pdf": len(USER_PDF_STORE),
        "ready": True
    }