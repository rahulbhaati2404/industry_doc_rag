import asyncio
import time
from typing import Any

from context.token_counter import token_counter
from core.logger import logger
from guardrails.input_guard import input_guard
from memory.semantic_memory import semantic_memory
from memory.session_memory import session_memory
from memory.summarizer import conversation_summarizer
from models.router import model_router
from observability.metrics import metrics_collector
from observability.tracing import trace_manager
from pipeline.generation_stage import run_generation
from pipeline.memory_stage import (
    build_memory_context,
    build_retrieval_query,
    resolve_memory_answer,
)
from pipeline.retrieval_stage import run_retrieval
from pipeline.safety_stage import validate_answer
from rag.context_builder import context_builder
from rag.prompt_builder import prompt_builder


class RAGPipeline:
    """Production RAG pipeline orchestration with async and streaming support."""

    async def _prepare(self, query: str, session_id: str) -> dict[str, Any]:
        """Validate input and prepare retrieval, prompt, and model selection."""

        guardrail_result = input_guard.validate_input(query)
        if guardrail_result.blocked:
            return {
                "blocked": True,
                "guardrail_message": guardrail_result.message,
                "guardrail_reason": guardrail_result.matched_pattern,
                "query": query,
                "retrieval_query": query,
            }

        query = guardrail_result.cleaned_text or query

        memory_answer = resolve_memory_answer(
            session_id=session_id,
            query=query,
        )
        if memory_answer:
            return {
                "blocked": False,
                "memory_answer": memory_answer,
                "query": query,
            }

        memory_context = build_memory_context(
            session_id=session_id,
            query=query,
        )

        retrieval_query = build_retrieval_query(
            session_id=session_id,
            query=query,
        )

        retrieved_docs = await run_retrieval(query=retrieval_query)

        with trace_manager.trace("context_building"):
            context = context_builder.build_context(retrieved_docs)

        with trace_manager.trace("prompt_building"):
            prompt = prompt_builder.build_prompt(
                query=query,
                context=context,
                memory_context=memory_context,
            )

        prompt_tokens = token_counter.estimate_tokens(prompt)
        selected_model = model_router.route_generation_model(
            prompt_length=prompt_tokens,
        )

        logger.info(f"Selected model: {selected_model}")

        return {
            "blocked": False,
            "query": query,
            "retrieval_query": retrieval_query,
            "prompt": prompt,
            "context": context,
            "retrieved_docs": retrieved_docs,
            "selected_model": selected_model,
            "prompt_tokens": prompt_tokens,
        }

    def run(self, query: str, session_id: str = "default") -> dict[str, Any]:
        """Run the async pipeline from sync callers."""

        return asyncio.run(self.arun(query=query, session_id=session_id))

    async def arun(self, query: str, session_id: str = "default") -> dict[str, Any]:
        """Run the full non-streaming RAG flow."""

        start_time = time.time()
        logger.info(f"Starting async RAG pipeline for query: {query}")

        prepared = await self._prepare(query=query, session_id=session_id)
        if prepared.get("blocked") and prepared.get("guardrail_message"):
            latency_ms = (time.time() - start_time) * 1000
            blocked_message = prepared["guardrail_message"]
            logger.info(f"Pipeline interrupted in {latency_ms:.2f} ms")
            return self._build_interrupted_response(
                query=query,
                message=blocked_message,
                latency_ms=latency_ms,
                reason=prepared.get("guardrail_reason"),
            )

        if prepared.get("memory_answer"):
            answer = prepared["memory_answer"]
            latency_ms = (time.time() - start_time) * 1000
            self._store_memory(
                session_id=session_id,
                query=query,
                answer=answer,
            )
            return {
                "query": query,
                "answer": answer,
                "model_used": "session-memory",
                "sources": [],
                "tokens_used": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "latency_ms": latency_ms,
                "confidence_score": 1.0,
                "is_hallucinated": False,
                "status": "success",
                "message": "Answer resolved from conversation memory.",
                "guardrail_triggered": False,
            }

        query = prepared["query"]
        prompt = prepared["prompt"]
        context = prepared["context"]
        retrieved_docs = prepared["retrieved_docs"]
        selected_model = prepared["selected_model"]
        prompt_tokens = prepared["prompt_tokens"]

        answer, response_cache_hit = await run_generation(
            prompt=prompt,
            model=selected_model,
        )

        completion_tokens = token_counter.estimate_tokens(answer)
        total_tokens = prompt_tokens + completion_tokens
        latency_ms = (time.time() - start_time) * 1000

        logger.info(f"Pipeline completed in {latency_ms:.2f} ms")

        (
            answer,
            confidence_score,
            is_hallucinated,
            output_guard_triggered,
            guardrail_message,
            guardrail_reason,
        ) = await validate_answer(
            query=query,
            context=context,
            answer=answer,
            model=selected_model,
        )

        self._record_metrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            confidence_score=confidence_score,
            is_hallucinated=is_hallucinated,
            retrieved_docs=retrieved_docs,
            response_cache_hit=response_cache_hit,
        )

        self._store_memory(
            session_id=session_id,
            query=query,
            answer=answer,
        )

        return {
            "query": query,
            "answer": answer,
            "model_used": selected_model,
            "sources": [
                {
                    "content": doc["text"][:500],
                    "source_file": doc["metadata"].get("source", "unknown"),
                    "relevance_score": doc.get("rerank_score", 0.0),
                }
                for doc in retrieved_docs
            ],
            "tokens_used": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "latency_ms": latency_ms,
            "confidence_score": confidence_score,
            "is_hallucinated": is_hallucinated,
            "status": "blocked" if output_guard_triggered else "success",
            "message": guardrail_message,
            "guardrail_triggered": output_guard_triggered,
            "guardrail_reason": guardrail_reason,
        }

    async def astream(self, query: str, session_id: str = "default"):
        """Stream model output for a prepared RAG prompt."""

        from models.ollama_client import ollama_client

        prepared = await self._prepare(query=query, session_id=session_id)
        if prepared.get("blocked") and prepared.get("guardrail_message"):
            yield prepared["guardrail_message"]
            return

        if prepared.get("memory_answer"):
            yield prepared["memory_answer"]
            return

        prompt = prepared["prompt"]
        selected_model = prepared["selected_model"]

        async for chunk in ollama_client.astream_generate(
            prompt=prompt,
            model=selected_model,
        ):
            yield chunk

    def _record_metrics(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        confidence_score: float,
        is_hallucinated: bool,
        retrieved_docs: list[dict[str, Any]],
        response_cache_hit: bool,
    ) -> None:
        metrics_collector.record("prompt_tokens", prompt_tokens)
        metrics_collector.record("completion_tokens", completion_tokens)
        metrics_collector.record("latency_ms", latency_ms)
        metrics_collector.record("hallucination_score", confidence_score)
        metrics_collector.record("hallucination_detected", 1 if is_hallucinated else 0)
        metrics_collector.record("retrieved_documents", len(retrieved_docs))
        metrics_collector.record("response_cache_hit", 1 if response_cache_hit else 0)

        if retrieved_docs:
            metrics_collector.record(
                "top_rerank_score",
                retrieved_docs[0].get("rerank_score", 0.0),
            )

    def _store_memory(self, session_id: str, query: str, answer: str) -> None:
        session_memory.add_message(session_id, "user", query)
        session_memory.add_message(session_id, "assistant", answer)

        updated_history = session_memory.get_recent_history(session_id)
        summary = conversation_summarizer.summarize(updated_history)
        semantic_memory.remember(session_id=session_id, memory=summary)

    def _build_interrupted_response(
        self,
        query: str,
        message: str,
        latency_ms: float,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "answer": message,
            "model_used": "guardrail",
            "sources": [],
            "tokens_used": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "latency_ms": latency_ms,
            "confidence_score": None,
            "is_hallucinated": False,
            "status": "blocked",
            "message": message,
            "guardrail_triggered": True,
            "guardrail_reason": reason,
        }


rag_pipeline = RAGPipeline()
