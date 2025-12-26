import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
    GITHUB_PRIVATE_KEY_PATH = os.getenv("GITHUB_PRIVATE_KEY_PATH")
    GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
    PORT = int(os.getenv("PORT", 3000))

    # LLM Configuration
    LLM_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("BASE_URL") or os.getenv("LLM_BASE_URL")
    LLM_MODEL = os.getenv("MODEL") or os.getenv("LLM_MODEL", "GLM-4.6")

    # Enhanced Vulnerability Detection Configuration
    VULN_RISK_THRESHOLD_LOGIC = int(os.getenv("VULN_RISK_THRESHOLD_LOGIC", 60))
    VULN_RISK_THRESHOLD_SECURITY = int(os.getenv("VULN_RISK_THRESHOLD_SECURITY", 35))
    VULN_MAX_UNITS_LOGIC = int(os.getenv("VULN_MAX_UNITS_LOGIC", 12))
    VULN_MAX_UNITS_SECURITY = int(os.getenv("VULN_MAX_UNITS_SECURITY", 10))

    @classmethod
    def get_private_key(cls) -> str:
        if not cls.GITHUB_PRIVATE_KEY_PATH:
            raise ValueError("GITHUB_PRIVATE_KEY_PATH not set")
        with open(cls.GITHUB_PRIVATE_KEY_PATH, "r") as f:
            return f.read()

    @classmethod
    def validate(cls):
        required = ["GITHUB_APP_ID", "GITHUB_PRIVATE_KEY_PATH", "GITHUB_WEBHOOK_SECRET"]
        missing = [var for var in required if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
