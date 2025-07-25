import time
from googleapiclient import discovery
import json
import os
from dotenv import load_dotenv
from collections import OrderedDict
from utils import get_targeting_data
from googleapiclient.errors import HttpError
load_dotenv()

PERSPECTIVE_API_KEY = os.getenv('PERSPECTIVE_API_KEY')

def get_client():
    client = discovery.build(
        "commentanalyzer",
        "v1alpha1",
        developerKey=PERSPECTIVE_API_KEY,
        discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
        static_discovery=False,
    )
    return client

def get_perspective_api_score(client, text):
    requestedAttributes = get_targeting_data()['requestedAttributes']
    analyze_request = {
        'comment': { 'text': text },
        'spanAnnotations': True,
        'requestedAttributes': requestedAttributes
    }
    try:
        response = client.comments().analyze(body=analyze_request).execute()
    except HttpError as e:
        if e.resp.status == 429:
            raise e
        elif e.resp.status == 400:
            return None # Bad request, most likely due to unknown language
        else:
            raise e
    return response

def clean_response(text, response):
    if response is None:
        return None
    sorted_scores = OrderedDict()
    for attribute, score in response['attributeScores'].items():
        sorted_scores[attribute] = OrderedDict()
        sorted_scores[attribute]['summary_score'] = score['summaryScore']['value']
        sorted_scores[attribute]['spans'] = []
        for _span in score['spanScores']:
          span = OrderedDict()
          span['text'] = text[_span['begin']: _span['end']]
          span['score'] = _span['score']['value']
          sorted_scores[attribute]['spans'].append(span)
    sorted_scores = OrderedDict(sorted(sorted_scores.items(), key=lambda item: item[1]['summary_score'], reverse=True))
    first_key = next(iter(sorted_scores))
    first_value = sorted_scores[first_key]
    return {
      'max_score': first_value['summary_score'],
      'max_score_attribute': first_key,
      'scores': sorted_scores,
      'languages': response['languages'],
      'detected_languages': response['detectedLanguages'],
    }

def clean_response_flat(response):
  if response is None:
    return None
  output = {}
  output['languages'] = ', '.join(response['languages'])
  output['detected_languages'] = ', '.join(response['detectedLanguages'])
  for attribute, data in response['attributeScores'].items():
    # Sort spanScores by score value descending
    spanScores = sorted(data['spanScores'], key=lambda item: item['score']['value'], reverse=True)
    output.update({
      f'{attribute}_score': data['summaryScore']['value'],
      f'{attribute}_max_span_begin': spanScores[0]['begin'],
      f'{attribute}_max_span_end': spanScores[0]['end'],
    })
  return output

if __name__ == '__main__':
    client = get_client()
    text = 'Jews have too much control over the U.S. Government'
    response = get_perspective_api_score(client, text)
    print(json.dumps(clean_response_flat(response), indent=4))