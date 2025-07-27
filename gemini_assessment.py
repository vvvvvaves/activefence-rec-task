import os
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types
import json

load_dotenv()
MODEL_NAME = "gemini-1.5-flash"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
    )
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )
    # The response.text should be a JSON string
    return json.loads(response.text)

if __name__ == "__main__":
    prompt = "List a few popular cookie recipes."
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "recipe_name": {"type": "string"},
                "calories": {"type": "integer"}
            },
            "required": ["recipe_name"]
        }
    }
    response = gemini_generate_structured(prompt, schema)
    print(json.dumps(response, indent=4))