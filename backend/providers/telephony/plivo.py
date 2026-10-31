"""Plivo Telephony adapter.

Initiates outbound PSTN calls and manages call lifecycles using Plivo REST API:
  POST https://api.plivo.com/v1/Account/{auth_id}/Call/
"""

import logging
from typing import Any, Optional
import httpx

from backend.providers.base import TelephonyProvider

log = logging.getLogger("provider.telephony.plivo")


class PlivoTelephonyProvider(TelephonyProvider):
    provider_name = "plivo"

    def __init__(self, base_url: str = "https://api.plivo.com/v1", client: Optional[httpx.AsyncClient] = None):
        self.base_url = base_url.rstrip("/")
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=20.0)

    async def initiate_call(self, to: str, from_number: str, **kwargs: Any) -> dict:
        """
        Initiate an outbound call via Plivo REST API.
        kwargs must contain:
          - auth_id: str
          - auth_token: str
          - url: str (answer_url pointing to PlivoXML webhook)
        """
        auth_id = kwargs.get("auth_id")
        auth_token = kwargs.get("auth_token")
        answer_url = kwargs.get("url")

        if not auth_id or not auth_token:
            raise ValueError("Plivo initiate_call requires auth_id and auth_token")
        if not answer_url:
            raise ValueError("Plivo initiate_call requires url (answer_url)")

        endpoint = f"{self.base_url}/Account/{auth_id}/Call/"
        auth = (auth_id, auth_token)
        payload = {
            "from": from_number,
            "to": to,
            "answer_url": answer_url,
            "answer_method": "POST",
        }

        client = await self._get_client()
        try:
            r = await client.post(endpoint, auth=auth, json=payload)
            r.raise_for_status()
            data = r.json()
            log.info("Plivo initiate_call response: %s", data)
            call_id = (
                data.get("request_uuid")
                or data.get("call_uuid")
                or data.get("call_id")
                or data.get("api_id")
                or "plivo_call"
            )
            return {
                "provider_resource_id": str(call_id),
                "status": "queued",
                "raw": data,
            }
        except httpx.HTTPStatusError as exc:
            log.error("Plivo call initiation failed status=%s body=%s", exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Plivo API error: {exc.response.status_code} - {exc.response.text}") from exc
        finally:
            if self._client is None:
                await client.aclose()

    async def hangup_call(self, provider_resource_id: str, **kwargs: Any) -> None:
        """Hang up a live call."""
        auth_id = kwargs.get("auth_id")
        auth_token = kwargs.get("auth_token")
        if not auth_id or not auth_token:
            log.warning("Cannot hangup Plivo call %s without auth credentials", provider_resource_id)
            return

        endpoint = f"{self.base_url}/Account/{auth_id}/Call/{provider_resource_id}/"
        auth = (auth_id, auth_token)
        client = await self._get_client()
        try:
            r = await client.delete(endpoint, auth=auth)
            r.raise_for_status()
        except Exception as exc:
            log.warning("Failed to hang up Plivo call %s: %s", provider_resource_id, exc)
        finally:
            if self._client is None:
                await client.aclose()

    async def get_call_status(self, provider_resource_id: str, **kwargs: Any) -> dict:
        """Fetch status of a call."""
        auth_id = kwargs.get("auth_id")
        auth_token = kwargs.get("auth_token")
        if not auth_id or not auth_token:
            return {"provider_resource_id": provider_resource_id, "status": "unknown"}

        endpoint = f"{self.base_url}/Account/{auth_id}/Call/{provider_resource_id}/"
        auth = (auth_id, auth_token)
        client = await self._get_client()
        try:
            r = await client.get(endpoint, auth=auth)
            r.raise_for_status()
            data = r.json()
            return {
                "provider_resource_id": provider_resource_id,
                "status": data.get("call_status") or data.get("status", "in-progress"),
                "raw": data,
            }
        except Exception as exc:
            log.warning("Failed to get Plivo call status %s: %s", provider_resource_id, exc)
            return {"provider_resource_id": provider_resource_id, "status": "unknown"}
        finally:
            if self._client is None:
                await client.aclose()

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "outbound_calling": True,
            "inbound_calling": True,
            "streaming_audio": True,
        }
