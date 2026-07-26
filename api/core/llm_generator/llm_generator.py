from common.entites import ModelProvider
from config.settings import settings
from core.llm_generator.prompts import GENERATOR_QA_PROMPT
from core.model_manager import ModelManager
from core.model_runtime.message_entities import PromptMessage, SystemPromptMessage, UserPromptMessage


class LLMGenerator:
    async def generate_qa_document(self, content: str, language: str) -> str:
        """生成Q-A问答对"""
        prompt = GENERATOR_QA_PROMPT.format(language=language)
        prompt_messages: list[PromptMessage] = [SystemPromptMessage(content=prompt), UserPromptMessage(content=content)]
        model_manager = ModelManager(
            settings.QA_MODEL_NAME,
            ModelProvider.OPENAI,
        )
        instance = model_manager.get_model_instance()
        resp = ""
        async for chunk in instance.invoke_llm_stream(prompt_messages):
            resp += chunk
        return resp
