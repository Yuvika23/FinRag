"""
FinRAG — LLM client abstraction.
Supports OpenAI, Anthropic, Google (Gemini), or a no-LLM fallback.
"""

from __future__ import annotations

from typing import Optional
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LLMClient:
    """
    Unified LLM interface. Chooses provider from settings.
    Returns None if LLM_PROVIDER=none or credentials are missing.
    """

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        provider = settings.llm_provider.lower()

        if provider == "none":
            return None

        if provider == "openai":
            return self._openai(prompt, system_prompt)
        elif provider == "anthropic":
            return self._anthropic(prompt, system_prompt)
        elif provider == "google":
            return self._google(prompt, system_prompt)
        elif provider == "huggingface":
            return self._huggingface(prompt, system_prompt)
        else:
            logger.warning("unknown_llm_provider", provider=provider)
            return None

    def is_available(self) -> bool:
        provider = settings.llm_provider.lower()
        if provider == "none":
            return False
        if provider == "openai":
            return bool(settings.openai_api_key)
        if provider == "anthropic":
            return bool(settings.anthropic_api_key)
        if provider == "google":
            return bool(settings.google_api_key)
        if provider == "huggingface":
            return True  # Local model
        return False

    def _openai(self, prompt: str, system_prompt: Optional[str]) -> Optional[str]:
        if not settings.openai_api_key:
            logger.warning("openai_key_missing")
            return None
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=0.1,
                max_tokens=1500,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("openai_error", error=str(e))
            return None

    def _anthropic(self, prompt: str, system_prompt: Optional[str]) -> Optional[str]:
        if not settings.anthropic_api_key:
            logger.warning("anthropic_key_missing")
            return None
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            kwargs = {
                "model": settings.anthropic_model,
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            logger.error("anthropic_error", error=str(e))
            return None

    def _google(self, prompt: str, system_prompt: Optional[str]) -> Optional[str]:
        if not settings.google_api_key:
            logger.warning("google_key_missing")
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            model = genai.GenerativeModel(
                settings.google_model,
                system_instruction=system_prompt or "",
            )
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 1500},
            )
            return response.text
        except Exception as e:
            logger.error("google_error", error=str(e))
            return None

    def _huggingface(self, prompt: str, system_prompt: Optional[str]) -> Optional[str]:
        try:
            from transformers import pipeline
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            pipe = pipeline(
                "text-generation",
                model=settings.hf_model_name,
                device=settings.hf_device,
                max_new_tokens=512,
            )
            result = pipe(full_prompt)
            generated = result[0]["generated_text"]
            # Remove the input prompt from the output
            if generated.startswith(full_prompt):
                generated = generated[len(full_prompt):].strip()
            return generated
        except Exception as e:
            logger.error("huggingface_error", error=str(e))
            return None


llm_client = LLMClient()
