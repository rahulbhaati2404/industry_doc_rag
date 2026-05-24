class ContextBuilder:

    def build_context(
        self,
        documents: list[dict]
    ) -> str:

        context_parts = []

        for idx, doc in enumerate(documents):

            source = doc["metadata"].get(
                "source",
                "unknown"
            )

            score = doc.get(
                "rerank_score",
                0.0
            )

            context_parts.append(
                f"""
                    [Document {idx + 1}]
                    Source: {source}
                    Relevance Score: {score:.4f}

                    Content:
                    {doc['text']}
                """
            )

        final_context = "\n\n".join(
            context_parts
        )

        return final_context


context_builder = ContextBuilder()