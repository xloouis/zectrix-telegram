#!/usr/bin/env python3
"""
Fetch latest messages from public Telegram channels and push to Zectrix e-ink device.
"""

import argparse
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

# Enable DEBUG logging if DEBUG env var is set
if os.getenv("DEBUG"):
    logger.setLevel(logging.DEBUG)

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
        # Look for the main message text (not reply text)
        message_text_div = latest_message.find("div", class_="js-message_text")

        if not message_text_div:
            logger.warning(f"Latest message in {channel} has no text")
            return None

        logger.debug(f"Message div HTML: {str(message_text_div)[:500]}")

        # Replace <br/> tags with newlines
        br_count = len(message_text_div.find_all("br"))
        logger.debug(f"Found {br_count} <br/> tags in message")

        for br in message_text_div.find_all("br"):
            br.replace_with("\n")

        message_text = message_text_div.get_text()

        logger.debug(f"Raw message text: {repr(message_text[:200])}")
        logger.debug(f"Newline count in message: {message_text.count(chr(10))}")

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

    logger.debug(f"Page {page_id} - Title: {title}")
    logger.debug(f"Page {page_id} - Body: {body}")

    payload = {
        "title": title,
        "body": body[:5000],  # Zectrix limit is 5000 chars
        "fontSize": 12,
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
    parser = argparse.ArgumentParser(description="Fetch Telegram messages and push to Zectrix device")
    parser.add_argument("--dry-run", action="store_true", help="Generate content but do not push to device")
    args = parser.parse_args()

    try:
        config = get_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    api_key = config["api_key"]
    device_id = config["device_id"]
    channels = config["channels"]

    logger.info(f"Starting fetch from {len(channels)} channels")
    if args.dry_run:
        logger.info("DRY RUN MODE: Content will be generated but not pushed")

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

    # Delete all pages first (skip in dry-run)
    if not args.dry_run:
        logger.info("Deleting all existing pages")
        if not delete_all_pages(api_key, device_id):
            logger.error("Failed to delete pages, aborting push")
            return
    else:
        logger.info("[DRY RUN] Would delete all existing pages")

    # Push messages to pages 1-5
    for page_id, message_text in enumerate(messages, start=1):
        lines = message_text.split('\n', 1)
        title = lines[0][:200]
        body = lines[1] if len(lines) > 1 else ""

        logger.info(f"Pushing message to page {page_id}")
        logger.debug(f"Page {page_id} - Title: {title}")
        logger.debug(f"Page {page_id} - Body: {body}")

        if not args.dry_run:
            success = push_to_zectrix(api_key, device_id, message_text, page_id)
            if not success:
                logger.warning(f"Failed to push message to page {page_id}")
        else:
            logger.info(f"[DRY RUN] Would push to page {page_id}")

    logger.info(f"Completed: pushed {len(messages)} messages to pages 1-{len(messages)}")


if __name__ == "__main__":
    main()
