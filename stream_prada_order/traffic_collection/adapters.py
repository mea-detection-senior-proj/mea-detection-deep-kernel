"""Adapter contracts only. No transformers/torch/HTTP imports or model loaders."""
from dataclasses import dataclass
from typing import Protocol

from .schema import ExecutionDisabled


@dataclass(frozen=True)
class AdapterResponse:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    token_origin: str = "unavailable"


class AdapterFailure(Exception):
    def __init__(self, code="adapter_failure", delivery="unknown", retryable=False):
        super().__init__("adapter_failure")
        self.code, self.delivery, self.retryable = code, delivery, retryable


class VictimAdapter(Protocol):
    is_mock: bool
    identity: dict

    def respond(self, query: str, context: dict) -> AdapterResponse: ...


class QwenLocalAdapter:
    """Pinned deployment plan, deliberately non-executable throughout Phase G.

    A future authorized phase must implement/review the local runtime bridge.
    Neither an environment variable nor a CLI switch can enable it here.
    """
    is_mock = False
    revision = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
    identity = {"model_id": "Qwen/Qwen2.5-1.5B-Instruct", "model_revision": revision,
                "tokenizer_id": "Qwen/Qwen2.5-1.5B-Instruct", "tokenizer_revision": revision}

    def deployment_plan(self):
        return {"identity": dict(self.identity), "execution_enabled": False,
                "local_files_only": True, "trust_remote_code": False,
                "batch_size": 1, "max_input_tokens": 2048, "max_new_tokens": 128,
                "runtime_bridge_implemented": False}

    def respond(self, query, context):
        raise ExecutionDisabled("real_model_execution_disabled")
