from __future__ import annotations

# ============================================================
# WEBRAG STUDIO
# RAGAS 0.4.3 EVALUATION
#
# Current setup:
#   Python       : 3.12
#   RAGAS        : 0.4.3
#   LLM          : Ollama qwen3:8b
#   Embeddings   : Ollama nomic-embed-text
#
# IMPORTANT:
# We DO NOT use ragas.evaluate().
#
# Ragas 0.4.x collection metrics are evaluated using:
#
#     await metric.ascore(...)
#
# ============================================================


from __future__ import annotations

import asyncio
import importlib
import json
import math
import os
import sys
import traceback
import types
from pathlib import Path


# ============================================================
# PATH SETUP
# ============================================================

# This file is:
#
# website-scraping/
# ├── app/
# ├── Evaluation/
# │   └── evaluate_ragas.py
# └── streamlit_app.py
#
# Therefore parents[1] = website-scraping

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


# ============================================================
# ENVIRONMENT
# ============================================================

# Load .env if python-dotenv is available.
try:
    from dotenv import load_dotenv

    load_dotenv(
        PROJECT_ROOT / ".env"
    )

except Exception:
    pass


# ============================================================
# PATHS
# ============================================================

EVALUATION_DIR = (
    PROJECT_ROOT / "Evaluation"
)

QUESTIONS_FILE = (
    EVALUATION_DIR
    / "test_questions.json"
)

RESULTS_DIR = (
    EVALUATION_DIR
    / "results"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# CONFIG
# ============================================================

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://127.0.0.1:11434",
).rstrip("/")


OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:8b",
)


# IMPORTANT:
# This is the embedding model used ONLY by RAGAS.
#
# Your RAG application can continue using:
#
# BAAI/bge-small-en-v1.5
#
# RAGAS will use Ollama's:
#
# nomic-embed-text

RAGAS_EMBEDDING_MODEL = os.getenv(
    "RAGAS_EMBEDDING_MODEL",
    "nomic-embed-text",
)


# ============================================================
# DISPLAY
# ============================================================

print()
print("=" * 78)
print("WEBRAG RAGAS EVALUATION")
print("=" * 78)

print(
    f"Python          : {sys.version.split()[0]}"
)

print(
    f"Ollama host     : {OLLAMA_HOST}"
)

print(
    f"Evaluator model : {OLLAMA_MODEL}"
)

print(
    f"Embedding model : {RAGAS_EMBEDDING_MODEL}"
)

print(
    f"Questions file  : {QUESTIONS_FILE}"
)

print(
    f"Results folder  : {RESULTS_DIR}"
)

print("=" * 78)


# ============================================================
# VERTEXAI COMPATIBILITY
# ============================================================
#
# Ragas 0.4.3 imports VertexAI classes while importing its LLM
# module, even though YOUR evaluation uses Ollama.
#
# If the real VertexAI integration exists, nothing is changed.
#
# If it doesn't exist, create lightweight compatibility modules
# so Ragas can finish importing.
#
# This DOES NOT use VertexAI for evaluation.
# ============================================================


def ensure_vertexai_import_compatibility() -> None:

    module_name = (
        "langchain_community.chat_models.vertexai"
    )

    try:

        importlib.import_module(
            module_name
        )

        print(
            "VertexAI compatibility : available"
        )

        return

    except ModuleNotFoundError:

        pass

    print(
        "VertexAI integration is not available."
    )

    print(
        "Installing a lightweight compatibility stub."
    )

    # --------------------------------------------------------
    # Ensure parent package exists
    # --------------------------------------------------------

    try:

        import langchain_community

    except Exception:

        return

    # --------------------------------------------------------
    # chat_models package
    # --------------------------------------------------------

    chat_models_name = (
        "langchain_community.chat_models"
    )

    try:

        chat_models = importlib.import_module(
            chat_models_name
        )

    except Exception:

        chat_models = types.ModuleType(
            chat_models_name
        )

        chat_models.__path__ = []

        sys.modules[
            chat_models_name
        ] = chat_models

        setattr(
            langchain_community,
            "chat_models",
            chat_models,
        )

    # --------------------------------------------------------
    # vertexai module
    # --------------------------------------------------------

    vertex_module = types.ModuleType(
        module_name
    )

    class ChatVertexAI:
        """
        Compatibility placeholder.

        This evaluation does NOT use VertexAI.
        """

        def __init__(
            self,
            *args,
            **kwargs,
        ):

            raise RuntimeError(
                "ChatVertexAI is not used by this "
                "WebRAG evaluation. "
                "Ollama qwen3:8b is the evaluator."
            )

    vertex_module.ChatVertexAI = (
        ChatVertexAI
    )

    sys.modules[
        module_name
    ] = vertex_module

    setattr(
        chat_models,
        "vertexai",
        vertex_module,
    )

    # --------------------------------------------------------
    # llms.vertexai
    # --------------------------------------------------------

    llms_name = (
        "langchain_community.llms.vertexai"
    )

    try:

        importlib.import_module(
            llms_name
        )

    except ModuleNotFoundError:

        try:

            llms = importlib.import_module(
                "langchain_community.llms"
            )

        except Exception:

            llms = types.ModuleType(
                "langchain_community.llms"
            )

            llms.__path__ = []

            sys.modules[
                "langchain_community.llms"
            ] = llms

        llm_vertex_module = types.ModuleType(
            llms_name
        )

        class VertexAI:
            """
            Compatibility placeholder.

            This evaluation does NOT use VertexAI.
            """

            def __init__(
                self,
                *args,
                **kwargs,
            ):

                raise RuntimeError(
                    "VertexAI is not used by this "
                    "WebRAG evaluation. "
                    "Ollama qwen3:8b is the evaluator."
                )

        llm_vertex_module.VertexAI = (
            VertexAI
        )

        sys.modules[
            llms_name
        ] = llm_vertex_module

        setattr(
            llms,
            "vertexai",
            llm_vertex_module,
        )

    print(
        "VertexAI compatibility : stub installed"
    )


# ============================================================
# LOAD RAGAS
# ============================================================


def load_ragas():

    print()
    print("=" * 78)
    print("LOADING RAGAS")
    print("=" * 78)

    ensure_vertexai_import_compatibility()

    try:

        import ragas

        print(
            f"Ragas version : "
            f"{getattr(ragas, '__version__', 'unknown')}"
        )

    except Exception as exc:

        print()
        print(
            "RAGAS IMPORT FAILED"
        )

        print(
            repr(exc)
        )

        traceback.print_exc()

        raise

    # --------------------------------------------------------
    # Ragas 0.4.3 dataset
    # --------------------------------------------------------

    try:

        from ragas import (
            EvaluationDataset,
            SingleTurnSample,
        )

    except Exception:

        from ragas.dataset_schema import (
            EvaluationDataset,
            SingleTurnSample,
        )

    # --------------------------------------------------------
    # Modern collection metrics
    # --------------------------------------------------------

    from ragas.metrics.collections import (
        Faithfulness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
    )

    # --------------------------------------------------------
    # Ragas factories
    # --------------------------------------------------------

    from ragas.llms import (
        llm_factory,
    )

    from ragas.embeddings import (
        embedding_factory,
    )

    return {
        "ragas": ragas,
        "EvaluationDataset": EvaluationDataset,
        "SingleTurnSample": SingleTurnSample,
        "Faithfulness": Faithfulness,
        "AnswerRelevancy": AnswerRelevancy,
        "ContextPrecision": ContextPrecision,
        "ContextRecall": ContextRecall,
        "llm_factory": llm_factory,
        "embedding_factory": embedding_factory,
    }


# ============================================================
# LOAD QUESTIONS
# ============================================================


def load_questions() -> list[dict]:

    if not QUESTIONS_FILE.exists():

        raise FileNotFoundError(
            "Test questions file was not found:\n"
            f"{QUESTIONS_FILE}"
        )

    with open(
        QUESTIONS_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(
        data,
        list,
    ):

        raise ValueError(
            "test_questions.json must contain "
            "a JSON list."
        )

    valid_questions = []

    for index, item in enumerate(
        data,
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):

            print(
                f"WARNING: Question {index} "
                f"is not an object. Skipping."
            )

            continue

        question = str(
            item.get(
                "question",
                "",
            )
        ).strip()

        reference = str(
            item.get(
                "reference",
                "",
            )
        ).strip()

        if not question:

            print(
                f"WARNING: Question {index} "
                f"has no question. Skipping."
            )

            continue

        valid_questions.append(
            {
                "question": question,
                "reference": reference,
            }
        )

    return valid_questions


# ============================================================
# CREATE EVALUATOR LLM
# ============================================================


def create_evaluator_llm(
    ragas_tools,
):

    print()
    print("=" * 78)
    print("CREATING RAGAS EVALUATOR LLM")
    print("=" * 78)

    from openai import OpenAI

    client = OpenAI(
        api_key="ollama",
        base_url=(
            f"{OLLAMA_HOST}/v1"
        ),
    )

    llm_factory = ragas_tools[
        "llm_factory"
    ]

    evaluator_llm = llm_factory(
        OLLAMA_MODEL,
        provider="openai",
        client=client,
    )

    print(
        "Ragas evaluator LLM created."
    )

    return evaluator_llm


# ============================================================
# CREATE RAGAS EMBEDDINGS
# ============================================================


def create_ragas_embeddings(
    ragas_tools,
):

    print()
    print("=" * 78)
    print("CREATING RAGAS EMBEDDINGS")
    print("=" * 78)

    print(
        f"Embedding model: "
        f"{RAGAS_EMBEDDING_MODEL}"
    )

    from openai import OpenAI

    client = OpenAI(
        api_key="ollama",
        base_url=(
            f"{OLLAMA_HOST}/v1"
        ),
    )

    embedding_factory = ragas_tools[
        "embedding_factory"
    ]

    # --------------------------------------------------------
    # IMPORTANT
    #
    # Ragas 0.4.x collection metrics require modern
    # embeddings.
    #
    # Therefore we explicitly use:
    #
    # interface="modern"
    #
    # instead of the older Ragas adapter.
    # --------------------------------------------------------

    embeddings = embedding_factory(
        "openai",
        model=RAGAS_EMBEDDING_MODEL,
        client=client,
        interface="modern",
    )

    print(
        "Modern Ragas embeddings created."
    )

    return embeddings


# ============================================================
# INITIALIZE METRICS
# ============================================================


def create_metrics(
    ragas_tools,
    evaluator_llm,
    embeddings,
):

    print()
    print("=" * 78)
    print("CREATING RAGAS METRICS")
    print("=" * 78)

    Faithfulness = ragas_tools[
        "Faithfulness"
    ]

    AnswerRelevancy = ragas_tools[
        "AnswerRelevancy"
    ]

    ContextPrecision = ragas_tools[
        "ContextPrecision"
    ]

    ContextRecall = ragas_tools[
        "ContextRecall"
    ]

    # --------------------------------------------------------
    # Faithfulness
    # --------------------------------------------------------

    print(
        "Creating Faithfulness..."
    )

    faithfulness = Faithfulness(
        llm=evaluator_llm,
    )

    # --------------------------------------------------------
    # Answer Relevancy
    # --------------------------------------------------------

    print(
        "Creating AnswerRelevancy..."
    )

    answer_relevancy = AnswerRelevancy(
        llm=evaluator_llm,
        embeddings=embeddings,
    )

    # --------------------------------------------------------
    # Context Precision
    # --------------------------------------------------------

    print(
        "Creating ContextPrecision..."
    )

    context_precision = ContextPrecision(
        llm=evaluator_llm,
    )

    # --------------------------------------------------------
    # Context Recall
    # --------------------------------------------------------

    print(
        "Creating ContextRecall..."
    )

    context_recall = ContextRecall(
        llm=evaluator_llm,
    )

    metrics = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
    }

    print()
    print(
        "All Ragas metrics created successfully."
    )

    return metrics


# ============================================================
# SAFE SCORE
# ============================================================


def clean_score(value):

    if value is None:

        return None

    try:

        value = float(value)

    except (
        TypeError,
        ValueError,
    ):

        return None

    if math.isnan(value):

        return None

    if math.isinf(value):

        return None

    # Keep scores in the expected range.

    return max(
        0.0,
        min(
            1.0,
            value,
        ),
    )


# ============================================================
# RUN ONE METRIC
# ============================================================


async def score_metric(
    metric,
    *,
    user_input: str,
    response: str,
    retrieved_contexts: list[str],
    reference: str,
):

    kwargs = {
        "user_input": user_input,
        "response": response,
        "retrieved_contexts": retrieved_contexts,
    }

    # Context Recall needs the reference.
    #
    # Ragas 0.4.x uses "reference" for the collection metric.

    metric_name = getattr(
        metric,
        "name",
        "",
    )

    if metric_name == "context_recall":

        kwargs[
            "reference"
        ] = reference

    # --------------------------------------------------------
    # Ragas 0.4.x:
    #
    # result = await metric.ascore(...)
    #
    # result.value = numeric score
    #
    # result.reason = optional explanation
    # --------------------------------------------------------

    result = await metric.ascore(
        **kwargs
    )

    score = clean_score(
        getattr(
            result,
            "value",
            None,
        )
    )

    reason = getattr(
        result,
        "reason",
        None,
    )

    return score, reason


# ============================================================
# RUN ONE QUESTION
# ============================================================


async def evaluate_one_question(
    index: int,
    total: int,
    item: dict,
    rag: object,
    metrics: dict,
):

    question = item[
        "question"
    ]

    reference = item.get(
        "reference",
        "",
    )

    print()
    print("-" * 78)

    print(
        f"[{index}/{total}]"
    )

    print(
        f"Question: {question}"
    )

    # --------------------------------------------------------
    # Run your EXISTING RAG pipeline
    # --------------------------------------------------------

    try:

        rag_result = rag.ask(
            question
        )

    except Exception as exc:

        print(
            f"RAG ERROR: {exc}"
        )

        return {
            "question": question,
            "reference": reference,
            "answer": "",
            "retrieved_contexts": [],
            "chunks_retrieved": 0,
            "faithfulness": None,
            "answer_relevancy": None,
            "context_precision": None,
            "context_recall": None,
            "error": f"RAG error: {exc}",
        }

    answer = str(
        getattr(
            rag_result,
            "answer",
            "",
        )
        or ""
    )

    # --------------------------------------------------------
    # VERY IMPORTANT
    #
    # Your RAGPipeline AskResult currently has:
    #
    # answer
    # sources
    # chunks_used
    # verification_note
    #
    # It does NOT expose retrieved_contexts directly.
    #
    # Therefore we retrieve the same chunks again using the
    # existing Retriever and convert them to strings.
    # --------------------------------------------------------

    retrieved_contexts = []

    try:

        retrieved_chunks = (
            rag.retriever.retrieve(
                question
            )
        )

        for chunk in (
            retrieved_chunks or []
        ):

            content = str(
                getattr(
                    chunk,
                    "content",
                    "",
                )
                or ""
            ).strip()

            if content:

                retrieved_contexts.append(
                    content
                )

    except Exception as exc:

        print(
            "WARNING: Could not obtain "
            "retrieved contexts directly: "
            f"{exc}"
        )

    print(
        f"Chunks retrieved: "
        f"{len(retrieved_contexts)}"
    )

    print(
        f"Answer: "
        f"{answer[:500]}"
    )

    # --------------------------------------------------------
    # If no context was retrieved
    #
    # Ragas cannot meaningfully calculate context metrics.
    # --------------------------------------------------------

    if not retrieved_contexts:

        print(
            "WARNING: No retrieved context."
        )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    row = {
        "question": question,
        "reference": reference,
        "answer": answer,
        "retrieved_contexts": (
            retrieved_contexts
        ),
        "chunks_retrieved": len(
            retrieved_contexts
        ),
        "faithfulness": None,
        "answer_relevancy": None,
        "context_precision": None,
        "context_recall": None,
        "faithfulness_reason": "",
        "answer_relevancy_reason": "",
        "context_precision_reason": "",
        "context_recall_reason": "",
        "error": "",
    }

    # ========================================================
    # FAITHFULNESS
    # ========================================================

    print(
        "  Evaluating Faithfulness..."
    )

    try:

        score, reason = await score_metric(
            metrics[
                "faithfulness"
            ],
            user_input=question,
            response=answer,
            retrieved_contexts=retrieved_contexts,
            reference=reference,
        )

        row[
            "faithfulness"
        ] = score

        row[
            "faithfulness_reason"
        ] = str(
            reason or ""
        )

        print(
            f"    Faithfulness: "
            f"{score if score is not None else 'N/A'}"
        )

    except Exception as exc:

        print(
            f"    Faithfulness ERROR: "
            f"{exc}"
        )

        row[
            "faithfulness_reason"
        ] = f"ERROR: {exc}"

    # ========================================================
    # ANSWER RELEVANCY
    # ========================================================

    print(
        "  Evaluating Answer Relevancy..."
    )

    try:

        score, reason = await score_metric(
            metrics[
                "answer_relevancy"
            ],
            user_input=question,
            response=answer,
            retrieved_contexts=retrieved_contexts,
            reference=reference,
        )

        row[
            "answer_relevancy"
        ] = score

        row[
            "answer_relevancy_reason"
        ] = str(
            reason or ""
        )

        print(
            f"    Answer Relevancy: "
            f"{score if score is not None else 'N/A'}"
        )

    except Exception as exc:

        print(
            f"    Answer Relevancy ERROR: "
            f"{exc}"
        )

        row[
            "answer_relevancy_reason"
        ] = f"ERROR: {exc}"

    # ========================================================
    # CONTEXT PRECISION
    # ========================================================

    print(
        "  Evaluating Context Precision..."
    )

    try:

        score, reason = await score_metric(
            metrics[
                "context_precision"
            ],
            user_input=question,
            response=answer,
            retrieved_contexts=retrieved_contexts,
            reference=reference,
        )

        row[
            "context_precision"
        ] = score

        row[
            "context_precision_reason"
        ] = str(
            reason or ""
        )

        print(
            f"    Context Precision: "
            f"{score if score is not None else 'N/A'}"
        )

    except Exception as exc:

        print(
            f"    Context Precision ERROR: "
            f"{exc}"
        )

        row[
            "context_precision_reason"
        ] = f"ERROR: {exc}"

    # ========================================================
    # CONTEXT RECALL
    # ========================================================

    print(
        "  Evaluating Context Recall..."
    )

    try:

        if not reference:

            print(
                "    Context Recall skipped: "
                "no reference answer."
            )

        else:

            score, reason = await score_metric(
                metrics[
                    "context_recall"
                ],
                user_input=question,
                response=answer,
                retrieved_contexts=retrieved_contexts,
                reference=reference,
            )

            row[
                "context_recall"
            ] = score

            row[
                "context_recall_reason"
            ] = str(
                reason or ""
            )

            print(
                f"    Context Recall: "
                f"{score if score is not None else 'N/A'}"
            )

    except Exception as exc:

        print(
            f"    Context Recall ERROR: "
            f"{exc}"
        )

        row[
            "context_recall_reason"
        ] = f"ERROR: {exc}"

    # ========================================================
    # PRINT QUESTION SUMMARY
    # ========================================================

    print()
    print(
        "  QUESTION SCORE SUMMARY"
    )

    for metric_name in [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]:

        score = row[
            metric_name
        ]

        if score is None:

            display = "N/A"

        else:

            display = (
                f"{score:.4f} "
                f"({score * 100:.2f}%)"
            )

        print(
            f"    {metric_name:25s}: "
            f"{display}"
        )

    return row


# ============================================================
# RUN ALL QUESTIONS
# ============================================================


async def evaluate_all_questions(
    rag,
    test_cases,
    metrics,
):

    results = []

    total = len(
        test_cases
    )

    print()
    print("=" * 78)
    print("STARTING RAGAS EVALUATION")
    print("=" * 78)

    for index, item in enumerate(
        test_cases,
        start=1,
    ):

        result = (
            await evaluate_one_question(
                index=index,
                total=total,
                item=item,
                rag=rag,
                metrics=metrics,
            )
        )

        results.append(
            result
        )

    return results


# ============================================================
# SAVE CSV
# ============================================================


def save_csv(
    results,
):

    import pandas as pd

    dataframe = pd.DataFrame(
        results
    )

    output_file = (
        RESULTS_DIR
        / "ragas_results.csv"
    )

    dataframe.to_csv(
        output_file,
        index=False,
    )

    print()
    print(
        f"CSV saved to:"
    )

    print(
        output_file
    )

    return dataframe


# ============================================================
# SAVE JSON
# ============================================================


def save_json(
    results,
):

    output_file = (
        RESULTS_DIR
        / "ragas_results.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"JSON saved to:"
    )

    print(
        output_file
    )


# ============================================================
# CALCULATE OVERALL SCORES
# ============================================================


def calculate_overall_scores(
    results,
):

    metric_names = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]

    overall = {}

    print()
    print("=" * 78)
    print("OVERALL RAGAS SCORES")
    print("=" * 78)

    for metric_name in metric_names:

        values = []

        for row in results:

            value = row.get(
                metric_name
            )

            value = clean_score(
                value
            )

            if value is not None:

                values.append(
                    value
                )

        if values:

            average = (
                sum(values)
                / len(values)
            )

            overall[
                metric_name
            ] = average

            print(
                f"{metric_name:25s}: "
                f"{average:.4f} "
                f"({average * 100:.2f}%) "
                f"[{len(values)}/{len(results)}]"
            )

        else:

            overall[
                metric_name
            ] = None

            print(
                f"{metric_name:25s}: N/A"
            )

    return overall


# ============================================================
# SAVE SUMMARY
# ============================================================


def save_summary(
    overall,
    results,
):

    summary = {
        "configuration": {
            "ragas_version": "0.4.3",
            "ollama_host": OLLAMA_HOST,
            "evaluator_model": OLLAMA_MODEL,
            "embedding_model": RAGAS_EMBEDDING_MODEL,
        },
        "questions_total": len(
            results
        ),
        "scores": overall,
    }

    output_file = (
        RESULTS_DIR
        / "ragas_summary.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            indent=2,
        )

    print()
    print(
        f"Summary saved to:"
    )

    print(
        output_file
    )


# ============================================================
# INTERPRET SCORES
# ============================================================


def print_interpretation(
    overall,
):

    print()
    print("=" * 78)
    print("RAGAS SCORE INTERPRETATION")
    print("=" * 78)

    print(
        """
Score guide:

0.90 - 1.00  Excellent
0.80 - 0.89  Very good
0.70 - 0.79  Good
0.60 - 0.69  Needs improvement
Below 0.60    Poor

Important:
These are evaluation indicators, not a literal
"percentage accuracy" of the entire RAG system.
"""
    )

    for name, score in overall.items():

        if score is None:

            continue

        if score >= 0.90:

            level = "EXCELLENT"

        elif score >= 0.80:

            level = "VERY GOOD"

        elif score >= 0.70:

            level = "GOOD"

        elif score >= 0.60:

            level = "NEEDS IMPROVEMENT"

        else:

            level = "POOR"

        print(
            f"{name:25s}: "
            f"{level}"
        )

    print("=" * 78)


# ============================================================
# MAIN
# ============================================================


def main():

    try:

        # ====================================================
        # LOAD TEST QUESTIONS
        # ====================================================

        test_cases = load_questions()

        print()
        print(
            f"Test questions: "
            f"{len(test_cases)}"
        )

        if not test_cases:

            raise RuntimeError(
                "No valid questions were found "
                "in test_questions.json."
            )

        # ====================================================
        # LOAD RAGAS
        # ====================================================

        ragas_tools = load_ragas()

        # ====================================================
        # LOAD YOUR EXISTING RAG
        # ====================================================

        print()
        print("=" * 78)
        print("INITIALIZING YOUR EXISTING RAG PIPELINE")
        print("=" * 78)

        from app.rag import (
            RAGPipeline
        )

        rag = RAGPipeline()

        print(
            "RAGPipeline: OK"
        )

        # ====================================================
        # CREATE RAGAS LLM
        # ====================================================

        evaluator_llm = (
            create_evaluator_llm(
                ragas_tools
            )
        )

        # ====================================================
        # CREATE RAGAS EMBEDDINGS
        # ====================================================

        embeddings = (
            create_ragas_embeddings(
                ragas_tools
            )
        )

        # ====================================================
        # CREATE METRICS
        # ====================================================

        metrics = create_metrics(
            ragas_tools=ragas_tools,
            evaluator_llm=evaluator_llm,
            embeddings=embeddings,
        )

        # ====================================================
        # RUN EVALUATION
        # ====================================================

        results = asyncio.run(
            evaluate_all_questions(
                rag=rag,
                test_cases=test_cases,
                metrics=metrics,
            )
        )

        # ====================================================
        # SAVE RESULTS
        # ====================================================

        dataframe = save_csv(
            results
        )

        save_json(
            results
        )

        # ====================================================
        # OVERALL SCORES
        # ====================================================

        overall = (
            calculate_overall_scores(
                results
            )
        )

        save_summary(
            overall=overall,
            results=results,
        )

        # ====================================================
        # INTERPRETATION
        # ====================================================

        print_interpretation(
            overall
        )

        # ====================================================
        # FINAL
        # ====================================================

        print()
        print("=" * 78)
        print("RAGAS EVALUATION COMPLETED SUCCESSFULLY")
        print("=" * 78)

        print(
            f"Questions evaluated: "
            f"{len(results)}"
        )

        print()
        print(
            "Files:"
        )

        print(
            f"  {RESULTS_DIR / 'ragas_results.csv'}"
        )

        print(
            f"  {RESULTS_DIR / 'ragas_results.json'}"
        )

        print(
            f"  {RESULTS_DIR / 'ragas_summary.json'}"
        )

        print()
        print(
            "Your RAGAS evaluation is complete."
        )

    except KeyboardInterrupt:

        print()
        print(
            "Evaluation interrupted by user."
        )

    except Exception as exc:

        print()
        print("=" * 78)
        print("RAGAS EVALUATION FAILED")
        print("=" * 78)

        print(
            repr(exc)
        )

        traceback.print_exc()

        raise

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()