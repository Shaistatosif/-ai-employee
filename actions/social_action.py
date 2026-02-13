"""
Social media draft actions for Personal AI Employee System.

Creates post drafts for Facebook, Instagram, and Twitter/X.
All social media posts require HITL approval before publishing.
"""

import logging
import re
from datetime import datetime
from pathlib import Path

from actions.base_action import BaseAction, ActionResult, ActionStatus
from config import settings

logger = logging.getLogger(__name__)


class FacebookDraftAction(BaseAction):
    """
    Creates Facebook post drafts for human review.

    Drafts saved to obsidian_vault/Drafts/Facebook/
    """

    def __init__(self):
        super().__init__(name="facebook_draft")

    def can_handle(self, task_data: dict) -> bool:
        task_type = task_data.get("type", "").lower()
        if task_type == "facebook_post":
            return True
        if task_type == "social_post":
            body = task_data.get("body", "").lower()
            raw = task_data.get("raw_content", "").lower()
            if "facebook" in body or "facebook" in raw or "fb" in body:
                return True
        return False

    def execute(self, task_data: dict, task_path: Path) -> ActionResult:
        return _create_social_draft(
            platform="Facebook",
            task_data=task_data,
            task_path=task_path,
            action_name=self.name,
            log_fn=self._log_execution,
        )


class InstagramDraftAction(BaseAction):
    """
    Creates Instagram post drafts for human review.

    Drafts saved to obsidian_vault/Drafts/Instagram/
    """

    def __init__(self):
        super().__init__(name="instagram_draft")

    def can_handle(self, task_data: dict) -> bool:
        task_type = task_data.get("type", "").lower()
        if task_type in ("instagram_post", "instagram_story"):
            return True
        if task_type == "social_post":
            body = task_data.get("body", "").lower()
            raw = task_data.get("raw_content", "").lower()
            if "instagram" in body or "instagram" in raw or "insta" in body:
                return True
        return False

    def execute(self, task_data: dict, task_path: Path) -> ActionResult:
        return _create_social_draft(
            platform="Instagram",
            task_data=task_data,
            task_path=task_path,
            action_name=self.name,
            log_fn=self._log_execution,
            extra_checklist=[
                "Image/video attached or described",
                "Caption length appropriate (< 2200 chars)",
                "Alt text provided for accessibility",
            ],
        )


class TwitterDraftAction(BaseAction):
    """
    Creates Twitter/X post drafts for human review.

    Drafts saved to obsidian_vault/Drafts/Twitter/
    """

    def __init__(self):
        super().__init__(name="twitter_draft")

    def can_handle(self, task_data: dict) -> bool:
        task_type = task_data.get("type", "").lower()
        if task_type in ("twitter_post", "tweet", "x_post"):
            return True
        if task_type == "social_post":
            body = task_data.get("body", "").lower()
            raw = task_data.get("raw_content", "").lower()
            if "twitter" in body or "twitter" in raw or "tweet" in body or " x " in body:
                return True
        return False

    def execute(self, task_data: dict, task_path: Path) -> ActionResult:
        return _create_social_draft(
            platform="Twitter",
            task_data=task_data,
            task_path=task_path,
            action_name=self.name,
            log_fn=self._log_execution,
            extra_checklist=[
                "Tweet within 280 character limit",
                "Thread formatted correctly (if applicable)",
            ],
        )


def _create_social_draft(
    platform: str,
    task_data: dict,
    task_path: Path,
    action_name: str,
    log_fn,
    extra_checklist: list[str] | None = None,
) -> ActionResult:
    """Shared logic for creating social media drafts across platforms."""
    logger.info(f"Creating {platform} draft for: {task_path.name}")

    # Extract post data
    body = task_data.get("body", "")
    raw = task_data.get("raw_content", "")
    title = task_data.get("title", "") or task_data.get("subject", f"{platform} Post")
    content = task_data.get("message", "") or task_data.get("post_content", "") or body
    audience = task_data.get("audience", "General audience")

    # Extract hashtags
    hashtags = task_data.get("hashtags", [])
    if not hashtags and isinstance(body, str):
        hashtags = re.findall(r"#(\w+)", body + " " + raw)

    # Create drafts directory
    platform_drafts = settings.drafts_path / platform
    platform_drafts.mkdir(parents=True, exist_ok=True)

    # Generate draft file
    now = datetime.now()
    safe_title = "".join(
        c if c.isalnum() or c in "-_ " else "_" for c in title
    )[:40].strip()
    filename = f"draft_{now.strftime('%Y%m%d_%H%M%S')}_{safe_title}.md"
    draft_path = platform_drafts / filename

    hashtag_str = (
        " ".join(f"#{h}" for h in hashtags) if hashtags else "# Add relevant hashtags"
    )

    # Build checklist
    checklist_items = [
        "Content is appropriate for the platform",
        "No confidential information included",
        "Hashtags are relevant",
        "Tone matches brand voice",
        "No spelling/grammar errors",
    ]
    if extra_checklist:
        checklist_items.extend(extra_checklist)
    checklist = "\n".join(f"- [ ] {item}" for item in checklist_items)

    draft_content = f"""---
type: {platform.lower()}_post
status: draft
created: '{now.isoformat()}'
audience: '{audience}'
platform: {platform.lower()}
requires_approval: true
---

# {platform} Post Draft

**Created**: {now.strftime('%Y-%m-%d %H:%M')}
**Status**: Draft - Requires Review
**Platform**: {platform}
**Target Audience**: {audience}

---

## Post Content

{content}

---

## Hashtags

{hashtag_str}

---

## Review Checklist

{checklist}

---

## Instructions

1. Review and edit the post content above
2. Update hashtags as needed
3. When ready, manually post to {platform}
4. Move this file to Done/ after publishing

---

*Draft generated by AI Employee System*
*All social media posts require human review before publishing*
"""

    draft_path.write_text(draft_content, encoding="utf-8")

    result = ActionResult(
        status=ActionStatus.SUCCESS,
        message=f"{platform} draft created: {draft_path.name}",
        data={
            "draft_path": str(draft_path),
            "platform": platform,
            "title": title,
            "hashtags": hashtags,
        },
    )
    log_fn(task_path, result, {"draft_path": str(draft_path), "platform": platform})

    logger.info(f"{platform} draft created: {draft_path}")
    return result
