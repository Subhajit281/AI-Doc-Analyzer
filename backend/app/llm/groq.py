import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

class GroqProvider:
    """
    Groq LLM Provider hosting OpenAI's GPT-OSS 120B model on Groq's LPU inference engine.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.2,
    ):
        api_key = os.getenv("GROQ_API_KEY", "").strip()

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Please add GROQ_API_KEY to your backend/.env file."
            )

        self.model_name = (
            model
            or os.getenv("GROQ_MODEL", "").strip()
            or DEFAULT_GROQ_MODEL
        )

        self.model = ChatGroq(
            model=self.model_name,
            api_key=api_key,
            temperature=temperature,
        )

    def get_model(self):
        return self.model

