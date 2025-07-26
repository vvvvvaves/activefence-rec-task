from llm.perspective_api import get_client, get_perspective_api_score, clean_response_flat
import json
from utils import get_gsheets_api
from submodules.google_api.google_sheets_api import get_rows_from_range, add_rows_to_sheet
import uuid
import time
from tqdm import tqdm

def comments_worker(batch_size=100, start_row=0):
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
            body = comment_dict['Body']
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


if __name__ == '__main__':
    comments_worker(batch_size=100, start_row=3878)