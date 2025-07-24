import json
import os

def posts_to_dict(posts):
    """
    Convert a list of post objects to a list of dicts using the .d_ attribute.
    
    Input:
        posts (list of praw.models.Submission or praw.models.Submission): List of post objects or a single post object.
    Output:
        list of dict: List of dictionaries representing the post data (using .d_ attribute).
    """
    if isinstance(posts, list):
        return [post.__dict__ for post in posts]
    else:
        return [posts.__dict__]

def comments_to_dict(comments):
    """
    Convert a list of comment objects to a list of dicts using the .d_ attribute.
    
    Input:
        comments (list of praw.models.Comment or praw.models.Comment): List of comment objects or a single comment object.
    Output:
        list of dict: List of dictionaries representing the comment data (using .d_ attribute).
    """
    if isinstance(comments, list):
        return [comment.__dict__ for comment in comments]
    else:
        return [comments.__dict__]

def save_json(data, filename):
    """
    Save data to a JSON file.

    Deletes non-serializable keys and stores dictionary of {"comment_id": Comment} as list of comment_ids.
    
    Input:
        data (list of dict): List of dictionaries to save.
        filename (str): Path to the JSON file to write.
    Output:
        None. Writes data to the specified JSON file.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    non_serializable = ['_replies', 'author', '_submission', '_reddit', 'subreddit', '_comments', 'body_html', 'body']
    for i, d in enumerate(data):
        for key in non_serializable:
            if key in d.keys():
                data[i].pop(key)

        if '_comments_by_id' in d.keys():
            _comments_by_id = d.pop('_comments_by_id')
            data[i]['_comments_by_id'] = list(_comments_by_id.keys())
       
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_targeting_data():
    with open('targeting.json', 'r', encoding='utf-8') as f:
        return json.load(f)
