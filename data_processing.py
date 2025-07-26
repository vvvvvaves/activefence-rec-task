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

def read_spans(path, attribute, _df, _perspective_df):
    if os.path.exists(path):
        return pd.read_csv(path)
    df = _df.copy()
    perspective_df = _perspective_df.copy()
    attribute = attribute.lower()
    df.sort_values(by='id', key=perspective_df['id'].reindex, na_position='last', inplace=True)
    perspective_df.sort_values(by='id', inplace=True)
    sheet_name = perspective_df['sheet_name'].iloc[0]
    content_column_name = 'body' if sheet_name.lower() == 'comments' else 'selftext'
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
    perspective_df.to_csv(path, index=False)
    return perspective_df

if __name__ == '__main__':
    gsheets_api = get_gsheets_api()
    spreadsheet_id = gsheets_api['spreadsheet_id']
    perspective_sheet_id = gsheets_api['perspective_sheet_id']
    comments_sheet_id = gsheets_api['comments_sheet_id']
    google_sheets_service = gsheets_api['google_sheets_service']
    comments_df = to_csv(path='comments.csv', service=google_sheets_service, spreadsheet_id=spreadsheet_id, sheet_id=comments_sheet_id)
    perspectives_df = to_csv(path='perspectives.csv', service=google_sheets_service, spreadsheet_id=spreadsheet_id, sheet_id=perspective_sheet_id)
    attribute = 'identity_attack'
    df = comments_df
    perspective_df = perspectives_df
    perspective_df = read_spans('perspectives_identity_attack.csv', attribute, df, perspective_df)
    print(perspective_df[['identity_attack_score', 'identity_attack_span']])