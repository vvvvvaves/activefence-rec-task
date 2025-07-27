from utils import get_gsheets_api
from submodules.google_api.google_sheets_api import get_all_rows_from_sheet
import pandas as pd
import os
import time

def to_csv(path, service=None, spreadsheet_id=None, sheet_id=None):
    if os.path.exists(path):
        df = pd.read_csv(path)
    else:
        if service is None or spreadsheet_id is None or sheet_id is None:
            raise ValueError('service, spreadsheet_id, and sheet_id must be provided')
        rows = get_all_rows_from_sheet(service, spreadsheet_id, sheet_id)
        columns = [col.lower() for col in rows[0]]
        rows = rows[1:]
        df = pd.DataFrame(rows, columns=columns)
        df.to_csv(path, index=False)
    return df

def find_highest_scores(path, df, perspective_df):
    if os.path.exists(path):
        return pd.read_csv(path)
    perspective_df = perspective_df.iloc[:100]
    score_columns = [col for col in perspective_df.columns if '_score' in col]
    perspective_df['max_attribute'] = perspective_df[score_columns].idxmax(axis=1).apply(lambda x: x[:-6])
    perspective_df['max_score'] = perspective_df[score_columns].max(axis=1)
    perspective_df['max_span_begin'] = perspective_df.apply(lambda row: f'{row['max_attribute']}_max_span_begin', axis=1)
    perspective_df['max_span_end'] = perspective_df.apply(lambda row: f'{row['max_attribute']}_max_span_end', axis=1)
    df.sort_values(by='id', key=perspective_df['id'].reindex, na_position='last', inplace=True)
    sheet_name = perspective_df['sheet_name'].iloc[0]
    content_column_name = 'body' if sheet_name.lower() == 'comments' else 'selftext'
    df['max_span_begin'] = perspective_df['max_span_begin']
    df['max_span_end'] = perspective_df['max_span_end']
    perspective_df['max_span'] = df.apply(
        lambda row: f'{row[content_column_name]}[{row["max_span_begin"]}:{row["max_span_end"]}]' 
        if row[content_column_name] != '[deleted]' else "[not available]", axis=1
        )
    if "full_text" not in perspective_df.columns:
        perspective_df["full_text"] = df[content_column_name]
    df.drop(columns=['max_span_begin', 'max_span_end'], inplace=True)
    perspective_df.sort_values(by='max_score', ascending=False, inplace=True)
    perspective_df.to_csv(path, index=False)
    return perspective_df

def read_spans(attribute, _df, _perspective_df, path=None):
    if path is not None and os.path.exists(path):
        return pd.read_csv(path)
    df = _df.copy()
    perspective_df = _perspective_df.copy()
    attribute = attribute.lower()
    df.sort_values(by='id', key=perspective_df['id'].reindex, na_position='last', inplace=True)
    perspective_df.sort_values(by='id', inplace=True)
    sheet_name = perspective_df['sheet_name'].iloc[0]
    content_column_name = ('body' if 'full_text_with_context' not in df.columns else 'full_text_with_context') if sheet_name.lower() == 'comments' else 'selftext'
    begin_col = f'{attribute}_max_span_begin'
    end_col = f'{attribute}_max_span_end'
    df[begin_col] = perspective_df[begin_col]
    df[end_col] = perspective_df[end_col]
    
    perspective_df[f'{attribute}_span'] = df.loc[df[begin_col].notnull()].apply(
        lambda row: f'{row[content_column_name][int(row[begin_col]):int(row[end_col])]}' 
        if row[content_column_name] != '[deleted]' else "[not available]", axis=1
        )
    if "full_text" not in perspective_df.columns:
        perspective_df["full_text"] = df[content_column_name]
    df.drop(columns=[begin_col, end_col], inplace=True)
    perspective_df.sort_values(by=f'{attribute}_score', ascending=False, inplace=True)
    if path is not None:
        perspective_df.to_csv(path, index=False)
    return perspective_df

def get_full_comment_context(comments_path, posts_path):
    if os.path.exists(comments_path):
        comments_df = pd.read_csv(comments_path)
    else:
        raise ValueError('File does not exist: ' + comments_path)
    if os.path.exists(posts_path):
        posts_df = pd.read_csv(posts_path)
    else:
        raise ValueError('File does not exist: ' + posts_path)

    def get_context(comment_id):
        row = comments_df[comments_df['id'] == comment_id]
        row_author = list(row['author'])[0] if len(row['author']) > 0 else "[unknown]"
        row_body = list(row['body'])[0] if len(row['body']) > 0 else "[not available]"
        body_formatted = f"[User {row_author}]:\n{row_body}"
        parent_id = list(row['parent_id'])[0] if len(row['parent_id']) > 0 else None
        prefix = parent_id.split('_')[0] if parent_id is not None else None
        parent_id = parent_id.split('_')[1] if parent_id is not None else None
        if parent_id is None:
            return body_formatted
        elif prefix == 't3':
            post_row = posts_df[posts_df['id'] == parent_id]
            post_author = list(post_row['author'])[0] if len(post_row['author']) > 0 else "[unknown]"
            post_title = list(post_row['title'])[0] if len(post_row['title']) > 0 else "[not available]"
            post_body = list(post_row['selftext'])[0] if len(post_row['selftext']) > 0 else "[not available]"
            post_formatted = f"[Post {post_title}, by User {post_author}]:\n{post_body}"
            return post_formatted + "\n\n" + body_formatted
        elif prefix == 't1':
            parent_row = comments_df[comments_df['id'] == parent_id]
            parent_formatted = get_context(parent_id)
            return parent_formatted + "\n\n" + body_formatted
    
    comments_df['full_text_with_context'] = comments_df.apply(
        lambda row: get_context(row['id']), axis=1
    )
    comments_df.to_csv(f'{comments_path[:-4]}_with_context.csv', index=False)
    return comments_df

if __name__ == '__main__':
    gsheets_api = get_gsheets_api()
    spreadsheet_id = gsheets_api['spreadsheet_id']
    perspective_sheet_id = gsheets_api['perspective_sheet_id']
    comments_sheet_id = gsheets_api['comments_sheet_id']
    google_sheets_service = gsheets_api['google_sheets_service']
    perspective_df = to_csv(path='perspective_full_context.csv', service=google_sheets_service, spreadsheet_id=spreadsheet_id, sheet_id=perspective_sheet_id)
    comments_df = to_csv(path='comments_with_context.csv', service=google_sheets_service, spreadsheet_id=spreadsheet_id, sheet_id=comments_sheet_id).dropna(subset=['id'])
    perspective_df = perspective_df[perspective_df['sheet_name'] == 'comments']
    for attribute in ['toxicity', 'severe_toxicity', 'threat', 'insult', 'profanity', 'identity_attack', 'inflammatory', 'attack_on_author', 'attack_on_commenter']:
        perspective_df = read_spans(attribute, comments_df, perspective_df, path=None)
    perspective_df.to_csv('perspective_full_context_spans.csv', index=False)