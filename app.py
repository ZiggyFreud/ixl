import os
import re
import json
import random
import anthropic
import chromadb
from chromadb.config import Settings
from flask import Flask, request, jsonify
from flask_cors import CORS
from voyageai import Client as VoyageClient

app = Flask(__name__)
CORS(app)

# ── Clients ──────────────────────────────────────────────────────────────────
anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
voyage_client = VoyageClient(api_key=os.environ.get("VOYAGE_API_KEY"))

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_PATH = os.environ.get("CHROMA_PATH", "/data/chroma_db")
chroma_client = chromadb.PersistentClient(
    path=CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False)
)
collection = chroma_client.get_or_create_collection(name="ixl")

# ── Random responses ──────────────────────────────────────────────────────────
with open("random_responses.json", "r") as f:
    RESPONSES = json.load(f)

def pick(category):
    return random.choice(RESPONSES.get(category, [""]))

# ── Helpers ───────────────────────────────────────────────────────────────────
ADMIN_PREFIX = os.environ.get("ADMIN_TOKEN", "admin332445")

def clean_response(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def embed(texts):
    result = voyage_client.embed(texts, model="voyage-3")
    return result.embeddings

def retrieve(query, n=4):
    q_emb = embed([query])[0]
    results = collection.query(query_embeddings=[q_emb], n_results=n)
    docs = results["documents"][0] if results["documents"] else []
    return "\n\n".join(docs)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are the virtual assistant for IXL Public Adjuster, a licensed public adjusting firm serving homeowners, business owners, and commercial property clients throughout New Jersey and the surrounding region.

Your role is to:
- Answer questions about IXL's services, the claims process, and what a public adjuster does
- Educate visitors about their rights as policyholders
- Encourage visitors to reach out for a free, no-obligation claim review
- Capture lead information (name, phone or email, and type of claim) when someone is ready to get started

Contact information to share when relevant:
- Office: (609) 246-0616
- Cell: (609) 369-6630
- Email: admin@ixlpa.com

Key facts about IXL:
- IXL represents policyholders — never the insurance company
- 75+ years of combined industry experience
- Contingency fee basis: no upfront cost, IXL only gets paid when you do
- Services: Claims Management & Filing, Damage Assessment, Negotiation, Dispute Resolution, Business-Specific Services
- Types of claims handled: fire/smoke, water/flood, wind/storm/hurricane, roof, mold/structural, theft/vandalism, business interruption, catastrophic/total loss
- Can reopen denied or underpaid claims in many cases
- Serves residential and commercial clients

IMPORTANT GUIDELINES:
- Never provide specific legal advice or interpret specific insurance policy language for the user
- Never guarantee a specific outcome or settlement amount
- If someone asks about their specific policy coverage, direct them to contact IXL directly for a free review
- Always be warm, empathetic, and professional — visitors are often dealing with stressful property damage situations
- Keep answers concise and plain — no bullet points, no markdown formatting
- If you don't know something, say so and encourage the visitor to contact IXL directly

Use the context below (retrieved from IXL's website) to answer questions accurately.
"""

# ── Admin handler ─────────────────────────────────────────────────────────────
def handle_admin(message):
    msg = message[len(ADMIN_PREFIX):].strip()

    if msg.upper().startswith("ADD:"):
        content = msg[4:].strip()
        if not content:
            return "ADD failed: no content provided."
        doc_id = f"admin_{random.randint(100000, 999999)}"
        emb = embed([content])[0]
        collection.add(documents=[content], embeddings=[emb], ids=[doc_id],
                       metadatas=[{"source": "admin"}])
        return f"Added to knowledge base. ID: {doc_id}"

    if msg.upper().startswith("DELETE:"):
        doc_id = msg[7:].strip()
        try:
            collection.delete(ids=[doc_id])
            return f"Deleted document: {doc_id}"
        except Exception as e:
            return f"Delete failed: {str(e)}"

    if msg.upper() == "LIST":
        results = collection.get(where={"source": "admin"})
        if not results["ids"]:
            return "No admin-added documents found."
        lines = [f"{i}: {d[:120]}..." for i, d in zip(results["ids"], results["documents"])]
        return "Admin documents:\n" + "\n".join(lines)

    return "Admin commands: ADD: <text> | DELETE: <id> | LIST"

# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    if not user_message:
        return jsonify({"response": "I didn't catch that — could you try again?"})

    # Greetings
    lower = user_message.lower()
    if lower in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]:
        return jsonify({"response": pick("greetings")})

    if lower in ["thanks", "thank you", "thx", "ty"]:
        return jsonify({"response": pick("thank_yous")})

    # Admin
    if user_message.startswith(ADMIN_PREFIX):
        return jsonify({"response": handle_admin(user_message)})

    # RAG
    context = retrieve(user_message)

    messages = []
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    system_with_context = SYSTEM_PROMPT
    if context:
        system_with_context += f"\n\nRELEVANT CONTEXT:\n{context}"

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=system_with_context,
            messages=messages
        )
        reply = clean_response(response.content[0].text)
    except Exception as e:
        reply = "I'm having trouble connecting right now. Please contact us directly at (609) 246-0616 or admin@ixlpa.com."

    return jsonify({"response": reply})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=False)