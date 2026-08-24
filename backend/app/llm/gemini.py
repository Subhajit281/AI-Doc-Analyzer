import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


# Load variables from .env
load_dotenv()


class GeminiProvider:

    def __init__(
        self,
        model: str = "gemini-3.5-flash-lite"
    ):

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set"
            )

        self.model = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
        )

    def get_model(self):
        return self.model