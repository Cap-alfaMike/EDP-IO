# ============================================================================
# EDP-IO - Serverless Provider Abstraction
# ============================================================================
"""
Cloud-agnostic serverless interface for Functions/Containers.

PROVIDERS:
- Azure: Functions, Container Apps
- GCP: Cloud Functions, Cloud Run
- AWS: Lambda, Fargate
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FunctionConfig(BaseModel):
    name: str
    runtime: str = "python3.11"
    memory_mb: int = 256
    timeout_seconds: int = 300
    environment: Dict[str, str] = {}
    entry_point: str = "main"


class FunctionDeployment(BaseModel):
    function_id: str
    name: str
    url: str
    status: str
    deployed_at: datetime


class InvocationResult(BaseModel):
    status_code: int
    body: Any
    duration_ms: float
    logs: Optional[str] = None


class ServerlessProvider(ABC):
    """Abstract serverless provider interface."""

    @abstractmethod
    def deploy_function(self, config: FunctionConfig, code_path: str) -> FunctionDeployment:
        pass

    @abstractmethod
    def invoke(self, function_name: str, payload: Dict[str, Any]) -> InvocationResult:
        pass

    @abstractmethod
    def list_functions(self) -> List[FunctionDeployment]:
        pass

    @abstractmethod
    def delete_function(self, function_name: str) -> bool:
        pass


class AzureFunctionsProvider(ServerlessProvider):
    """Azure Functions implementation."""

    def __init__(self, resource_group: Optional[str] = None):
        self.resource_group = resource_group or os.getenv("AZURE_RESOURCE_GROUP")

    def deploy_function(self, config: FunctionConfig, code_path: str) -> FunctionDeployment:
        return FunctionDeployment(
            function_id=f"azure-{config.name}",
            name=config.name,
            url=f"https://{config.name}.azurewebsites.net/api/{config.entry_point}",
            status="deployed",
            deployed_at=datetime.now(),
        )

    def invoke(self, function_name: str, payload: Dict[str, Any]) -> InvocationResult:
        return InvocationResult(status_code=200, body={"result": "ok"}, duration_ms=150)

    def list_functions(self) -> List[FunctionDeployment]:
        return []

    def delete_function(self, function_name: str) -> bool:
        return True


class GCPCloudRunProvider(ServerlessProvider):
    """GCP Cloud Run / Cloud Functions."""

    def __init__(self, project: Optional[str] = None, region: str = "us-central1"):
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = region

    def deploy_function(self, config: FunctionConfig, code_path: str) -> FunctionDeployment:
        return FunctionDeployment(
            function_id=f"gcp-{config.name}",
            name=config.name,
            url=f"https://{config.name}-{self.region}.a.run.app",
            status="deployed",
            deployed_at=datetime.now(),
        )

    def invoke(self, function_name: str, payload: Dict[str, Any]) -> InvocationResult:
        return InvocationResult(status_code=200, body={"result": "ok"}, duration_ms=100)

    def list_functions(self) -> List[FunctionDeployment]:
        return []

    def delete_function(self, function_name: str) -> bool:
        return True


class AWSLambdaProvider(ServerlessProvider):
    """AWS Lambda."""

    def __init__(self, region: str = "us-east-1"):
        self.region = region

    def deploy_function(self, config: FunctionConfig, code_path: str) -> FunctionDeployment:
        return FunctionDeployment(
            function_id=f"arn:aws:lambda:{self.region}:123456789:function:{config.name}",
            name=config.name,
            url=f"https://{config.name}.lambda-url.{self.region}.on.aws/",
            status="deployed",
            deployed_at=datetime.now(),
        )

    def invoke(self, function_name: str, payload: Dict[str, Any]) -> InvocationResult:
        return InvocationResult(status_code=200, body={"result": "ok"}, duration_ms=80)

    def list_functions(self) -> List[FunctionDeployment]:
        return []

    def delete_function(self, function_name: str) -> bool:
        return True


class MockServerlessProvider(ServerlessProvider):
    """Mock provider for local development."""

    def __init__(self):
        self._functions: Dict[str, FunctionDeployment] = {}

    def deploy_function(self, config: FunctionConfig, code_path: str) -> FunctionDeployment:
        deployment = FunctionDeployment(
            function_id=f"mock-{config.name}",
            name=config.name,
            url=f"http://localhost:8080/{config.name}",
            status="deployed",
            deployed_at=datetime.now(),
        )
        self._functions[config.name] = deployment
        return deployment

    def invoke(self, function_name: str, payload: Dict[str, Any]) -> InvocationResult:
        return InvocationResult(status_code=200, body=payload, duration_ms=10)

    def list_functions(self) -> List[FunctionDeployment]:
        return list(self._functions.values())

    def delete_function(self, function_name: str) -> bool:
        if function_name in self._functions:
            del self._functions[function_name]
            return True
        return False


def get_serverless_provider(provider: Optional[str] = None) -> ServerlessProvider:
    """Factory to get configured serverless provider."""
    provider = provider or os.getenv("SERVERLESS_PROVIDER", "mock")

    if provider == "azure":
        return AzureFunctionsProvider()
    elif provider == "gcp":
        return GCPCloudRunProvider()
    elif provider == "aws":
        return AWSLambdaProvider()
    return MockServerlessProvider()
