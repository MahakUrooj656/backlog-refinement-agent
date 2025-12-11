# backlog_refinement_agent/config.py

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


@dataclass
class JiraConfig:
    use_jira: bool = os.getenv("USE_JIRA", "1") == "1"
    base_url: str = os.getenv("JIRA_BASE_URL", "")
    email: str = os.getenv("JIRA_EMAIL", "")
    api_token: str = os.getenv("JIRA_API_TOKEN", "")
    project_key: str = os.getenv("JIRA_PROJECT_KEY", "")
    max_results: int = int(os.getenv("JIRA_MAX_RESULTS", "50"))
    local_file: str = os.getenv("LOCAL_FILE", "backlog.csv")


@dataclass
class SlackConfig:
    webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")

@dataclass
class OpenAIConfig:
    api_key: str = os.getenv("OPENAI_API_KEY", "")

@dataclass
class Settings:
    jira: JiraConfig = field(default_factory=JiraConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)


settings = Settings()
