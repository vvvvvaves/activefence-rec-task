import json
import os
from datetime import datetime
import copy
import praw
from typing import Generator

def to_dict(objects):
    """
    Convert a list of objects to a list of dicts using the .d_ attribute.
    
    Input:
        objects (list of praw.models.Submission or praw.models.Comment or praw.models.Redditor): List of post objects or a single post object.
    Output:
        list of dict: List of dictionaries representing the post data (using .d_ attribute).
    """
    if isinstance(objects, Generator):
        objects = list(objects)

    if isinstance(objects, list):
        return [copy.deepcopy(obj).__dict__ for obj in objects]
    else:
        return [copy.deepcopy(objects).__dict__]

def save_json(data, filename, clean=True):
    """
    Save data to a JSON file.

    Input:
        data (list of dict): List of dictionaries to save.
        filename (str): Path to the JSON file to write.
    Output:
        None. Writes data to the specified JSON file.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    non_serializable = ['_replies', '_submission', '_reddit', '_comments', 'selftext_html']

    for i, d in enumerate(data):
        for key in non_serializable:
            if key in d.keys():
                data[i].pop(key)

        if 'subreddit' in d.keys():
            d['subreddit'] = d['subreddit'].display_name

        if 'author' in d.keys():
            d['author'] = d['author'].name if isinstance(d['author'], praw.models.Redditor) else d['author']

        if 'created_utc' in d.keys():
            d['created_utc'] = datetime.fromtimestamp(d['created_utc']).strftime('%Y-%m-%d %H:%M:%S')

        if '_comments_by_id' in d.keys():
            _comments_by_id = d.pop('_comments_by_id')
            data[i]['_comments_by_id'] = list(_comments_by_id.keys())

    if clean:
        retain_keys = [
            'subreddit', 
            'selftext', 
            'title', 
            'query',
            "_comments_by_id",
            "author",
            "created",
            "id",
            "score",
            'upvote_ratio',
            "url",
            'author_is_blocked',
            'over_18',
            'parent_id',
            'body',
            'controversiality',
            'ups',
            'downs'
        ]

        requested_attributes = get_targeting_data()['requestedAttributes']
        clean_data = []
        for d in data:
            clean_data.append({k: v for k, v in d.items() if k in retain_keys or k in requested_attributes.keys()})

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, indent=4)
    else:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

def get_targeting_data():
    with open('targeting.json', 'r', encoding='utf-8') as f:
        return json.load(f)
