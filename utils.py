import json
import os
from datetime import datetime
import copy
import praw
from typing import Generator
from submodules.google_api.creds_and_service import (
    get_credentials,
    get_sheets_service,
    get_drive_service
    )
from submodules.google_api.google_sheets_api import (
    create_sheet, 
    create_table_from_schema, 
    add_rows_to_sheet,
    add_sheet_to_spreadsheet
    )

def to_dict(objects, clean=True):
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
        objects_dict = [copy.deepcopy(obj).__dict__ for obj in objects]
    else:
        objects_dict = [copy.deepcopy(objects).__dict__]
    
    if clean:
        return clean_dict(objects_dict)
    else:
        return objects_dict

def clean_dict(data):
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
        'downs',
        'query',
        'perspective_id',
        'custom_llm_id'
    ]

    clean_data = []
    for d in data:
        d = {k: v for k, v in d.items() if k in retain_keys}
        for key in ['query', 'perspective_id', 'custom_llm_id']:
            if key not in d.keys():
                d[key] = ""
        clean_data.append(d)

    return clean_data

def save_json(data_dict, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data_dict, f, indent=4)

def get_targeting_data():
    with open('targeting.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_gsheets_api():
    targeting_data = get_targeting_data()
    google_credentials = get_credentials(client_secrets_path='client_secrets.json')
    google_sheets_service = get_sheets_service(google_credentials)
    if targeting_data['spreadsheet_id'] is None:
        # Create spreadsheet
        spreadsheet_id = create_sheet(google_sheets_service, targeting_data['spreadsheet_name'])
        targeting_data['spreadsheet_id'] = spreadsheet_id
    else:
        spreadsheet_id = targeting_data['spreadsheet_id']
    sheet_names = [key.replace('_sheet_name', '') for key in targeting_data.keys() if '_sheet_name' in key]
    for sheet_name in sheet_names:
        if f'{sheet_name.lower()}_sheet_id' not in targeting_data.keys() or targeting_data[f'{sheet_name.lower()}_sheet_id'] is None:
            targeting_data[f'{sheet_name.lower()}_sheet_name'] = sheet_name
            sheet_id = add_sheet_to_spreadsheet(google_sheets_service, spreadsheet_id, sheet_title=targeting_data[f'{sheet_name.lower()}_sheet_name'])
            targeting_data[f'{sheet_name.lower()}_sheet_id'] = sheet_id
            create_table_from_schema(google_sheets_service, spreadsheet_id, sheet_id=sheet_id, table_name=targeting_data[f'{sheet_name.lower()}_sheet_name'], schema_path=f'data/schemas/{sheet_name.lower()}_schema.json')
            with open('targeting.json', 'w', encoding='utf-8') as f:
                json.dump(targeting_data, f, indent=4)
    
    output_data = {
        'spreadsheet_id': targeting_data['spreadsheet_id'],
        'google_sheets_service': google_sheets_service,
    }
    
    for sheet_name in sheet_names:
        output_data[f'{sheet_name.lower()}_sheet_id'] = targeting_data[f'{sheet_name.lower()}_sheet_id']

    return output_data

def reset_spreadsheet_config():
    """
    Reset spreadsheet configuration by setting spreadsheet_id to null and removing all sheet_id key-value pairs.
    This function will be called when the newSheet argument is provided to create a fresh spreadsheet.
    """
    try:
        with open('targeting.json', 'r', encoding='utf-8') as f:
            targeting_data = json.load(f)
        
        # Set spreadsheet_id to null
        targeting_data['spreadsheet_id'] = None
        
        # Remove all key-value pairs where the key ends with 'sheet_id'
        keys_to_remove = [key for key in targeting_data.keys() if key.endswith('_sheet_id')]
        for key in keys_to_remove:
            del targeting_data[key]
        
        # Save the updated configuration back to targeting.json
        with open('targeting.json', 'w', encoding='utf-8') as f:
            json.dump(targeting_data, f, indent=4)
        
        print("✓ Spreadsheet configuration reset successfully")
        print(f"  - Removed {len(keys_to_remove)} sheet_id entries")
        print("  - Set spreadsheet_id to null")

        get_gsheets_api()

        print("✓ New spreadsheet created successfully")
        
    except Exception as e:
        print(f"❌ Error resetting spreadsheet configuration: {e}")
        raise 