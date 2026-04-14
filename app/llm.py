from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.config import get_settings
from app.models import ConversationRecord, UserProfile

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a CRM intelligence engine. Extract a clean, structured profile from sales conversations. A sales agent must be able to read it in 10 seconds and know exactly who they are talking to.

Return ONLY valid JSON matching the schema below. No markdown, no commentary.

---

## LANGUAGE RULE
All profile fields must be written in English — except personal.name (keep as written by the customer) and personal.delivery_address (keep in the customer's language). Everything else: pain_points, buying_persona, current_needs, personal_details, etc. — write in English regardless of the conversation language.

## IGNORE ASSISTANT ERRORS
The assistant (bot) may contain bugs: calling the customer by the wrong name, calling itself by the customer's name, giving inconsistent responses. Extract facts ONLY from what the CUSTOMER writes, not from assistant messages — unless the assistant is confirming an order or quoting cart contents. Never extract the customer's name or identity from assistant messages.

---

## FIELD GUIDE

### personal
- name: full name from the customer's own messages or checkout form. Never from the assistant greeting.
- gender: "male" / "female" / "unknown".
  Infer from Arabic/non-Latin names — عطاء، محمد، أحمد، خالد، فهد = male; فاطمة، مريم، نور، سارة = female.
  Also infer from pronouns or explicit mention. Never leave "unknown" if the name makes it obvious.
- phone: the single most recent phone number from the customer. One number only — no concatenation. If multiple appear, keep the last one.
- company, role: fill only if mentioned by the customer.
- location: city + country only. Infer from shipping address or any mention. e.g. "Riyadh, Saudi Arabia". Never include zip code.
- delivery_address: the FULL address the customer provided — address fields ONLY (street, building, district, city, country, zip). No commentary.
  Use the LATEST complete submission. On re-submission, REPLACE entirely — never merge across submissions.
  BAD: "Street X, Riyadh (re-entered due to errors)"
  GOOD: "Street X, Building 2456, Apt 12, Al-Dira, Riyadh, Saudi Arabia, 13336"
  The fact they had to re-enter it → pain_point, NOT here.

### preferences
- communication_style: infer ONLY from how the customer writes — message length, tone, directness.
  e.g. "brief and direct" / "asks many questions" / "responds well to specific suggestions"
  NOT from checkout behavior. Leave empty if there is insufficient signal.
- best_contact_channel: ONLY if the customer explicitly states a preference. Never infer from conversation medium.
- languages: ALL languages the customer uses in their own messages. Scan every customer message.
  Checkout forms in Arabic ≠ Arabic speaker if all other messages are in English.
  BAD: ["Arabic"] when the customer writes mostly English with Arabic checkout forms only
  GOOD: ["English", "Arabic"]

### sales › buying_persona  ← most important, always update
ONE or TWO punchy sentences. Who is this buyer, why do they buy, how do they decide.
Must be consistent with relationship.status: "returning customer" or "active buyer" → must say "repeat buyer", never "first-time buyer".
Include: who they buy for, category, price tier, proven buyer or prospect.
GOOD: "Repeat buyer shopping for himself and his wife — classic watches, 30–190 SAR range. Persistent through checkout friction; has completed multiple orders."

### sales › current_needs
What they are actively shopping for RIGHT NOW.
- Remove a need ONLY when a confirmed order for it exists in purchase_history, OR the customer explicitly says they no longer want it.
- Checkout failure does NOT remove a need.
- Group by recipient: "Wife: classic women's watch (prefers gold)"
- If all needs for a recipient are fulfilled, remove that entry entirely.

### sales › buying_triggers
Recurring PATTERNS that drive purchases — occasions, relationships, habits. NOT product lists.
Think: WHY and WHEN does this person buy, not WHAT they buy.
BAD: "Buys classic watches" ← that's a preference, not a trigger
GOOD: "Buys gifts for wife alongside personal purchases — shops for both in the same session"
GOOD: "Purchases driven by personal style upgrades — shops when he needs something specific"
Leave empty if no clear recurring pattern is evident.

### sales › pain_points
Specific frustrations, one distinct problem per entry. Write in English.
- Checkout/system failures ARE pain points — count exact occurrences.
- Address re-entry is a SEPARATE pain point from checkout failures — different root cause.
- A problem and its direct consequence are ONE entry.
GOOD: "Checkout failed 3× — postal code format rejected by system"
GOOD: "Delivery address not saved — re-entered from scratch each session"

### sales › objections_raised
Hesitations that slowed or blocked the purchase. Different from pain_points (which are system/process frustrations).
Examples: price concern, delivery time worry, product availability doubt, wanting to compare before deciding.
Leave empty if the customer showed no hesitation — do not invent objections.

### sales › budget_range
Infer from ALL prices seen across the conversation (cart items, confirmed purchases, mentioned prices).
Use the full observed range — not just confirmed purchases.
e.g. "30–189 SAR" if those were the extremes seen.

### sales › purchase_history
Confirmed completed orders only. An order is confirmed ONLY when the assistant sends an explicit success message ("تمت عملية الطلب بنجاح", "Your order has been placed", or a checkout URL).
- Adding to cart ≠ purchase.
- Checkout failure ≠ purchase.
- Cart cleared before checkout ≠ purchase.
- Trace chronologically: at each confirmation, what was in the cart? Record that item + price.
Format: "Item name – price"

### relationship › status
MUST be exactly one of: "new lead" / "warm prospect" / "active buyer" / "returning customer" / "negotiating" / "closed"
At least one confirmed order → "active buyer" or "returning customer". Never leave empty.

### relationship › last_contact_date
ISO date (YYYY-MM-DD) of the most recent conversation. Infer from date references in messages, or use today's date as a fallback if no date is mentioned.

### relationship › personal_details
Rapport facts NOT captured in any other field. Write in English.
DO NOT repeat: gender, location, communication style, buying behavior, or family members (those go in relatives).
USE FOR: hobbies, life events, memorable personal context, personality traits useful for rapport.
GOOD example: "Mentioned his daughter's birthday is coming up"
GOOD example: "Patient and persistent despite repeated system failures — does not escalate"
Leave empty if nothing genuinely new to add.

### relatives
Create an entry for EVERY person the customer shops for or mentions by relationship.
ANY "for my wife / daughter / son / mother / friend" → create or update a relative entry.
- relation: "wife" / "daughter" / "son" / "mother" / "friend" / etc.
- name: if mentioned, else ""  (never write "unknown")
- age: if mentioned
- gender: infer from relation (wife → female, son → male)
- preferences: short English tags ["classic watches", "gold color", "size 38"]
- sizes: {"shoes": "38", "clothes": "S"}
- notes: only facts not captured elsewhere. Leave "" if nothing new.

---

## CORE RULES

### Preserve existing data
NEVER overwrite a non-empty field with an empty value. Only update when you have newer or more accurate information.

### No hallucination
Extract only what is directly evidenced in customer messages. Do not infer unstated motivations.

### Address fields
- personal.location: city + country only, no zip, full country name
- personal.delivery_address: full address verbatim, no commentary

### Consolidation
One entry per concept. New detail on existing topic → REPLACE, not append. No fact in more than one field.

---

## Schema
{
  "personal":     { "name": "", "gender": "", "phone": "", "company": "", "role": "", "location": "", "delivery_address": "" },
  "preferences":  { "communication_style": "", "best_contact_channel": "", "languages": [] },
  "sales": {
    "buying_persona": "",
    "current_needs": [],
    "buying_triggers": [],
    "pain_points": [],
    "objections_raised": [],
    "budget_range": "",
    "purchase_history": []
  },
  "relationship": { "status": "", "last_contact_date": "", "personal_details": [] },
  "relatives": [
    { "relation": "", "name": "", "age": "", "gender": "", "preferences": [], "sizes": {}, "notes": "" }
  ]
}"""


_REVIEWER_PROMPT = """You are a senior CRM reviewer. You will receive customer conversations and a draft profile JSON extracted from them.

Your job: review the draft against the conversations, identify every issue, then produce a corrected profile — all in one response.

Return a JSON object with exactly two keys:
- "critique": a plain-English string describing what was wrong or missing. If nothing is wrong, write "No issues found."
- "profile": the fully corrected profile JSON. If nothing needs changing, return the draft unchanged.

The expected schema is:
{
  "personal":     { "name": "", "gender": "", "phone": "", "company": "", "role": "", "location": "", "delivery_address": "" },
  "preferences":  { "communication_style": "", "best_contact_channel": "", "languages": [] },
  "sales": {
    "buying_persona": "",
    "current_needs": [],
    "buying_triggers": [],
    "pain_points": [],
    "objections_raised": [],
    "budget_range": "",
    "purchase_history": []
  },
  "relationship": { "status": "", "last_contact_date": "", "personal_details": [] },
  "relatives": [
    { "relation": "", "name": "", "age": "", "gender": "", "preferences": [], "sizes": {}, "notes": "" }
  ]
}
If the draft is missing any top-level key from this schema, add it with its default empty value.

## WHAT TO REVIEW

Only extract facts from CUSTOMER messages. Ignore assistant errors (wrong names, bot glitches, calling itself by the customer's name).

Check and fix every item below:

**Identity**
- personal.gender blank when name makes it obvious (Arabic: عطاء/محمد/أحمد = male; فاطمة/مريم/نور = female)
- personal.name taken from assistant greeting instead of customer's own message or checkout form
- personal.location containing a zip code or abbreviated country — must be "City, Country" only, full country name
- phone: ONE number, the most recent. Strip any concatenation ("+x,+y" → keep last)

**Language & preferences**
- languages: scan every customer message — if they write English AND Arabic, list both. Checkout-form Arabic ≠ primary language
- best_contact_channel filled when customer never stated a preference — must be ""
- communication_style inferred from checkout behavior — infer from writing style only

**Sales data**
- buying_persona contradicts relationship.status ("first-time buyer" when status is "returning customer")
- buying_triggers contain product lists instead of WHY/WHEN patterns — replace with behavioral patterns
- objections_raised empty when the customer expressed hesitation, price concern, or doubt about delivery/availability
- purchase_history includes cart additions or checkout failures — only explicit assistant confirmation counts. Trace chronologically; cleared-cart items were never purchased. Prices must match the cart at confirmation time
- current_needs lists needs already fulfilled by confirmed orders in purchase_history
- budget_range too narrow — must span ALL prices seen across the conversation
- pain_points merging different root causes — keep checkout failure and address re-entry as separate entries
- personal_details repeating info already in other fields (gender, location, buying behavior, relatives)

**Relatives**
- relatives empty when customer mentioned shopping for a family member or friend
- relatives[].name set to the word "unknown" — must be ""

**Delivery & address**
- delivery_address contains commentary — must be address fields only, no notes
- delivery_address accumulated from multiple submissions — use latest complete one only

**Structure**
- relationship.status not in allowed set: "new lead" / "warm prospect" / "active buyer" / "returning customer" / "negotiating" / "closed"
- Any field written in Arabic that should be in English (except name and delivery_address)

Hard constraints on the corrected profile:
- Never blank a non-empty field unless it was factually wrong
- Never fill best_contact_channel unless the customer stated it explicitly
- Never write "unknown" as a relative's name — use ""
- Never put a zip code in personal.location
- All fields except personal.name and personal.delivery_address must be in English"""


_COMPRESSOR_PROMPT = """You are a CRM profile compressor. You will receive a detailed profile JSON. Your job is to produce a lean, token-efficient version of it that retains every actionable fact but eliminates all bloat.

This profile will be injected into other AI agents as context, so size directly impacts cost and quality. Be ruthless about compression.

Return ONLY valid JSON — same schema, no markdown, no commentary.

## COMPRESSION RULES

### Newer wins, older loses
If the profile contains information that has been superseded (e.g. an old address replaced by a newer one, a resolved pain point, a need that was fulfilled), keep only the latest state. Do not accumulate history where the current state is what matters.

### Strings: cut to the bone
- Every string field must be as short as possible without losing meaning.
- Remove filler words: "the customer", "it is worth noting", "based on the conversation", "shows that".
- Use fragments and tags, not full sentences, where meaning is preserved.
- BAD: "Customer had to re-enter full delivery address multiple times because the system did not retain it between sessions"
- GOOD: "Delivery address not saved between sessions — re-entered 5×"

### Arrays: merge and cap
- Merge array entries that describe the SAME root cause into one entry.
- pain_points: max 4 entries. NEVER merge pain points that have different root causes — a checkout validation failure and a missing address persistence are two different problems and must stay as separate entries. Only merge entries that are genuinely about the same issue.
- buying_triggers: max 3 entries.
- current_needs: max 5 entries. One line per need, no redundancy.
- purchase_history: keep all confirmed orders but shorten each to "Item – price".
- personal_details: max 3 entries. Drop anything already captured in another field.
- relatives[].preferences: max 4 tags per relative.

### buying_persona: max 2 sentences
Compress without losing the essential character of this buyer.

### delivery_address: address fields only, keep full, do not truncate
This is used operationally for shipping — it must contain ONLY address data (street, building, district, city, country, zip).
If it contains any commentary or notes (e.g. "re-entered multiple times", "system error"), strip that text out completely.
Never shorten the actual address fields.

### Do NOT invent
- Never fill a field that was empty in the input unless you are shortening a non-empty value.
- best_contact_channel: if empty in input, leave empty. Never infer it from the conversation medium.
- personal.phone: if the input has multiple numbers concatenated (e.g. "+x,+y"), reduce to the last number only.
- relatives[].name: if unknown, use "" — never write the word "unknown".

### Do NOT drop or blank
- personal.name, personal.phone, personal.gender, personal.location, personal.delivery_address — if any of these are non-empty in the input, they MUST be non-empty in the output
- personal.gender: never blank it out. If the input has "male" or "female", keep it exactly as-is
- Any confirmed purchase in purchase_history
- Any active current_need
- relatives entries
- Pain points — especially those about address persistence and checkout failures, which are operationally important

### personal.location format
- personal.location must be ONLY city + country — e.g. "Riyadh, Saudi Arabia"
- Never put a zip/postal code in personal.location — that belongs in delivery_address only
- Never abbreviate the country name (use "Saudi Arabia" not "SA")"""


def _build_conversation_text(conversations: list[ConversationRecord]) -> str:
    parts: list[str] = []
    for rec in conversations:
        for msg in rec.messages:
            parts.append(f"{msg.role.upper()}: {msg.content}")
        parts.append("---")
    return "\n".join(parts)


def _build_user_message(profile: UserProfile, conversations: list[ConversationRecord]) -> str:
    profile_dict = profile.model_dump(exclude={"user_id", "created_at", "updated_at"})
    return (
        f"CURRENT PROFILE:\n{json.dumps(profile_dict, indent=2)}\n\n"
        f"RECENT CONVERSATIONS:\n{_build_conversation_text(conversations)}"
    )


async def _call_llm(
    client: AsyncOpenAI,
    model: str,
    system: str,
    user: str,
    *,
    json_mode: bool = True,
) -> tuple[str, object]:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        **({"response_format": {"type": "json_object"}} if json_mode else {}),
    )
    return response.choices[0].message.content, response.usage


def _safe_merge(updated_data: dict, profile: UserProfile) -> UserProfile:
    """Merge LLM output into the profile with null-safe fallbacks."""
    def _dict(key: str, fallback: dict) -> dict:
        val = updated_data.get(key)
        return val if isinstance(val, dict) else fallback

    def _list(key: str, fallback: list) -> list:
        val = updated_data.get(key)
        return val if isinstance(val, list) else fallback

    merged = {
        "user_id": profile.user_id,
        "created_at": profile.created_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "personal": _dict("personal", profile.personal.model_dump()),
        "preferences": _dict("preferences", profile.preferences.model_dump()),
        "sales": _dict("sales", profile.sales.model_dump()),
        "relationship": _dict("relationship", profile.relationship.model_dump()),
        "relatives": _list("relatives", [r.model_dump() for r in profile.relatives]),
    }
    return UserProfile.model_validate(merged)


async def extract_and_update_profile(
    profile: UserProfile,
    conversations: list[ConversationRecord],
    *,
    account_id: str | None = None,
    project_id: str | None = None,
    contact_id: str | None = None,
) -> UserProfile:
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )

    conv_text = _build_conversation_text(conversations)
    usages = []

    # ── Tier 1: extract draft profile ────────────────────────────────────────
    tier1_json, u1 = await _call_llm(
        client, settings.groq_model, _SYSTEM_PROMPT,
        _build_user_message(profile, conversations),
    )
    usages.append(u1)
    logger.debug("Tier 1 extraction done")

    # ── Tier 2: review + correct in one shot ─────────────────────────────────
    try:
        review_json, u2 = await _call_llm(
            client, settings.groq_model, _REVIEWER_PROMPT,
            f"CONVERSATIONS:\n{conv_text}\n\nDRAFT PROFILE:\n{tier1_json}",
        )
        usages.append(u2)
        review_data = json.loads(review_json)
        logger.debug("Tier 2 review critique: %s", review_data.get("critique", ""))
        final_data = review_data.get("profile") or json.loads(tier1_json)
    except Exception:
        logger.exception("Tier 2 review failed — using tier 1 output")
        final_data = json.loads(tier1_json)

    # ── Log combined token usage ──────────────────────────────────────────────
    if account_id and project_id:
        from app import supabase_client as db
        total_prompt = sum(u.prompt_tokens for u in usages if u)
        total_completion = sum(u.completion_tokens for u in usages if u)
        await db.log_llm_usage(
            account_id=account_id,
            project_id=project_id,
            contact_id=contact_id,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            total_tokens=total_prompt + total_completion,
            model=settings.groq_model,
        )

    return _safe_merge(final_data, profile)


async def compress_profile(
    profile: UserProfile,
    *,
    account_id: str | None = None,
    project_id: str | None = None,
    contact_id: str | None = None,
) -> UserProfile:
    """Run compression (tier 3) on an already-extracted profile. Called manually or on schedule."""
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )

    profile_json = json.dumps(
        profile.model_dump(exclude={"user_id", "created_at", "updated_at"}),
        indent=2, ensure_ascii=False,
    )

    compressed_json, usage = await _call_llm(
        client, settings.groq_model, _COMPRESSOR_PROMPT, profile_json,
    )

    if account_id and project_id and usage:
        from app import supabase_client as db
        await db.log_llm_usage(
            account_id=account_id,
            project_id=project_id,
            contact_id=contact_id,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            model=settings.groq_model,
        )

    try:
        compressed_data = json.loads(compressed_json)
    except json.JSONDecodeError:
        logger.exception("Compression returned invalid JSON — keeping original")
        return profile

    return _safe_merge(compressed_data, profile)
