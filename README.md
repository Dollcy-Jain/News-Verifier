# 🔍 News Fact-Checking uAgent

An autonomous verification agent built on Fetch.ai's [uAgents](https://fetch.ai/) framework and deployable via [Agentverse](https://agentverse.ai/). This agent ingests user claims, searches live news and dedicated fact-checking indexes via the Tavily Search API, performs relevance filtering and detail matching, and responds with a structured authenticity verdict.

---

## ✨ Features

- **Standard Chat Protocol Support:** Uses `uagents_core.contrib.protocols.chat` (`ChatMessage`, `TextContent`, `ChatAcknowledgement`) for seamless integration with Agentverse chat UI and other uAgents.
- **Dual-Stream Search:** Queries Tavily both for breaking news coverage and dedicated fact-check reporting concurrently.
- **Smart Heuristics & Filtering:**
  - **Stop-word & Filler Removal:** Distills natural-language prompts down to core subjects.
  - **Keyword Match Scoring:** Discards off-topic or noisy articles prior to analysis.
  - **Specific Detail Verification:** Checks for specific numbers, dates, and capitalized entities to detect exaggerated or context-lacking claims.
- **Intent Awareness:** Intercepts meta-questions (e.g., asking what verdicts mean) and capability queries (e.g., search timeframe limits) without consuming search API calls.
- **Structured Verdict Taxonomy:**
  - **Real:** Core claims and specific figures/details are corroborated by credible sources.
  - **Fake:** Credible sources explicitly debunk the claim using refutation markers.
  - **Partially Real:** The broad event occurred, but figures/details conflict or are unverified.
  - **Unverified:** No credible matching sources could be retrieved.

---

## 🏗️ Architecture

```text
User / Agentverse Chat
       │
       ▼
[ChatMessage Received]
       │
       ├──> Is Meta/Taxonomy Question? ──> Return Taxonomy Guide
       ├──> Is Capability Question?     ──> Return Scope & Limits
       ├──> Insufficient Keywords?     ──> Request User Clarification
       │
       ▼
[Execute Tavily Search Queries]
  ├── News Endpoint
  └── Fact-Check Endpoint
       │
       ▼
[Verdict Analyst]
  ├── Filter Unrelated Articles
  ├── Check Specific Details (Dates, Figures, Entities)
  └── Evaluate Stance (Real / Fake / Partial Markers)
       │
       ▼
[Structured Response with Citations]
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A [Tavily Search API](https://tavily.com/) key

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/news-fact-checker-uagent.git
cd news-fact-checker-uagent
```

### 2. Set Up a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Dependencies (`requirements.txt`)

Create a `requirements.txt` file with the following:

```text
uagents
uagents-core
httpx
```

### 4. Configure Environment Variables

Set your Tavily API key:

```bash
# Linux / macOS
export TAVILY_API_KEY="tvly-YOUR_ACTUAL_API_KEY"

# Windows (Command Prompt)
set TAVILY_API_KEY="tvly-YOUR_ACTUAL_API_KEY"

# Windows (PowerShell)
$env:TAVILY_API_KEY="tvly-YOUR_ACTUAL_API_KEY"
```

---

## 💻 Running the Agent

### Locally
Run the agent script directly:

```bash
python agent.py
```

### On Agentverse
1. Log in to [Agentverse.ai](https://agentverse.ai/).
2. Create a new **Hosted Agent**.
3. Paste the contents of `main.py` into the editor.
4. Set your `TAVILY_API_KEY` under the agent's **Secrets / Environment Variables** tab.
5. Click **Start** to deploy and test directly through the Agentverse Chat interface.

---

## 💬 Usage Examples

### 1. Verifying a Claim
> **User:** "Did NASA launch the Europa Clipper mission in October 2024?"  
> **Agent:**  
> **Verdict:** Real  
> **Explanation:** Based on the retrieved sources:  
> - **nasa.gov** supports the core event or claim.  
> **Relevant Sources:**  
> - `https://www.nasa.gov/...`

### 2. Vague or Ambiguous Claim
> **User:** "Is it true?"  
> **Agent:** "I couldn't identify a specific, verifiable claim in your message. Could you please clarify and provide the specific statement, event, or news item you are referring to?"

### 3. Asking About Taxonomy
> **User:** "What does Partially Real mean?"  
> **Agent:** Returns definitions for *Real*, *Fake*, *Partially Real*, and *Unverified*.

---
