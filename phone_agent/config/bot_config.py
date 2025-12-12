import os
import yaml
from typing import Optional

from phone_agent.model import ModelConfig
from phone_agent.agent import AgentConfig


class BotConfig:
    def __init__(self, config_path: str = "config/bot_config.yaml"):
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Please create it with your bot configuration."
            )

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    @property
    def token(self) -> str:
        return self.config['telegram']['token']

    @property
    def allowed_user_id(self) -> int:
        return self.config['telegram']['allowed_user_id']

    @property
    def device_id(self) -> Optional[str]:
        return self.config['agent'].get('device_id')

    @property
    def model_config(self) -> ModelConfig:
        return ModelConfig(
            base_url=self.config['model']['base_url'],
            model_name=self.config['model']['model_name'],
            api_key=self.config['model'].get('api_key', 'EMPTY')
        )

    @property
    def agent_config(self) -> AgentConfig:
        return AgentConfig(
            max_steps=self.config['agent'].get('max_steps', 100),
            device_id=self.device_id,
            verbose=self.config['agent'].get('verbose', True),
            lang=self.config['agent'].get('lang', 'cn')
        )

    @property
    def lark_app_id(self) -> str:
        return self.config.get('lark', {}).get('app_id', '')

    @property
    def lark_app_secret(self) -> str:
        return self.config.get('lark', {}).get('app_secret', '')

    @property
    def lark_verification_token(self) -> str:
        return self.config.get('lark', {}).get('verification_token', '')

    @property
    def lark_allowed_users(self) -> list:
        return self.config.get('lark', {}).get('allowed_users', [])
