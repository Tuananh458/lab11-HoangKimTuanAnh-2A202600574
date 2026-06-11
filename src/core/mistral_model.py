import os
import httpx
from typing import AsyncGenerator
from google.genai import types
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.models.registry import LLMRegistry

class MistralLlm(BaseLlm):
    @classmethod
    def supported_models(cls) -> list[str]:
        # Match Mistral model names
        return [r"pixtral-.*", r"mistral-.*", r"open-mixtral-.*", r"codestral-.*", r"mistral:.*"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        # Get api key and model name
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is not set in environment.")

        model_name = self.model  # e.g., 'pixtral-12b-latest'

        # Format messages
        messages = []
        if llm_request.config and llm_request.config.system_instruction:
            messages.append({
                "role": "system",
                "content": llm_request.config.system_instruction
            })

        for content in llm_request.contents:
            role = "user" if content.role == "user" else "assistant"
            text_content = ""
            for part in content.parts:
                if hasattr(part, "text") and part.text:
                    text_content += part.text
            messages.append({
                "role": role,
                "content": text_content
            })

        # Call Mistral API via httpx
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_name,
            "messages": messages,
            "temperature": llm_request.config.temperature if (llm_request.config and llm_request.config.temperature is not None) else 0.3
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=data)
            if resp.status_code != 200:
                raise RuntimeError(f"Mistral API error: {resp.status_code} - {resp.text}")
            
            result_json = resp.json()
            reply = result_json["choices"][0]["message"]["content"]

        # Yield response
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=reply)]
            ),
            partial=False
        )

# Register the MistralLlm in LLMRegistry
LLMRegistry.register(MistralLlm)
