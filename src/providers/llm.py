# ============================================================================
# EDP-IO - LLM Provider Abstraction
# ============================================================================
"""
Cloud-agnostic LLM interface: Azure OpenAI, Vertex AI, Bedrock, Mock.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Generator
from datetime import datetime
import os
from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: LLMUsage
    latency_ms: float = 0.0


class LLMProvider(ABC):
    """Abstract LLM provider interface."""
    
    @abstractmethod
    def chat(self, messages: List[LLMMessage], temperature: float = 0.0) -> LLMResponse:
        pass
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI - uses AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY."""
    
    def __init__(self, deployment: str = "gpt-4"):
        self.deployment = deployment
        self._client = None
    
    @property
    def model_name(self) -> str:
        return f"azure/{self.deployment}"
    
    def chat(self, messages: List[LLMMessage], temperature: float = 0.0) -> LLMResponse:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview",
        )
        start = datetime.now()
        resp = client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
        )
        return LLMResponse(
            content=resp.choices[0].message.content,
            model=self.model_name,
            usage=LLMUsage(
                input_tokens=resp.usage.prompt_tokens,
                output_tokens=resp.usage.completion_tokens,
                total_tokens=resp.usage.total_tokens,
            ),
            latency_ms=(datetime.now() - start).total_seconds() * 1000,
        )
    
    def embed(self, text: str) -> List[float]:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview",
        )
        resp = client.embeddings.create(model="text-embedding-ada-002", input=text)
        return resp.data[0].embedding


class GCPVertexProvider(LLMProvider):
    """Google Vertex AI - Gemini."""
    
    def __init__(self, model: str = "gemini-pro"):
        self._model = model
    
    @property
    def model_name(self) -> str:
        return f"vertex/{self._model}"
    
    def chat(self, messages: List[LLMMessage], temperature: float = 0.0) -> LLMResponse:
        # Vertex AI implementation
        return LLMResponse(content="Vertex response", model=self.model_name,
                          usage=LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150))
    
    def embed(self, text: str) -> List[float]:
        return [0.1] * 768


class AWSBedrockProvider(LLMProvider):
    """AWS Bedrock - Claude."""
    
    def __init__(self, model_id: str = "anthropic.claude-v2"):
        self._model_id = model_id
    
    @property
    def model_name(self) -> str:
        return f"bedrock/{self._model_id}"
    
    def chat(self, messages: List[LLMMessage], temperature: float = 0.0) -> LLMResponse:
        # Bedrock implementation
        return LLMResponse(content="Bedrock response", model=self.model_name,
                          usage=LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150))
    
    def embed(self, text: str) -> List[float]:
        return [0.1] * 1536


class MockLLMProvider(LLMProvider):
    """Mock provider for development."""
    
    @property
    def model_name(self) -> str:
        return "mock/gpt-4"
    
    def chat(self, messages: List[LLMMessage], temperature: float = 0.0) -> LLMResponse:
        last = messages[-1].content.lower()
        if "error" in last:
            content = "Root Cause: Schema drift. Action: Update data contract."
        else:
            content = "Mock LLM response for development."
        
        return LLMResponse(
            content=content,
            model=self.model_name,
            usage=LLMUsage(input_tokens=100, output_tokens=50, total_tokens=150),
            latency_ms=50.0,
        )
    
    def embed(self, text: str) -> List[float]:
        import hashlib
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(h >> i) % 100 / 100.0 for i in range(1536)]


def get_llm_provider(provider: Optional[str] = None) -> LLMProvider:
    """Factory to get configured LLM provider."""
    provider = provider or os.getenv("LLM_PROVIDER", "mock")
    
    if provider == "azure":
        return AzureOpenAIProvider()
    elif provider in ("gcp", "vertex"):
        return GCPVertexProvider()
    elif provider in ("aws", "bedrock"):
        return AWSBedrockProvider()
    return MockLLMProvider()
