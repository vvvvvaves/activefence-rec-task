from llm.perspective_api import get_client, get_perspective_api_score, clean_response_flat
import json

if __name__ == '__main__':
    perspective_client = get_client()
    text = 'Jews have too much control over the U.S. Government'
    response = get_perspective_api_score(perspective_client, text)
    print(json.dumps(clean_response_flat(response), indent=4))
