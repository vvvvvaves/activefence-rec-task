import os
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types
import json

load_dotenv()
MODEL_NAME = "gemini-2.5-flash-lite"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# "Implicit caching is enabled by default for all Gemini 2.5 models. 
# We automatically pass on cost savings if your request hits caches. 
# There is nothing you need to do in order to enable this. It is effective as of May 8th, 2025. 
# The minimum input token count for context caching is 1,024 for 2.5 Flash and 2,048 for 2.5 Pro."
# https://ai.google.dev/gemini-api/docs/caching?lang=python

def gemini_generate(
    prompt: str,
    model_name: str = MODEL_NAME,
    temperature: float = 0.7,
    max_output_tokens: int = 200,
    top_p: float = 0.95,
    top_k: int = 40,
) -> str:
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        top_k=top_k,
    )
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )
    return response.text

# Structured output example
def gemini_generate_structured(
    prompt: str,
    response_schema: dict,
    model_name: str = MODEL_NAME,
    temperature: float = 0.7,
    max_output_tokens: int = 200,
    top_p: float = 0.95,
    top_k: int = 40,
) -> dict:
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        top_p=top_p,
        top_k=top_k,
        response_mime_type="application/json",
        response_schema=response_schema,
        thinking_config=types.ThinkingConfig(
        include_thoughts=True
      )
    )
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )

    # Extract text and usage metadata
    response_dict = {
        "text": response.text,
        "usage_metadata": dict(response.usage_metadata) if response.usage_metadata else None,
        # You can add more fields as needed, e.g.:
        # "candidates": [c.text for c in response.candidates] if hasattr(response, "candidates") else None,
    }

    return response_dict

if __name__ == "__main__":
    prompt = "There are too many Jews in the U.S. government. Is this antisemitic?"
    schema = {
    "type": "object",
    "properties": {
        "is_antisemitic": {"type": "boolean"},
        "reasoning": {"type": "string"}
    },
    "required": ["is_antisemitic", "reasoning"]
    }
    response = gemini_generate_structured(prompt, schema)
    print(response)