#!/usr/bin/env python3
"""
Fetch latest messages from public Telegram channels and push to Zectrix e-ink device.
"""

import json
import os
import sys
import logging
from typing import Optional
from bs4 import BeautifulSoup

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

ZECTRIX_BASE_URL = "https://cloud.zectrix.com/open/v1"
TELEGRAM_WEB_URL = "https://t.me"


def get_config() -> dict:
    """Load configuration from environment variables."""
    api_key = os.getenv("ZECTRIX_API_KEY")
    device_id = os.getenv("ZECTRIX_DEVICE_ID")
    channels_json = os.getenv("TELEGRAM_CHANNELS")

    if not api_key:
        raise ValueError("ZECTRIX_API_KEY not set")
    if not device_id:
        raise ValueError("ZECTRIX_DEVICE_ID not set")
    if not channels_json:
        raise ValueError("TELEGRAM_CHANNELS not set")

    try:
        channels = json.loads(channels_json)
        if not isinstance(channels, list):
            raise ValueError("TELEGRAM_CHANNELS must be a JSON array")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid TELEGRAM_CHANNELS JSON: {e}")

    return {
        "api_key": api_key,
        "device_id": device_id,
        "channels": channels,
    }


def fetch_latest_message(channel: str) -> Optional[str]:
    """Fetch the latest message text from a public Telegram channel via web scraping."""
    url = f"{TELEGRAM_WEB_URL}/s/{channel}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Find all message divs and get the latest one
        messages = soup.find_all("div", class_="tgme_widget_message")

        if not messages:
            logger.warning(f"No messages found in {channel}")
            return None

        # Get the last (latest) message
        latest_message = messages[-1]
        message_text_div = latest_message.find("div", class_="tgme_widget_message_text")

        if not message_text_div:
            logger.warning(f"Latest message in {channel} has no text")
            return None

        message_text = message_text_div.get_text(strip=True)

        if not message_text:
            logger.warning(f"Latest message in {channel} has no text")
            return None

        logger.info(f"Fetched message from {channel}: {len(message_text)} chars")
        return message_text

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching from {channel}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error processing {channel}: {e}")
        return None


def delete_all_pages(api_key: str, device_id: str) -> bool:
    """Delete all pages on the Zectrix device."""
    url = f"{ZECTRIX_BASE_URL}/devices/{device_id}/display/pages"
    headers = {
        "X-API-Key": api_key,
    }

    try:
        response = requests.delete(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        logger.info(f"Delete all pages response: {data}")

        if data.get("code") == 0:
            logger.info(f"Successfully deleted all pages on device {device_id}")
            return True
        else:
            logger.error(f"Failed to delete pages: {data.get('msg', 'Unknown error')}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to delete pages: {e}")
        return False


def push_to_zectrix(api_key: str, device_id: str, text: str, page_id: int) -> bool:
    """Push text to Zectrix device on a specific page using structured-text."""
    url = f"{ZECTRIX_BASE_URL}/devices/{device_id}/display/structured-text"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }

    # Split title and body
    lines = text.split('\n', 1)
    title = lines[0][:200]  # First line as title, max 200 chars
    body = lines[1] if len(lines) > 1 else ""  # Rest as body

    payload = {
        "title": title,
        "body": body[:5000],  # Zectrix limit is 5000 chars
        "pageId": str(page_id),
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        logger.info(f"Zectrix API response for page {page_id}: {data}")

        if data.get("code") == 0:
            logger.info(f"Successfully pushed to device {device_id} on page {page_id}")
            return True
        else:
            logger.error(f"Zectrix API error: {data.get('msg', 'Unknown error')}")
            logger.error(f"Full response: {data}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to push to Zectrix: {e}")
        return False


def main():
    """Main entry point."""
    try:
        config = get_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    api_key = config["api_key"]
    device_id = config["device_id"]
    channels = config["channels"]

    logger.info(f"Starting fetch from {len(channels)} channels")

    # Fetch messages from channels (max 5)
    messages = []
    for channel in channels:
        if len(messages) >= 5:
            logger.info("Reached maximum of 5 messages, stopping fetch")
            break

        logger.info(f"Processing channel: {channel}")
        message_text = fetch_latest_message(channel)

        if message_text:
            messages.append(message_text)
            logger.info(f"Added message from {channel} (total: {len(messages)})")
        else:
            logger.info(f"Skipping {channel} - no message text to push")

    if not messages:
        logger.warning("No messages fetched from any channel")
        return

    # Delete all pages first
    logger.info("Deleting all existing pages")
    if not delete_all_pages(api_key, device_id):
        logger.error("Failed to delete pages, aborting push")
        return

    # Push messages to pages 1-5
    for page_id, message_text in enumerate(messages, start=1):
        logger.info(f"Pushing message to page {page_id}")
        success = push_to_zectrix(api_key, device_id, message_text, page_id)
        if not success:
            logger.warning(f"Failed to push message to page {page_id}")

    logger.info(f"Completed: pushed {len(messages)} messages to pages 1-{len(messages)}")


if __name__ == "__main__":
    main()
