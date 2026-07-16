"""Bedrock adapter. The only place that knows about Bedrock. Swappable via
config, per PROJECT_CONTEXT §23."""
from __future__ import annotations

import json
from typing import Any

import boto3


class BedrockReasoner:
    """Implements ReasonerPort using the Bedrock Converse API."""

    def __init__(
        self,
        model_id: str,
        region: str = "eu-central-1",
        profile: str | None = None,          # 👈 add
    ):
        session = boto3.Session(profile_name=profile, region_name=region)  # 👈 change
        self._client = session.client("bedrock-runtime")
        self._model_id = model_id

    async def reason(self, system_prompt: str, user_prompt: str) -> str:
        resp = self._client.converse(
            modelId=self._model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"temperature": 0.2, "maxTokens": 4096},
        )
        return resp["output"]["message"]["content"][0]["text"]

    async def reason_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        text = await self.reason(
            system_prompt + "\n\nRespond with valid JSON only.", user_prompt)
        try:
            return json.loads(text[text.find("{"): text.rfind("}") + 1])
        except (ValueError, json.JSONDecodeError):
            return {}