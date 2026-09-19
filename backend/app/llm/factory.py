import os
from dotenv import load_dotenv

load_dotenv()

def get_llm(is_pro: bool = False):
    """
    Returns the appropriate LLM instance based on user subscription tier.
    - Free Tier: Fast standard model ('llama-3.1-8b-instant') on Groq.
    - Paid Pro Tier: Groq's flagship OpenAI GPT-OSS 120B ('openai/gpt-oss-120b') for deep multi-page reasoning.
    """
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()

    if provider == "gemini":
        from app.llm.gemini import GeminiProvider
        return GeminiProvider().get_model()

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Please set your Groq API key (GROQ_API_KEY=gsk_...) in backend/.env to use Groq models."
        )

    from app.llm.groq import GroqProvider
    if is_pro:
        model = os.getenv("GROQ_PRO_MODEL", "qwen/qwen3.8-27b").strip()
        temperature = 0.1
    else:
        model = os.getenv("GROQ_FREE_MODEL", "openai/gpt-oss-120b").strip()
        temperature = 0.2

    return GroqProvider(model=model, temperature=temperature).get_model()

def get_model_name(is_pro: bool = False) -> str:
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider == "gemini":
        return "gemini-1.5-flash"
    if is_pro:
        return os.getenv("GROQ_PRO_MODEL", "qwen/qwen3.8-27b").strip()
    return os.getenv("GROQ_FREE_MODEL", "openai/gpt-oss-120b").strip()

