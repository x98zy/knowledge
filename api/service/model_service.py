from common.entites import ModelConfig, ModelProvider
from config.settings import settings


class ModelService:
    @classmethod
    def get_model(cls, model_name: str, provider_name: str) -> ModelConfig:
        provider = ModelProvider.value_of(provider_name) if isinstance(provider_name, str) else provider_name
        for model in settings.MODELS:
            if model.name == model_name and model.provider == provider:
                return model
        raise ValueError(f"Model {model_name} not found in provider {provider_name}")
