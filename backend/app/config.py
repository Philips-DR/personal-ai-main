from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # User profile — who this assistant serves
    # -------------------------------------------------------------------------
    user_name: str = "Phil"
    user_id: str = "phil"          # DB key for preferences row
    user_email: str = "philip@ayadata.ai"
    user_job_title: str = "AI/ML Engineer"
    user_company: str = "AyaData"

    # -------------------------------------------------------------------------
    # AWS Bedrock
    # -------------------------------------------------------------------------
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_bearer_token_bedrock: str = ""
    claude_model_id: str = "anthropic.claude-sonnet-4-6-20250514-v1:0"
    titan_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    titan_model_id: str = "amazon.titan-embed-text-v2:0"  # Alias used by memory module

    # -------------------------------------------------------------------------
    # PostgreSQL (local Docker via asyncpg)
    # -------------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://assistant:assistant@localhost:5432/assistant"

    # -------------------------------------------------------------------------
    # OAuth token encryption (Fernet key — see scripts/generate_key.py)
    # -------------------------------------------------------------------------
    oauth_token_encryption_key: str = ""

    # -------------------------------------------------------------------------
    # Gmail OAuth 2.0
    # -------------------------------------------------------------------------
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://localhost:8000/api/auth/gmail/callback"

    # -------------------------------------------------------------------------
    # Transcription
    # -------------------------------------------------------------------------
    assemblyai_api_key: str = ""
    transcription_provider: str = "assemblyai"  # "assemblyai" | "whisper"
    # tiny|base|small|medium|large-v2 — balances RAM usage vs. accuracy
    whisper_model_size: str = "base"

    # -------------------------------------------------------------------------
    # GitHub
    # -------------------------------------------------------------------------
    github_token: str = ""
    github_api_base_url: str = "https://api.github.com"
    github_analyze_max_files: int = 100         # max tree entries sent to Claude
    github_file_content_max_length: int = 2000  # chars per file in context
    github_analyze_max_context: int = 12000     # total chars of file content
    github_max_key_files: int = 25              # files fetched for analysis

    # -------------------------------------------------------------------------
    # Google Drive / Docs / Sheets
    # -------------------------------------------------------------------------
    drive_search_max_results: int = 10
    default_doc_title: str = "New Document"
    default_sheet_range: str = "Sheet1!A:Z"

    # -------------------------------------------------------------------------
    # Morning Brief
    # -------------------------------------------------------------------------
    brief_cron_expression: str = "0 7 * * *"
    brief_timezone: str = "Africa/Lagos"
    brief_delivery_email: str = ""  # Self-email; blank disables email delivery
    brief_priority_emails_limit: int = 10
    brief_action_items_limit: int = 10
    brief_roadmaps_limit: int = 2
    brief_habits_limit: int = 3
    brief_interests_limit: int = 3
    brief_skill_goals_limit: int = 2

    # -------------------------------------------------------------------------
    # Email module
    # -------------------------------------------------------------------------
    email_threads_limit: int = 10         # threads returned by read/list
    email_triage_limit: int = 10          # unclassified threads processed per triage
    email_poll_max_results: int = 20      # Gmail threads fetched per poll
    email_snippet_max_length: int = 300   # chars of body stored as snippet
    email_subject_display_length: int = 50
    email_summarize_limit: int = 5        # threads offered for summarization

    # -------------------------------------------------------------------------
    # Meeting module
    # -------------------------------------------------------------------------
    transcript_max_length: int = 8000   # chars sent to Claude for processing
    transcript_db_max_length: int = 5000  # chars stored in DB

    # -------------------------------------------------------------------------
    # Orchestrator / intent classification
    # -------------------------------------------------------------------------
    intent_confidence_threshold: float = 0.6
    conversation_history_limit: int = 6  # messages included (= 3 exchanges)

    # -------------------------------------------------------------------------
    # Memory / RAG
    # -------------------------------------------------------------------------
    max_context_tokens: int = 150000
    max_memory_entries_per_query: int = 10
    embedding_batch_size: int = 20
    context_memory_limit: int = 5  # entries injected into prompt context

    # -------------------------------------------------------------------------
    # Learning Coach defaults
    # -------------------------------------------------------------------------
    default_experience_level: str = "intermediate"
    default_daily_minutes: int = 60
    default_duration_weeks: int = 12

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_env: str = "development"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
