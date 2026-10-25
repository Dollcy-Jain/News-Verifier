import os
import re
import httpx
from datetime import datetime, timezone
from uuid import uuid4
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    chat_protocol_spec, ChatMessage, ChatAcknowledgement, TextContent
)

# --- 1. AGENT INITIALIZATION ---
agent = Agent()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "tvly-YOUR_API_KEY")
TAVILY_API_URL = "https://api.tavily.com/search"

# --- 2. RESEARCH & ANALYSIS FUNCTIONS ---
async def evidence_researcher(claim: str):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TAVILY_API_URL, 
                json={"api_key": TAVILY_API_KEY, "query": claim, "topic": "news", "max_results": 4},
                timeout=10.0
            )
            return resp.json().get("results", [])
    except Exception:
        return []

async def fact_check_researcher(claim: str):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TAVILY_API_URL, 
                json={"api_key": TAVILY_API_KEY, "query": f"{claim} fact check", "search_depth": "basic", "max_results": 3},
                timeout=10.0
            )
            return resp.json().get("results", [])
    except Exception:
        return []

def extract_keywords(claim: str) -> list:
    """Removes stop-words and conversational filler to isolate the core subject/claim for relevance scoring."""
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "did", "do", "does", "can", "could", "would", "should", 
        "of", "to", "in", "for", "with", "on", "at", "by", "from", "about", "as", "into", "like", "through", 
        "after", "over", "between", "out", "against", "during", "without", "before", "under", "around", "among", 
        "how", "what", "when", "where", "why", "who", "which", "this", "that", "these", "those", "it", "its", 
        "they", "their", "them", "he", "him", "his", "she", "her", "we", "us", "our", "you", "your", "my", "mine", "will",
        "be", "awarded", "has", "been", "have", "had", "not",
        # Added conversational & generic fact-checking words so they don't trigger false positives
        "fact", "check", "verify", "claim", "news", "true", "false", "real", "fake", "tell", "me", "if", "whether",
        "please", "article", "post", "tweet", "video", "information", "source", "story"
    }
    words = re.findall(r'\b[a-zA-Z0-9]+\b', claim.lower())
    return [w for w in words if w not in stop_words and len(w) > 2]

def extract_specifics(claim: str) -> list:
    """Extracts highly specific verifiable details like numbers, dates, or capitalized entities."""
    numbers = re.findall(r'\b\d+(?:[.,]\d+)?\b', claim)
    entities = re.findall(r'\b[A-Z][a-z]+\b', claim)
    return list(set(numbers + entities))

def is_meta_question(claim: str) -> bool:
    """Detects if the user is asking about the agent's verdict taxonomy."""
    claim_lower = claim.lower()
    meta_prompts = ["what does", "how do", "explain", "what is", "meaning of"]
    taxonomy_terms = ["partially real", "unverified", "fake", "real", "verdict"]
    
    is_question = any(claim_lower.startswith(p) for p in meta_prompts) or "?" in claim
    is_about_taxonomy = any(t in claim_lower for t in taxonomy_terms)
    
    return is_question and is_about_taxonomy

def is_capability_question(claim: str) -> bool:
    """Detects if the user is asking about the agent's capabilities or timeframe limits."""
    claim_lower = claim.lower()
    capability_phrases = [
        "can you", "are you able to", "how far back", "older events", 
        "past events", "what can you", "limitations", "your limits"
    ]
    action_words = ["check", "verify", "search", "fact", "do", "find", "handle"]
    
    has_capability = any(p in claim_lower for p in capability_phrases)
    has_action = any(a in claim_lower for a in action_words)
    
    return has_capability and has_action

def get_meta_response() -> str:
    return (
        "**Verdict Taxonomy Explained:**\n"
        "- **Real:** Retrieved sources confirm the core claim and its specific details with official or factual evidence.\n"
        "- **Fake:** Retrieved sources explicitly refute the claim using markers like 'debunked', 'hoax', or 'false'.\n"
        "- **Partially Real:** Retrieved sources confirm the core subject or event exists, but specific details (like a quoted figure, date, or secondary claim) cannot be verified or are contradicted.\n"
        "- **Unverified:** No highly relevant sources could be found that match the core subject, or sources discuss the topic without reaching a factual conclusion."
    )

def get_capability_response() -> str:
    return (
        "I can verify news claims and check their authenticity. While older established events "
        "can often be fact-checked, my news search capability is most effective for recent events "
        "(typically within the last 90 days). What specific claim would you like me to check?"
    )

def verdict_analyst(claim: str, keywords: list, evidence_results: list, fc_results: list):
    valid_sources = []
    excluded_sources = []
    specifics = extract_specifics(claim)

    for res in (evidence_results + fc_results):
        content_lower = res.get('content', '').lower()
        title_lower = res.get('title', '').lower()
        combined = content_lower + " " + title_lower
        
        match_count = sum(1 for kw in keywords if kw in combined)
        
        if (match_count / len(keywords)) >= 0.3 or match_count >= 2:
            valid_sources.append(res)
        else:
            excluded_sources.append({"url": res.get('url'), "reason": f"Only matched {match_count} keyword(s), excluding as unrelated story."})

    if not valid_sources:
        return "Unverified", "I searched for information regarding your claim, but could not find any highly relevant sources.", [], excluded_sources

    fake_markers = ["hoax", "debunked", "fake news", "baseless", "no evidence", "myth", "false", "untrue", "scam"]
    real_markers = ["confirmed", "announced", "awarded", "official", "demonstrated", "is true", "won"]
    partial_markers = ["misleading", "lacks context", "exaggerated", "partially", "mixed"]

    source_explanations = []
    has_fake, has_real, has_partial = False, False, False
    missing_specifics = set(specifics)

    for res in valid_sources:
        content = res.get('content', '').lower()
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', res.get('url', ''))
        domain = domain_match.group(1) if domain_match else "A source"
        
        for spec in list(missing_specifics):
            if spec.lower() in content:
                missing_specifics.remove(spec)

        if any(m in content for m in fake_markers):
            stance = "refutes the claim."
            has_fake = True
        elif any(m in content for m in partial_markers):
            stance = "indicates the claim is misleading or lacks key context."
            has_partial = True
        elif any(m in content for m in real_markers):
            stance = "supports the core event or claim."
            has_real = True
        else:
            stance = "discusses the topic but lacks a definitive factual conclusion."

        if not any(domain in s for s in source_explanations):
            source_explanations.append(f"- **{domain}** {stance}")

    explanation_parts = ["Based on the retrieved sources:\n" + "\n".join(source_explanations)]

    if has_real and has_fake:
        verdict = "Partially Real"
        explanation_parts.append("\n**Breakdown:** Sources show conflicting information, confirming some aspects while explicitly debunking others.")
    elif has_fake:
        verdict = "Fake"
    elif has_partial:
        verdict = "Partially Real"
    elif has_real:
        if missing_specifics:
            verdict = "Partially Real"
            explanation_parts.append(f"\n**Breakdown:** The core event is supported, but retrieved sources do not confirm the following specific details from your claim: {', '.join(missing_specifics)}.")
        else:
            verdict = "Real"
    else:
        verdict = "Unverified"

    explanation = "\n".join(explanation_parts)
    return verdict, explanation, valid_sources, excluded_sources

# --- 3. CHAT PROTOCOL COORDINATOR ---
chat_proto = Protocol(spec=chat_protocol_spec)

def create_text_chat(text: str) -> ChatMessage:
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=[TextContent(type="text", text=text)])

@chat_proto.on_message(model=ChatMessage)
async def verify_claim_handler(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))

    claim = next((item.text for item in msg.content if isinstance(item, TextContent)), "")
    if not claim: return

    ctx.logger.info(f"📱 MESSAGE RECEIVED: '{claim}'")
    
    # 1. Intent Check: Meta/Taxonomy Questions
    if is_meta_question(claim):
        await ctx.send(sender, create_text_chat(get_meta_response()))
        return

    # 2. Intent Check: Capability/Timeframe Questions
    if is_capability_question(claim):
        await ctx.send(sender, create_text_chat(get_capability_response()))
        return

    # 3. Keyword Extraction & Clarifying Question for vague inputs
    keywords = extract_keywords(claim)
    if len(keywords) < 2:
        await ctx.send(sender, create_text_chat(
            "I couldn't identify a specific, verifiable claim in your message. "
            "Could you please clarify and provide the specific statement, event, or news item you are referring to?"
        ))
        return

    # 4. Proceed to search ONLY if an identified claim subject exists
    evidence = await evidence_researcher(claim)
    fcs = await fact_check_researcher(claim)
    
    verdict, explanation, valid_sources, excluded_sources = verdict_analyst(claim, keywords, evidence, fcs)

    response_text = f"**Verdict:** {verdict}\n\n**Explanation:**\n{explanation}"
    
    if valid_sources and verdict != "Unverified":
        unique_valid = {res.get("url"): res for res in valid_sources}.values()
        response_text += "\n\n**Relevant Sources:**\n" + "\n".join([f"- {res.get('url')}" for list_idx, res in enumerate(unique_valid) if list_idx < 3])
            
    if excluded_sources:
        unique_excluded = {ex["url"]: ex for ex in excluded_sources}.values()
        response_text += "\n\n**Excluded Sources:**\n" + "\n".join([f"- {ex['url']} ({ex['reason']})" for list_idx, ex in enumerate(unique_excluded) if list_idx < 2])

    await ctx.send(sender, create_text_chat(response_text))

@chat_proto.on_message(model=ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement): pass

agent.include(chat_proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()