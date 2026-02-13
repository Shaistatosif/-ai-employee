"""
Configuration management for Personal AI Employee System.

Loads settings from environment variables with validation.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Paths
    # ==========================================================================
    vault_path: Path = Field(
        default=Path("./obsidian_vault"),
        description="Path to Obsidian vault directory",
    )

    # ==========================================================================
    # Database
    # ==========================================================================
    neon_database_url: Optional[str] = Field(
        default=None,
        description="Neon PostgreSQL connection URL",
    )

    # ==========================================================================
    # Gmail API
    # ==========================================================================
    gmail_client_id: Optional[str] = Field(default=None)
    gmail_client_secret: Optional[str] = Field(default=None)
    gmail_refresh_token: Optional[str] = Field(default=None)

    # ==========================================================================
    # Twilio (WhatsApp)
    # ==========================================================================
    twilio_account_sid: Optional[str] = Field(default=None)
    twilio_auth_token: Optional[str] = Field(default=None)
    twilio_whatsapp_from: Optional[str] = Field(
        default=None,
        description="Twilio WhatsApp number (e.g., whatsapp:+14155238886)",
    )

    # ==========================================================================
    # Odoo Community (Accounting)
    # ==========================================================================
    odoo_url: Optional[str] = Field(
        default=None,
        description="Odoo Community URL (e.g., http://localhost:8069)",
    )
    odoo_db: Optional[str] = Field(default=None)
    odoo_username: Optional[str] = Field(default=None)
    odoo_password: Optional[str] = Field(default=None)

    # ==========================================================================
    # AI Provider
    # ==========================================================================
    anthropic_api_key: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)

    # ==========================================================================
    # System Settings
    # ==========================================================================
    dry_run: bool = Field(
        default=True,
        description="When True, no external actions are executed",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    watcher_interval: int = Field(
        default=30,
        description="Watcher poll interval in seconds",
    )
    health_check_port: int = Field(
        default=8080,
        description="Port for health check endpoint",
    )

    # ==========================================================================
    # Validators
    # ==========================================================================
    @field_validator("vault_path", mode="before")
    @classmethod
    def resolve_vault_path(cls, v: str | Path) -> Path:
        """Resolve vault path to absolute path."""
        path = Path(v)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return upper

    # ==========================================================================
    # Properties
    # ==========================================================================
    @property
    def needs_action_path(self) -> Path:
        """Path to Needs_Action folder."""
        return self.vault_path / "Needs_Action"

    @property
    def plans_path(self) -> Path:
        """Path to Plans folder."""
        return self.vault_path / "Plans"

    @property
    def pending_approval_path(self) -> Path:
        """Path to Pending_Approval folder."""
        return self.vault_path / "Pending_Approval"

    @property
    def approved_path(self) -> Path:
        """Path to Approved folder."""
        return self.vault_path / "Approved"

    @property
    def done_path(self) -> Path:
        """Path to Done folder."""
        return self.vault_path / "Done"

    @property
    def logs_path(self) -> Path:
        """Path to Logs folder."""
        return self.vault_path / "Logs"

    @property
    def briefings_path(self) -> Path:
        """Path to Briefings folder."""
        return self.vault_path / "Briefings"

    @property
    def drafts_path(self) -> Path:
        """Path to Drafts folder."""
        return self.vault_path / "Drafts"

    @property
    def multistep_path(self) -> Path:
        """Path to MultiStep task state folder."""
        return self.vault_path / "MultiStep"

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        directories = [
            self.vault_path,
            self.needs_action_path,
            self.plans_path,
            self.pending_approval_path,
            self.approved_path,
            self.done_path,
            self.logs_path,
            self.briefings_path,
            self.drafts_path,
            self.multistep_path,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def is_database_configured(self) -> bool:
        """Check if database is configured."""
        return self.neon_database_url is not None

    def is_gmail_configured(self) -> bool:
        """Check if Gmail API is configured."""
        return all([
            self.gmail_client_id,
            self.gmail_client_secret,
            self.gmail_refresh_token,
        ])

    def is_whatsapp_configured(self) -> bool:
        """Check if Twilio WhatsApp is configured."""
        return all([self.twilio_account_sid, self.twilio_auth_token])

    def is_odoo_configured(self) -> bool:
        """Check if Odoo Community is configured."""
        return all([self.odoo_url, self.odoo_db, self.odoo_username, self.odoo_password])


# Global settings instance
settings = Settings()
