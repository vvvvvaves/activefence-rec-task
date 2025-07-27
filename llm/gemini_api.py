import os
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types
import json

load_dotenv()
MODEL_NAME = "gemini-2.5-flash-lite"

def get_client():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return client

# "Implicit caching is enabled by default for all Gemini 2.5 models. 
# We automatically pass on cost savings if your request hits caches. 
# There is nothing you need to do in order to enable this. It is effective as of May 8th, 2025. 
# The minimum input token count for context caching is 1,024 for 2.5 Flash and 2,048 for 2.5 Pro."
# https://ai.google.dev/gemini-api/docs/caching?lang=python

def gemini_generate_structured(
    client,
    input_prompt: str,
    system_instruction: str,
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
        system_instruction=system_instruction,
        thinking_config=types.ThinkingConfig(include_thoughts=True)
    )
    response = client.models.generate_content(
        model=model_name,
        contents=input_prompt,
        config=config,
    )

    return response

if __name__ == "__main__":
    input_prompt = "[User ID: 1234567890, Post ID: 1234567890, Comment ID: 1234567890] There are too many Jews in the U.S. government. Is this antisemitic?"
    system_instruction = "You are a helpful assistant that assesses the antisemitism of a given text."
    with open('../data/schemas/gemini_llm_schema.json', 'r') as f:
        schema = json.load(f)
    client = get_client()
    response = gemini_generate_structured(
        client=client, 
        input_prompt=input_prompt, 
        system_instruction=system_instruction, 
        response_schema=schema
    )
    response = json.loads(response.text)
    print(response, type(response))