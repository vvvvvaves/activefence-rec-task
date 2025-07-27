#!/usr/bin/env python3
"""
Data Processing Module for AFRT Pipeline

This module implements Stage 2 of the AFRT pipeline: data processing and conversation
composition. It handles the conversion of raw Reddit data into structured conversation
threads suitable for analysis by the Perspective API and Gemini LLM.

Key functions:
- to_csv(): Convert Google Sheets data to CSV format
- compose_conversations(): Create conversation threads from posts and comments
- sort_conversations_by_score(): Sort conversations by toxicity scores
- find_highest_scores(): Process Perspective API results

Author: AFRT Team
Date: 2025
"""

from utils import get_gsheets_api
from submodules.google_api.google_sheets_api import get_all_rows_from_sheet
import pandas as pd
import os
import time

def to_csv(path, service=None, spreadsheet_id=None, sheet_id=None):
    """
    Convert Google Sheets data to CSV format.
    
    If the CSV file already exists, it loads from disk. Otherwise, it fetches
    data from Google Sheets and saves it as a CSV file.
    
    Args:
        path (str): Path to the CSV file to create or load
        service: Google Sheets API service object
        spreadsheet_id (str): Google Sheets spreadsheet ID
        sheet_id (str): Google Sheets sheet ID
    
    Returns:
        pd.DataFrame: DataFrame containing the sheet data
    
    Input:
        - Google Sheets API service and IDs (if file doesn't exist)
        - Existing CSV file (if file exists)
    
    Output:
        - CSV file saved to disk
        - DataFrame with sheet data
    """
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
    """
    Process Perspective API results to find the highest toxicity scores for each item.
    
    This function analyzes Perspective API results to identify the maximum toxicity
    score and corresponding attribute for each post, comment, or conversation.
    
    Args:
        path (str): Path to save the processed results CSV
        df (pd.DataFrame): Original data DataFrame (posts, comments, or conversations)
        perspective_df (pd.DataFrame): Perspective API results DataFrame
    
    Returns:
        pd.DataFrame: Processed DataFrame with maximum scores and attributes
    
    Input:
        - Original data DataFrame
        - Perspective API results DataFrame
    
    Output:
        - CSV file with maximum scores and attributes
        - Processed DataFrame with enhanced scoring information
    """
    if os.path.exists(path):
        return pd.read_csv(path)
    
    perspective_df = perspective_df.copy()
    df = df.copy()
    
    # Find score columns and calculate maximum scores
    score_columns = [col for col in perspective_df.columns if '_score' in col]
    perspective_df['max_attribute'] = perspective_df[score_columns].idxmax(axis=1).apply(lambda x: x[:-6])
    perspective_df['max_score'] = perspective_df[score_columns].max(axis=1)
    
    # Get span information for the maximum scoring attribute
    perspective_df['max_span_begin'] = perspective_df.apply(lambda row: row[f'{row['max_attribute']}_max_span_begin'], axis=1)
    perspective_df['max_span_end'] = perspective_df.apply(lambda row: row[f'{row['max_attribute']}_max_span_end'], axis=1)
    
    # Sort original data to match perspective results
    df.sort_values(by='post_id', key=perspective_df['post_id'].reindex, na_position='last', inplace=True)
    
    # Determine content column based on data type
    sheet_name = perspective_df['sheet_name'].iloc[0]
    content_column_name = None
    if sheet_name.lower() == 'comments':
        content_column_name = 'body' if 'full_text_with_context' not in df.columns else 'full_text_with_context'
    elif sheet_name.lower() == 'posts':
        content_column_name = 'selftext'
    elif sheet_name.lower() == 'conversations':
        content_column_name = 'full_conversation'

    # Add span information to original data
    df['max_span_begin'] = perspective_df['max_span_begin']
    df['max_span_end'] = perspective_df['max_span_end']
    
    # Add full text if not present
    if "full_text" not in perspective_df.columns:
        perspective_df["full_text"] = df[content_column_name]
    
    # Clean up temporary columns and sort by maximum score
    df.drop(columns=['max_span_begin', 'max_span_end'], inplace=True)
    perspective_df.sort_values(by='max_score', ascending=False, inplace=True)
    perspective_df.to_csv(path, index=False)
    
    return perspective_df

def sort_conversations_by_score(conversations_path, perspectives_max_path, output_path=None, required_attributes=None):
    """
    Sort conversations based on their highest max score from perspectives max CSV file.
    
    Args:
        conversations_path (str): Path to the conversations CSV file
        perspectives_max_path (str): Path to the perspectives max CSV file
        output_path (str, optional): Path to save the sorted conversations. If None, returns DataFrame without saving
        required_attributes (list, optional): List of specific attributes to filter by. If provided, only conversations
                                            with max_attribute in this list will be retained
    
    Returns:
        pd.DataFrame: Sorted conversations DataFrame
    """
    # Load the data
    if not os.path.exists(conversations_path):
        raise ValueError(f'Conversations file does not exist: {conversations_path}')
    if not os.path.exists(perspectives_max_path):
        raise ValueError(f'Perspectives max file does not exist: {perspectives_max_path}')
    
    conversations_df = pd.read_csv(conversations_path)
    perspectives_max_df = pd.read_csv(perspectives_max_path)
    
    # Ensure required columns exist in perspectives max DataFrame
    required_cols = ['post_id', 'max_score', 'max_attribute']
    missing_cols = [col for col in required_cols if col not in perspectives_max_df.columns]
    if missing_cols:
        raise ValueError(f'Missing columns in perspectives max file: {missing_cols}')
    
    # Filter by required attributes if specified
    if required_attributes is not None:
        if not isinstance(required_attributes, list):
            raise ValueError('required_attributes must be a list')
        
        # Convert to lowercase for case-insensitive matching
        required_attributes_lower = [attr.lower() for attr in required_attributes]
        
        # Filter perspectives max DataFrame to only include specified attributes
        perspectives_max_df = perspectives_max_df[
            perspectives_max_df['max_attribute'].str.lower().isin(required_attributes_lower)
        ]
        
        if perspectives_max_df.empty:
            print(f"Warning: No conversations found with the specified attributes: {required_attributes}")
            return pd.DataFrame()
    
    # Merge conversations with perspectives max data
    # Use inner join to only keep conversations that have perspective scores
    merged_df = conversations_df.merge(
        perspectives_max_df[['post_id', 'max_score', 'max_attribute']], 
        on='post_id', 
        how='inner'
    )
    
    # Sort by max_score in descending order (highest scores first)
    merged_df = merged_df.sort_values(by='max_score', ascending=False)
    
    # Reset index to reflect the new order
    merged_df = merged_df.reset_index(drop=True)
    
    # Save to file if output_path is provided
    if output_path is not None:
        merged_df.to_csv(output_path, index=False)
        print(f"Sorted conversations saved to: {output_path}")
        print(f"Total conversations: {len(merged_df)}")
        if required_attributes:
            print(f"Filtered by attributes: {required_attributes}")
        print(f"Score range: {merged_df['max_score'].min():.3f} - {merged_df['max_score'].max():.3f}")
    
    return merged_df

def compose_conversations(output_path, posts_path, comments_path):
    """
    Compose conversations dataset from posts and comments.
    Creates a dataset with post_id and full_conversation columns.
    """
    if os.path.exists(output_path):
        return pd.read_csv(output_path)
    
    # Load data
    if not os.path.exists(posts_path):
        raise ValueError(f'Posts file does not exist: {posts_path}')
    if not os.path.exists(comments_path):
        raise ValueError(f'Comments file does not exist: {comments_path}')
    
    posts_df = pd.read_csv(posts_path)
    comments_df = pd.read_csv(comments_path)
    
    # Clean and prepare data
    posts_df = posts_df.copy()
    comments_df = comments_df.copy()
    
    # Ensure required columns exist
    required_post_cols = ['id', 'title', 'selftext', 'author']
    required_comment_cols = ['id', 'body', 'parent_id', 'author']
    
    missing_post_cols = [col for col in required_post_cols if col not in posts_df.columns]
    missing_comment_cols = [col for col in required_comment_cols if col not in comments_df.columns]
    
    if missing_post_cols:
        raise ValueError(f'Missing columns in posts: {missing_post_cols}')
    if missing_comment_cols:
        raise ValueError(f'Missing columns in comments: {missing_comment_cols}')
    
    # Fill NaN values
    posts_df = posts_df.fillna({
        'title': '[No Title]',
        'selftext': '[No Content]',
        'author': '[Unknown Author]'
    })
    comments_df = comments_df.fillna({
        'body': '[No Content]',
        'author': '[Unknown Author]'
    })
    
    def build_conversation_tree(post_id):
        """Build conversation tree for a specific post"""
        # Get post info
        post_row = posts_df[posts_df['id'] == post_id]
        if post_row.empty:
            return None
        
        post_info = post_row.iloc[0]
        post_author = post_info['author']
        post_title = post_info['title']
        post_content = post_info['selftext']
        
        # Start conversation with post
        conversation = f"Post ID: {post_id}\n"
        conversation += f"Post Title: {post_title}\n"
        conversation += f"Post Content: {post_content}\n"
        conversation += f"Post Author: {post_author}\n"
        conversation += "-" * 50 + "\n"
        
        # Get top-level comments (comments that reply to the post)
        top_level_comments = comments_df[
            comments_df['parent_id'].str.startswith('t3_', na=False) & 
            (comments_df['parent_id'].str[3:] == str(post_id))
        ]
        
        if top_level_comments.empty:
            conversation += "No comments\n"
            return conversation
        
        # Build comment tree recursively
        def build_comment_tree(comment_id, indent_level=0, parent_comment_id=None):
            """Recursively build comment tree with proper indentation"""
            comment_row = comments_df[comments_df['id'] == comment_id]
            if comment_row.empty:
                return ""
            
            comment_info = comment_row.iloc[0]
            comment_author = comment_info['author']
            comment_body = comment_info['body']
            
            indent = "  " * indent_level
            comment_text = f"{indent}Comment ID: {comment_id}\n"
            
            # Add parent comment information if this is a reply
            if parent_comment_id is not None:
                comment_text += f"{indent}This comment is a reply to parent comment: {parent_comment_id}\n"
            
            comment_text += f"{indent}Comment Author: {comment_author}\n"
            comment_text += f"{indent}Comment Body: {comment_body}\n"
            comment_text += f"{indent}{'-' * 30}\n"
            
            # Find replies to this comment
            replies = comments_df[
                comments_df['parent_id'].str.startswith('t1_', na=False) & 
                (comments_df['parent_id'].str[3:] == str(comment_id))
            ]
            
            # Recursively add replies
            for _, reply in replies.iterrows():
                comment_text += build_comment_tree(reply['id'], indent_level + 1, comment_id)
            
            return comment_text
        
        # Add all top-level comments
        for _, comment in top_level_comments.iterrows():
            conversation += build_comment_tree(comment['id'], parent_comment_id=None)
        
        return conversation
    
    # Create conversations for each post
    conversations = []
    
    for _, post in posts_df.iterrows():
        post_id = post['id']
        full_conversation = build_conversation_tree(post_id)
        
        if full_conversation is not None:
            conversations.append({
                'post_id': post_id,
                'full_conversation': full_conversation
            })
    
    # Create DataFrame and save
    conversations_df = pd.DataFrame(conversations)
    conversations_df.to_csv(output_path, index=False)
    
    return conversations_df

if __name__ == '__main__':
    # Example usage of the new sort_conversations_by_score function
    # Sort all conversations by max score
    sorted_conversations = sort_conversations_by_score(
        conversations_path='data/conversations.csv',
        perspectives_max_path='data/perspectives_max.csv',
        output_path='data/conversations_sorted_by_score.csv'
    )
    
    # Example: Sort conversations filtered by specific attributes
    sorted_conversations_filtered = sort_conversations_by_score(
        conversations_path='data/conversations.csv',
        perspectives_max_path='data/perspectives_max.csv',
        output_path='data/conversations_filtered_by_attributes.csv',
        required_attributes=['toxicity', 'severe_toxicity', 'identity_attack']
    )
