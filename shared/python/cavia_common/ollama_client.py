"""
Ollama client for LLM inference
"""

from typing import Any, Dict, List, Optional
import httpx

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Client for Ollama LLM inference"""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.client = httpx.Client(timeout=120.0)
        logger.info("Ollama client initialized", host=self.host, model=self.model)

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """Generate text completion"""
        try:
            payload: Dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            }

            if system:
                payload["system"] = system

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            response = self.client.post(
                f"{self.host}/api/generate",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except Exception as e:
            logger.error("Ollama generation error", error=str(e))
            return None

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Chat completion with message history"""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }

            response = self.client.post(
                f"{self.host}/api/chat",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            return result.get("message", {}).get("content", "")

        except Exception as e:
            logger.error("Ollama chat error", error=str(e))
            return None

    def list_models(self) -> List[str]:
        """List available models"""
        try:
            response = self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            result = response.json()
            return [model["name"] for model in result.get("models", [])]
        except Exception as e:
            logger.error("Failed to list models", error=str(e))
            return []

    def pull_model(self, model: str) -> bool:
        """Pull a model from registry"""
        try:
            response = self.client.post(
                f"{self.host}/api/pull",
                json={"name": model},
                timeout=600.0,  # 10 minutes for model download
            )
            response.raise_for_status()
            logger.info("Model pulled successfully", model=model)
            return True
        except Exception as e:
            logger.error("Failed to pull model", model=model, error=str(e))
            return False


def get_ollama_client() -> OllamaClient:
    """Get Ollama client instance"""
    return OllamaClient()
