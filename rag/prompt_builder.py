
class PromptBuilder:

    SYSTEM_PROMPT = """
        You are an expert corporate assistant. Answer using the provided document snippets and the conversation memory.

Follow these formatting rules strictly:
1. Synthesize information from all provided snippets into a clean, direct answer. Do not apologize or tell the user that information is missing or incomplete if parts of the answer are present.
2. If the context contains partial lists or tables, construct the best possible answer from those items without adding preambles like "I couldn't find a comprehensive list, but...".
3. Keep your tone direct, professional, and clear. 
4. Use MEMORY to resolve follow-up questions, personal references, and conversation-specific facts even if the document snippets do not contain them.
5. If MEMORY contains the answer to a question about the current conversation or the user, prefer MEMORY over the document snippets.
6. ONLY say "I cannot find the information in the provided documents" if none of the keywords or requested details appear in the text snippets and MEMORY does not contain the answer either.
    """

    def build_prompt(
            self,
            query: str,
            context: str,
            memory_context: str = ""
    ):

        prompt = f"""
                {self.SYSTEM_PROMPT}

                ================ MEMORY ================

                {memory_context}

                ================ CONTEXT ================

                {context}

                ================ USER QUERY ================

                {query}

                ================ ANSWER ================
        """

        return prompt


prompt_builder = PromptBuilder()
