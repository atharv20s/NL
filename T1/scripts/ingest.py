"""
ingest.py — Email/file ingestion layer.

Supports two modes:
  - "dry-run": reads CSV files from a local directory (no Gmail needed).
  - "live":    searches Gmail inbox via the Google Gmail REST API using OAuth2.

In live mode, credentials.json must exist at GMAIL_CREDENTIALS_PATH
(default: ~/analytics-reports/.gmail-credentials.json).
The OAuth2 token is cached at GMAIL_TOKEN_PATH
(default: ~/analytics-reports/.gmail-token.json).
"""

from __future__ import annotations

import logging
import os
import base64
import json
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

GMAIL_SCOPES        = ["https://www.googleapis.com/auth/gmail.readonly"]
GMAIL_CREDS_PATH    = Path.home() / "analytics-reports" / ".gmail-credentials.json"
GMAIL_TOKEN_PATH    = Path.home() / "analytics-reports" / ".gmail-token.json"
GMAIL_SENDER_FILTER = "google-analytics-noreply@google.com OR analytics-noreply@google.com"
SUBJECT_FILTER      = "Scheduled report"


@dataclass
class IngestedFile:
    path: str               # local temp/raw path
    original_filename: str
    source: str             # "local" | "gmail"
    email_subject: Optional[str]
    email_date: Optional[str]


# ── Dry-run mode ──────────────────────────────────────────────────────────────

def ingest_local(source_dir: str) -> list[IngestedFile]:
    """
    Ingest all .csv files from a local directory.

    Args:
        source_dir: Path to directory containing CSV files.

    Returns:
        List of IngestedFile.
    """
    src = Path(source_dir)
    if not src.exists():
        raise FileNotFoundError(f"Source directory does not exist: {src}")

    csvs = sorted(src.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No .csv files found in: {src}")

    result: list[IngestedFile] = []
    for csv_path in csvs:
        log.info("  [local] Found: %s", csv_path.name)
        result.append(IngestedFile(
            path=str(csv_path),
            original_filename=csv_path.name,
            source="local",
            email_subject=None,
            email_date=None,
        ))

    log.info("Ingested %d local CSV file(s) from %s", len(result), src)
    return result


# ── Live Gmail mode ───────────────────────────────────────────────────────────

def _get_gmail_credentials():
    """
    Return valid Google OAuth2 credentials.
    If a cached token exists, refreshes it if needed.
    If no token, runs the OAuth flow (requires a browser or device flow).
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise ImportError(
            "google-auth-oauthlib is not installed. Run: pip install google-auth-oauthlib"
        )

    creds = None

    if GMAIL_TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_PATH), GMAIL_SCOPES)
        except Exception as e:
            log.warning("Could not load cached token (%s). Re-authenticating.", e)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing Gmail OAuth2 token…")
            creds.refresh(Request())
        else:
            if not GMAIL_CREDS_PATH.exists():
                raise FileNotFoundError(
                    f"Gmail credentials.json not found at: {GMAIL_CREDS_PATH}\n"
                    "See README.md for Gmail OAuth2 setup instructions."
                )
            log.info("Starting Gmail OAuth2 flow…")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GMAIL_CREDS_PATH), GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for next run
        GMAIL_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(GMAIL_TOKEN_PATH, "w") as fh:
            fh.write(creds.to_json())
        log.info("Gmail token saved: %s", GMAIL_TOKEN_PATH)

    return creds


def ingest_gmail(output_dir: Path) -> list[IngestedFile]:
    """
    Search Gmail for scheduled GA4 report emails in the last 7 days.
    Download CSV attachments to output_dir.

    Args:
        output_dir: Directory where attachments will be saved temporarily.

    Returns:
        List of IngestedFile.
    """
    try:
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "google-api-python-client is not installed. Run: pip install google-api-python-client"
        )

    creds   = _get_gmail_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    # Build search query — last 7 days, from GA4 noreply, has attachment
    after_date = (date.today() - timedelta(days=7)).strftime("%Y/%m/%d")
    query = (
        f'has:attachment filename:csv after:{after_date} '
        f'(from:google-analytics-noreply@google.com OR from:analytics-noreply@google.com '
        f'OR subject:"Scheduled report" OR subject:"Google Analytics")'
    )

    log.info("Gmail search query: %s", query)
    response = service.users().messages().list(userId="me", q=query).execute()
    messages = response.get("messages", [])
    log.info("Gmail: found %d matching email(s)", len(messages))

    if not messages:
        log.warning(
            "No matching emails found. Make sure scheduled reports are configured "
            "and have been delivered to your inbox in the last 7 days."
        )
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    result: list[IngestedFile] = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers  = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        subject  = headers.get("Subject", "")
        email_dt = headers.get("Date", "")

        log.info("  Processing email: %s", subject)

        parts = _get_parts(msg["payload"])
        for part in parts:
            filename = part.get("filename", "")
            if not filename.lower().endswith(".csv"):
                continue

            body = part.get("body", {})
            attachment_id = body.get("attachmentId")
            if attachment_id:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=msg_ref["id"], id=attachment_id
                ).execute()
                data = att["data"]
            else:
                data = body.get("data", "")

            if not data:
                log.warning("  Empty attachment body for: %s", filename)
                continue

            csv_bytes = base64.urlsafe_b64decode(data + "==")
            dest = output_dir / filename
            dest.write_bytes(csv_bytes)
            log.info("  [gmail] Saved attachment: %s (%d bytes)", filename, len(csv_bytes))

            result.append(IngestedFile(
                path=str(dest),
                original_filename=filename,
                source="gmail",
                email_subject=subject,
                email_date=email_dt,
            ))

    log.info("Gmail ingestion complete: %d CSV attachment(s) downloaded", len(result))
    return result


def _get_parts(payload: dict) -> list[dict]:
    """Recursively extract all MIME parts from a Gmail message payload."""
    parts = []
    if "parts" in payload:
        for part in payload["parts"]:
            parts.extend(_get_parts(part))
    else:
        parts.append(payload)
    return parts


# ── Auth-only helper ──────────────────────────────────────────────────────────

def authenticate_only():
    """Run OAuth2 flow and cache token without fetching any emails."""
    _get_gmail_credentials()
    log.info("Gmail authentication successful. Token cached at: %s", GMAIL_TOKEN_PATH)
