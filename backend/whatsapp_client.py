"""
MaatiGyan — WhatsApp Cloud API Client

Sends text messages and audio voice notes via Meta WhatsApp Business Cloud API.
DEMO MODE: Logs the message instead of making real API calls.
"""
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

WHATSAPP_API_BASE = "https://graph.facebook.com/v20.0"


async def send_text_message(
    phone_number: str,
    message: str,
    phone_number_id: str,
    access_token: str,
    demo_mode: bool = True,
) -> bool:
    """Send a WhatsApp text message to a phone number."""
    if demo_mode or not access_token or not phone_number_id:
        logger.info(f"[DEMO] WhatsApp → {phone_number}:\n{message[:200]}...")
        return True

    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message, "preview_url": False},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"WhatsApp message sent. Message ID: {data.get('messages', [{}])[0].get('id')}")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"WhatsApp API error {e.response.status_code}: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")
        return False


async def send_audio_message(
    phone_number: str,
    audio_url: str,
    phone_number_id: str,
    access_token: str,
    demo_mode: bool = True,
) -> bool:
    """Send an audio voice note via WhatsApp (requires public URL to audio file)."""
    if demo_mode or not access_token or not phone_number_id:
        logger.info(f"[DEMO] WhatsApp Audio → {phone_number}: {audio_url}")
        return True

    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "audio",
        "audio": {"link": audio_url},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            logger.info(f"WhatsApp audio sent to {phone_number}")
            return True
    except Exception as e:
        logger.error(f"WhatsApp audio send failed: {e}")
        return False


async def send_reaction(
    phone_number: str,
    message_id: str,
    emoji: str,
    phone_number_id: str,
    access_token: str,
    demo_mode: bool = True,
) -> bool:
    """Send an emoji reaction to a message (e.g., 🌱 to acknowledge location share)."""
    if demo_mode or not access_token:
        logger.info(f"[DEMO] Reaction {emoji} → {phone_number}")
        return True

    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "reaction",
        "reaction": {"message_id": message_id, "emoji": emoji},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Reaction send failed: {e}")
        return False


def parse_webhook_location(payload: dict) -> Optional[dict]:
    """
    Extract location data from a WhatsApp webhook payload.
    Returns dict with lat, lon, phone_number, message_id or None.
    """
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages", [])

        if not messages:
            return None

        msg = messages[0]
        msg_type = msg.get("type")
        from_number = msg.get("from")
        msg_id = msg.get("id")

        if msg_type == "location":
            loc = msg["location"]
            return {
                "lat": loc["latitude"],
                "lon": loc["longitude"],
                "phone_number": from_number,
                "message_id": msg_id,
                "address": loc.get("address", ""),
                "name": loc.get("name", ""),
            }

        # Handle text messages (instructions / language toggle)
        if msg_type == "text":
            text = msg["text"]["body"].strip().lower()
            return {
                "type": "text",
                "text": text,
                "phone_number": from_number,
                "message_id": msg_id,
            }

        return None

    except (KeyError, IndexError, TypeError) as e:
        logger.warning(f"Could not parse webhook payload: {e}")
        return None
