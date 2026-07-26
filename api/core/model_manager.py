from collections.abc import AsyncGenerator

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from common.entites import ModelConfig
from core.model_runtime.message_entities import (
    AudioPromptMessageContent,
    DocumentPromptMessageContent,
    ImagePromptMessageContent,
    PromptMessage,
    TextPromptMessageContent,
    VideoPromptMessageContent,
)
from service.model_service import ModelService


class ModelInstance:
    def __init__(self, model: ModelConfig):
        self._client = AsyncOpenAI(
            api_key=model.config.get("api_key"),
            base_url=model.config.get("base_url"),
        )
        self._model_name = model.name

    def _convert_messages(self, prompt_messages: list[PromptMessage]) -> list[ChatCompletionMessageParam]:
        """
        将内部消息格式转换为OpenAI API所需的格式
        :param prompt_messages: 内部消息列表
        :return: OpenAI格式的消息列表
        """
        messages: list[ChatCompletionMessageParam] = []

        for msg in prompt_messages:
            role = msg.rule.value

            content: str | list[dict[str, str | dict[str, str]]]
            if isinstance(msg.content, str):
                content = msg.content
            elif isinstance(msg.content, list):
                content = []
                for item in msg.content:
                    if isinstance(item, TextPromptMessageContent):
                        content.append({"type": "text", "text": item.data})
                    elif isinstance(item, ImagePromptMessageContent):
                        content.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": item.data, "detail": item.detail.value},
                            }
                        )
                    elif isinstance(
                        item, (AudioPromptMessageContent, VideoPromptMessageContent, DocumentPromptMessageContent)
                    ):
                        content.append({"type": "text", "text": item.data})
                    else:
                        content.append({"type": "text", "text": str(item)})
            else:
                content = ""

            messages.append({"role": role, "content": content})

        return messages

    async def invoke_llm(self, prompt_messages: list[PromptMessage], model_params: dict | None = None) -> str:
        """
        调用LLM模型（同步方式）
        :param prompt_messages: 输入的提示消息
        :return: 模型的响应
        """
        if model_params is None:
            model_params = {}
        messages = self._convert_messages(prompt_messages)

        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            **model_params,
        )

        return response.choices[0].message.content or ""

    async def invoke_llm_stream(
        self, prompt_messages: list[PromptMessage], model_params: dict | None = None
    ) -> AsyncGenerator[str, None]:
        """
        调用LLM模型（流式方式）
        :param prompt_messages: 输入的提示消息
        :return: 流式响应的异步生成器
        """
        if model_params is None:
            model_params = {}
        messages = self._convert_messages(prompt_messages)

        stream = await self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            stream=True,
            **model_params,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


class ModelManager:
    def __init__(self, model_name: str, provider_name: str):
        self.model_name = model_name
        self.provider_name = provider_name

    def get_model_instance(self) -> ModelInstance:
        model = ModelService.get_model(self.model_name, self.provider_name)
        return ModelInstance(model)
