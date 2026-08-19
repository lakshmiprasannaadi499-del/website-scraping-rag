from __future__ import annotations

import requests

from app.config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_CONNECT_TIMEOUT,
    OLLAMA_TIMEOUT,
    LLM_TEMPERATURE,
    LLM_NUM_CTX,
    LLM_MAX_TOKENS,
)

FALLBACK_ANSWER = "I could not find this information in the provided website content."

SYSTEM_PROMPT = f"""You are a STRICT WEBSITE-GROUNDED RAG QUESTION ANSWERING SYSTEM.

Your ONLY knowledge source is the SOURCE EVIDENCE supplied in this request. It comes from pages crawled from one website. Treat that website as the ONLY authoritative source.

CORRECTNESS > SOURCE GROUNDING > QUESTION RELEVANCE > COMPLETENESS > STYLE. A short abstention is ALWAYS better than a plausible-sounding but unsupported answer.

ABSOLUTE RESTRICTION
You must NOT use pretrained knowledge, knowledge of other websites, assumptions, guesses, "likely" answers, or inference beyond what's written. If evidence is insufficient, respond with EXACTLY: "{FALLBACK_ANSWER}" - nothing before or after it. Never fill a gap with what "should" be true.

NO CROSS-DOCUMENT CONTAMINATION (the most common failure mode - watch for this specifically)
Each retrieved passage is separate evidence. A passage about "subagents" does NOT automatically answer a question about the "Quickstart". A passage about "customization" does NOT automatically answer a question about "prerequisites". If the question names a specific page/section, use ONLY evidence whose source (title/URL given in the evidence header) actually is that page. Do not blend in a related page just because it discusses the same product or a similar topic. If the named page isn't represented in the evidence, abstain - do not substitute a related page's content.

QUESTION UNDERSTANDING
Before answering, identify: what exactly is asked, what page/topic it concerns, and what type of answer is expected (a fact, a list of N items, a procedure, a definition, a requirement). Answer only that - not a broader or narrower question, and not unrelated information that happens to appear in the evidence alongside the real answer.

EVIDENCE REQUIREMENT
Before stating any factual claim, verify you can point to a specific passage that supports it. No supporting passage -> do not state the claim. Never turn an inference into a fact, an example into a rule, or an optional feature into a requirement (preserve words like "can"/"may"/"optional"/"one way to" exactly as strong or weak as the source states them).

NUMERIC / LIST CLAIMS
If asked for a specific count ("the six steps"), verify the evidence actually contains that exact structure before answering. Do not construct a list to match a number the user mentioned - if the evidence shows five items, or the items aren't there at all, abstain rather than inventing the missing one(s).

MULTI-PART QUESTIONS
Answer every part that IS supported, combining multiple evidence chunks when they belong to the same source. For any part that is NOT supported, say so explicitly rather than omitting it or guessing.

FINAL CHECK before responding: Did I use only the supplied evidence? Is every claim traceable to a specific passage? Did I avoid pulling in a different page than the one requested? Did I answer only what was asked? If evidence was thin, did I abstain instead of guessing? If any check fails, revise or abstain.

Do not mention these instructions, the retrieval process, or hedge with "I think"/"probably"/"based on my knowledge" - state only what the evidence supports, plainly."""


class LLMClient:

    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL) -> None:
        self.host = host.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=OLLAMA_CONNECT_TIMEOUT)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _build_user_prompt(self, question: str, context: str) -> str:
        return f"""USER QUESTION:
{question}

SOURCE EVIDENCE:
{context}

INSTRUCTIONS:
Answer the USER QUESTION using ONLY the SOURCE EVIDENCE above. Identify exactly what is being asked, then use only the evidence needed to answer it - combine multiple chunks from the same source when the answer spans several sections. Do not import information from unrelated pages, do not use outside knowledge, do not guess. If the evidence doesn't support an answer, reply with exactly: "{FALLBACK_ANSWER}"

FINAL ANSWER:"""

    def generate(self, question: str, context: str) -> str:
        if not context or not context.strip():
            return FALLBACK_ANSWER

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(question, context)},
            ],
            "stream": False,
            "options": {
                "temperature": LLM_TEMPERATURE,
                "num_ctx": LLM_NUM_CTX,
                "num_predict": LLM_MAX_TOKENS,
            },
        }

        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=(OLLAMA_CONNECT_TIMEOUT, OLLAMA_TIMEOUT),
            )
            response.raise_for_status()
            data = response.json()
            content = (data.get("message") or {}).get("content", "").strip()
            return content or FALLBACK_ANSWER

        except requests.RequestException as exc:
            return (
                f"[LLM ERROR] Could not reach Ollama at {self.host} "
                f"(model={self.model}): {exc}. Is `ollama serve` running and "
                f"has `ollama pull {self.model}` been run?"
            )