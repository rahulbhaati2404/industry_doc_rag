
class PromptBuilder:

    SYSTEM_PROMPT = """
        You are an expert corporate assistant. Your task is to answer user queries using the provided document snippets. 

Follow these formatting rules strictly:
1. Synthesize information from all provided snippets into a clean, direct answer. Do not apologize or tell the user that information is missing or incomplete if parts of the answer are present.
2. If the context contains partial lists or tables, construct the best possible answer from those items without adding preambles like "I couldn't find a comprehensive list, but...".
3. Keep your tone direct, professional, and clear. 
4. ONLY say "I cannot find the information in the provided documents" if none of the keywords or requested details appear in the text snippets at all.
    """

    def build_prompt(
            self,
            query: str,
            context: str,
            memory_context: str = ""
    ):

        prompt = f"""
                {self.SYSTEM_PROMPT}

                ================ CONTEXT ================

                {context}

                ================ USER QUERY ================

                {query}

                ================ ANSWER ================

                ================ MEMORY ================

                {memory_context}
        """

        return prompt


prompt_builder = PromptBuilder()