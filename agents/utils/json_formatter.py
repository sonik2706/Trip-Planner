from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import json

class GenericLLMFormatter:
    def __init__(self, llm, prompt_template_str: str, input_variables: list[str]):
        """
        llm: LLM to be used (e.g., ChatGoogleGenerativeAI)
        prompt_template_str: raw string template (with placeholders)
        input_variables: list of variables used in the template
        """
        self.prompt = PromptTemplate(
            template=prompt_template_str,
            input_variables=input_variables
        )
        self.chain = LLMChain(llm=llm, prompt=self.prompt)

    def run(self, **kwargs) -> dict:
        """
        Runs the formatter chain with dynamic keyword arguments
        Always returns a dict (fallbacks to safe structure if parsing fails)
        """
        response = self.chain.run(kwargs)
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if 0 <= start < end:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        # Fallback dict
        return {
            "error": "LLM returned non-JSON response",
            "raw_text": response
        }
