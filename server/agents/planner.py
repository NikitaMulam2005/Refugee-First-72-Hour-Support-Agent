# backend/agents/planner.py
from groq import Groq
from config import config
from typing import List



client = Groq(api_key=config.GROQ_API_KEY)

def generate_survival_plan(
    city: str,
    language: str,
    urgency: str,
    needs: List[str],
    user_message: str,
    local_context: str  # ← REAL OSM DATA FROM RAG
) -> str:
    """
    THIS VERSION FORCES THE LLM TO USE REAL ADDRESSES.
    No more "go to a shelter" — it MUST say the actual name and address.
    """
    needs_str = ", ".join(needs)

    # Extract ONLY the real facilities (filter noise)
    facilities = []
    for line in local_context.split("\n"):
        line = line.strip()
        if line.startswith("## ") or ("address:" in line.lower()) or ("phone:" in line.lower()):
            facilities.append(line)
    
    if not facilities:
        facilities = ["No specific addresses found. Go to main train station and ask for refugee help."]

    facilities_text = "\n".join(facilities[:15])  # Top 15 lines max

    prompt = f"""
YOU ARE A REFUGEE CRISIS RESPONSE COORDINATOR IN {city.upper()}.

A refugee just arrived and said: "{user_message}"
Urgency: {urgency.upper()}
Needs: {needs_str}

CRITICAL RULE: YOU **MUST** USE THE REAL FACILITIES BELOW. 
DO NOT invent names or addresses. DO NOT say "a shelter" — say the actual name.

REAL FACILITIES (COPY-PASTE THESE EXACTLY):

{facilities_text}

NOW WRITE A 72-HOUR SURVIVAL PLAN IN SIMPLE ENGLISH.

MANDATORY STRUCTURE — USE THESE EXACT HEADINGS:

**FIRST 2 HOURS – IMMEDIATE SAFETY**
- Where to go RIGHT NOW (copy real shelter/clinic name + address)
- How to get there (metro/walk from center)
- What to say when you arrive

**NEXT 12 HOURS – REST & FOOD**
- Where to sleep tonight (real name + address)
- Where to get food/water (real name)
- Where to charge phone

**NEXT 48 HOURS – REGISTRATION & HELP**
- Where to register for asylum (real office or instructions)
- Medical help if needed
- Who to contact

TONE: Calm, direct, hopeful. Short sentences.
If "children" in needs → prioritize family-friendly places.
End with: "You are safe now. Help is real."

WRITE ONLY THE PLAN. NO INTRODUCTION.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,      # Lower = more obedient to instructions
            max_tokens=1800
        )
        plan = response.choices[0].message.content.strip()

        # Final safety check — if it still says "a shelter", override
        if any(phrase in plan.lower() for phrase in ["a shelter", "some shelter", "any shelter", "a clinic"]):
            plan = plan + "\n\nIMPORTANT: Use only the real addresses above. Do not trust unofficial helpers."

        return plan

    except Exception as e:
        print(f"Planner failed: {e}")
        return f"""
**FIRST 2 HOURS – IMMEDIATE SAFETY**
Go directly to the main train station in {city}.
Look for Red Cross, UNHCR, or police — say "I need refugee help".

**NEXT 12 HOURS**
Ask for emergency shelter — it is free.
You will get food and a place to sleep.

**NEXT 48 HOURS**
Go to government asylum office with any ID.
You are protected. You are not alone.
"""