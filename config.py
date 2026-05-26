"""
Configuration module using Pydantic for environment variable management.
All API keys, endpoints, and credentials are centralized here.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import os


class PipelineConfig(BaseSettings):
    """
    Central configuration manager for the ebook production pipeline.
    Reads all environment variables and validates required credentials.
    """

    # OpenAI Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for standard models (GPT-4, etc.)"
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI base URL"
    )

    # OpenRouter Configuration (custom base URL for open-weights models)
    openrouter_api_key: str = Field(
        default="",
        description="OpenRouter API key for open-weights model access"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter base URL for alternative model endpoints"
    )

    # HuggingFace Configuration
    huggingface_token: str = Field(
        default="",
        description="HuggingFace Hub authentication token"
    )
    huggingface_repo_id: Optional[str] = Field(
        default=None,
        description="Default HuggingFace repository for dataset pulls"
    )

    # Airtable Configuration
    airtable_token: str = Field(
        default="",
        description="Airtable personal access token (PAT)"
    )
    airtable_base_id: str = Field(
        default="",
        description="Airtable Base ID for ebook metadata storage"
    )
    airtable_table_name: str = Field(
        default="Books",
        description="Airtable table name for tracking book production"
    )

    # Google Tasks Configuration
    google_tasks_enabled: bool = Field(
        default=False,
        description="Enable Google Tasks integration for review workflows"
    )
    google_tasks_list_id: Optional[str] = Field(
        default=None,
        description="Google Tasks List ID for human review workflows"
    )
    google_service_account_json: Optional[str] = Field(
        default=None,
        description="Path to Google service account JSON file or JSON string"
    )

    # Pandoc Configuration
    pandoc_path: str = Field(
        default="pandoc",
        description="Path to pandoc executable or command name"
    )
    pandoc_defaults_dir: str = Field(
        default="./pandoc_defaults",
        description="Directory containing pandoc default configuration files"
    )

    # Pipeline Configuration
    pipeline_log_dir: str = Field(
        default="./logs",
        description="Directory for storing pipeline execution logs"
    )
    pipeline_state_dir: str = Field(
        default="./state",
        description="Directory for fallback state JSON files"
    )
    content_output_dir: str = Field(
        default="./output",
        description="Directory for generated EPUB/PDF output files"
    )
    content_source_dir: str = Field(
        default="./content",
        description="Directory containing source markdown files"
    )

    # LLM Model Selection
    default_openai_model: str = Field(
        default="gpt-4-turbo",
        description="Default OpenAI model for creative content generation"
    )
    default_openrouter_model: str = Field(
        default="mistralai/mistral-7b-instruct",
        description="Default OpenRouter model for semantic editing/extraction"
    )

    # Execution Configuration
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for API calls"
    )
    request_timeout_seconds: int = Field(
        default=30,
        description="API request timeout in seconds"
    )
    enable_fallback_mode: bool = Field(
        default=True,
        description="Enable local JSON state fallback when services are unavailable"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("pipeline_log_dir", "pipeline_state_dir", "content_output_dir", "content_source_dir", pre=True)
    def create_directories(cls, v):
        """Auto-create required directories if they don't exist."""
        if v:
            os.makedirs(v, exist_ok=True)
        return v

    def validate_critical_credentials(self) -> dict:
        """
        Validate that at least one LLM provider has credentials.
        Returns a dict with validation results.
        """
        results = {
            "openai_configured": bool(self.openai_api_key),
            "openrouter_configured": bool(self.openrouter_api_key),
            "airtable_configured": bool(self.airtable_token and self.airtable_base_id),
            "huggingface_configured": bool(self.huggingface_token),
            "google_tasks_configured": self.google_tasks_enabled and bool(self.google_service_account_json),
        }
        
        if not (results["openai_configured"] or results["openrouter_configured"]):
            raise ValueError(
                "At least one LLM provider (OpenAI or OpenRouter) must be configured with valid credentials."
            )
        
        return results


# Instantiate global config on module load
config = PipelineConfig()
