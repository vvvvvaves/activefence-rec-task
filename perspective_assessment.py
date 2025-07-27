from llm.perspective_api import get_client, get_perspective_api_score, clean_response_flat
import json
from utils import get_gsheets_api
from submodules.google_api.google_sheets_api import get_rows_from_range, add_rows_to_sheet
import uuid
import time
from tqdm import tqdm
import pandas as pd
import argparse
from googleapiclient.errors import HttpError

CONTEXT_SIZE = 4000
BATCH_SIZE = 100
START_ROW = 0
MODE = 'csv'

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--comments_path', type=str, default='comments_with_context.csv')
    parser.add_argument('-p', '--posts_path', type=str, default='submissions.csv')
    parser.add_argument('-b', '--batch_size', type=int, default=BATCH_SIZE)
    parser.add_argument('-s', '--start_row', type=int, default=START_ROW)
    parser.add_argument('-cs', '--context_size', type=int, default=CONTEXT_SIZE)
    parser.add_argument('-m', '--mode', type=str, choices=['sheet', 'csv'], default=MODE)
    return parser.parse_args()

def comments_worker_from_sheet(batch_size=BATCH_SIZE, start_row=START_ROW, context_size=CONTEXT_SIZE):
    gsheets_api = get_gsheets_api()
    spreadsheet_id = gsheets_api['spreadsheet_id']
    posts_sheet_id = gsheets_api['posts_sheet_id']
    comments_sheet_id = gsheets_api['comments_sheet_id']
    perspective_sheet_id = gsheets_api['perspective_sheet_id']
    google_sheets_service = gsheets_api['google_sheets_service']
    perspective_client = get_client()
    batch_index = 0
    comment_columns = get_rows_from_range(google_sheets_service, spreadsheet_id, comments_sheet_id, 1, 1)[0]
    perspective_columns = get_rows_from_range(google_sheets_service, spreadsheet_id, perspective_sheet_id, 1, 1)[0]
    assessment_bar = tqdm(total=None, dynamic_ncols=True, bar_format='Comments assessed: {n}')
    uploaded_bar = tqdm(total=None, dynamic_ncols=True, bar_format='Comments uploaded: {n}')
    assessment_bar.update(start_row)
    uploaded_bar.update(start_row)
    assessment_bar.refresh()
    uploaded_bar.refresh()
    while True:
        comments_rows = get_rows_from_range(
            google_sheets_service, spreadsheet_id, comments_sheet_id,
            batch_index * batch_size + start_row + 2,
            (batch_index + 1) * batch_size + start_row + 1,
        )
        if len(comments_rows) < 1:
            break
        perspective_rows = []
        for comment_row in comments_rows:
            comment_dict = dict(zip(comment_columns, comment_row))
            body = comment_dict['Body'][-context_size:]
            response = get_perspective_api_score(perspective_client, body)
            assessment_bar.update(1)
            assessment_bar.refresh()
            clean_response = clean_response_flat(response)
            if clean_response is None:
                continue
            clean_response['perspective_id'] = str(uuid.uuid4())
            clean_response['sheet_name'] = 'Comments'
            clean_response['subreddit'] = comment_dict['Subreddit']
            clean_response['id'] = comment_dict['Id']
            perspective_rows.append(clean_response)

            time.sleep(1.1)
        add_rows_to_sheet(
            google_sheets_service, spreadsheet_id, perspective_sheet_id,
            perspective_rows,
            [column.lower() for column in perspective_columns]
        )
        uploaded_bar.update(len(perspective_rows))
        uploaded_bar.refresh()
        batch_index += 1
    assessment_bar.close()
    uploaded_bar.close()

def worker_from_csv(path, batch_size=BATCH_SIZE, start_row=START_ROW, context_size=CONTEXT_SIZE, comments=True):
    gsheets_api = get_gsheets_api()
    spreadsheet_id = gsheets_api['spreadsheet_id']
    perspective_sheet_id = gsheets_api['perspective_sheet_id']
    google_sheets_service = gsheets_api['google_sheets_service']
    perspective_client = get_client()
    batch_index = 0
    perspective_columns = get_rows_from_range(google_sheets_service, spreadsheet_id, perspective_sheet_id, 1, 1)[0]
    assessment_bar = tqdm(total=None, dynamic_ncols=True, bar_format='Comments assessed: {n}' if comments else 'Posts assessed: {n}')
    uploaded_bar = tqdm(total=None, dynamic_ncols=True, bar_format='Comments uploaded: {n}' if comments else 'Posts uploaded: {n}')
    assessment_bar.update(start_row)
    uploaded_bar.update(start_row)
    assessment_bar.refresh()
    uploaded_bar.refresh()
    comments_df = pd.read_csv(path)
    while True:
        batch_df = comments_df.iloc[batch_index * batch_size + start_row: (batch_index + 1) * batch_size + start_row]
        if len(batch_df) < 1:
            break
        perspective_rows = []
        for index, row in batch_df.iterrows():
            if comments:
                if 'full_text_with_context' not in row and 'body' not in row:
                    continue
                elif 'full_text_with_context' not in row:
                    body = row['body']
                else:
                    body = row['full_text_with_context']
            else:
                body = str(row['title']) + '\n\n' + str(row['selftext'])
            if body is None:
                continue
            body = body[:context_size]
            try:
                response = get_perspective_api_score(perspective_client, body)
            except HttpError as e:
                if e.status_code == 429:
                    time.sleep(10)
                    response = get_perspective_api_score(perspective_client, body)
                else:
                    raise e
            assessment_bar.update(1)
            assessment_bar.refresh()
            clean_response = clean_response_flat(response)
            if clean_response is None:
                continue
            clean_response['perspective_id'] = str(uuid.uuid4())
            clean_response['sheet_name'] = 'comments' if comments else 'posts'
            clean_response['subreddit'] = row['subreddit']
            clean_response['id'] = row['id']
            perspective_rows.append(clean_response)

            time.sleep(1.1)
        add_rows_to_sheet(
            google_sheets_service, spreadsheet_id, perspective_sheet_id,
            perspective_rows,
            [column.lower() for column in perspective_columns]
        )
        uploaded_bar.update(len(perspective_rows))
        uploaded_bar.refresh()
        batch_index += 1
    assessment_bar.close()
    uploaded_bar.close()

if __name__ == '__main__':
    args = get_args()
    if args.mode == 'sheet':
        comments_worker_from_sheet(
            batch_size=args.batch_size, 
            start_row=args.start_row, 
            context_size=args.context_size
        )
    elif args.mode == 'csv':
        worker_from_csv(
            path=args.comments_path, 
            batch_size=args.batch_size, 
            start_row=args.start_row, 
            context_size=args.context_size, 
            comments=True
        )