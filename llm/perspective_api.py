import time
from googleapiclient import discovery
import json
import os
from dotenv import load_dotenv
from collections import OrderedDict
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
    analyze_request = {
        'comment': { 'text': text },
        'spanAnnotations': True,
        'requestedAttributes': {
            'TOXICITY': {
              'scoreType': 'PROBABILITY',
            }, 
            'SEVERE_TOXICITY': {
              'scoreType': 'PROBABILITY',
            }, 
            'IDENTITY_ATTACK': {
              'scoreType': 'PROBABILITY',
            }, 
            'INSULT': {
              'scoreType': 'PROBABILITY',
            }, 
            'PROFANITY': {
              'scoreType': 'PROBABILITY',
            }, 
            'THREAT': {
              'scoreType': 'PROBABILITY',
            },
            'TOXICITY_EXPERIMENTAL': {
              'scoreType': 'PROBABILITY',
            },
            'SEXUALLY_EXPLICIT': {
              'scoreType': 'PROBABILITY',
            },
            'FLIRTATION': {
              'scoreType': 'PROBABILITY',
            },
            'SEXUALLY_EXPLICIT_EXPERIMENTAL': {
              'scoreType': 'PROBABILITY',
            },
            'IDENTITY_ATTACK_EXPERIMENTAL': {
              'scoreType': 'PROBABILITY',
            },
            'INSULT_EXPERIMENTAL': {
              'scoreType': 'PROBABILITY',
            },
            'PROFANITY_EXPERIMENTAL': {
              'scoreType': 'PROBABILITY',
            },
            'THREAT_EXPERIMENTAL': {
              'scoreType': 'PROBABILITY',
            },
            'ATTACK_ON_AUTHOR': {
              'scoreType': 'PROBABILITY',
            },
            'ATTACK_ON_COMMENTER': {
              'scoreType': 'PROBABILITY',
            },
            'INFLAMMATORY': {
              'scoreType': 'PROBABILITY',
            },
            }
    }
    response = client.comments().analyze(body=analyze_request).execute()
    return response

def clean_response(text, response):
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


client = get_client()
text = 'Jews have too much control over the U.S. Government'
response = get_perspective_api_score(client, text)
print(json.dumps(clean_response(text, response), indent=4))