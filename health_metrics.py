from collections import defaultdict, Counter
from datetime import datetime, timedelta
from api import get_subreddit_posts, get_posts_comments
from utils import save_json, to_dict
from collections import defaultdict, Counter
from datetime import datetime, timedelta

def get_community_health_metrics(posts_data, comments_data, days_back=30):
    """
    Collect community health metrics for a subreddit using pre-fetched data.
    
    Input:
        posts_data (list of dict): List of post dictionaries. Each dict should contain at least 'created_utc', 'author', and optionally fields like 'score', 'upvote_ratio', 'distinguished', 'crosspost_parent', 'crosspost_info', 'num_comments', etc.
        comments_data (list of dict): List of comment dictionaries. Each dict should contain at least 'created_utc', 'author', and optionally fields like 'score', 'distinguished', 'post_id', etc.
        days_back (int, optional): Number of days back to analyze. Default is 30.
    Output:
        dict: Dictionary containing various community health metrics, such as total_posts, total_comments, total_users, comment_post_ratio, crosspost_count, avg_post_score, avg_comment_score, avg_upvote_ratio, post_score_distribution, avg_response_time_minutes, user_activity_distribution, mod_activity, post_engagement_rate, avg_comments_per_post, etc.
    """

    # Calculate derived properties for posts
    for post in posts_data:
        # is_crosspost
        if 'is_crosspost' not in post:
            post['is_crosspost'] = 'crosspost_parent' in post or 'crosspost_info' in post
        # is_mod_post
        if 'is_mod_post' not in post:
            post['is_mod_post'] = post.get('distinguished') == 'moderator'
        # crosspost_info
        if post['is_crosspost'] and 'crosspost_info' not in post:
            if 'crosspost_parent' in post:
                try:
                    post['crosspost_info'] = {
                        'from_sub': post['crosspost_parent'].split('/')[4],
                        'to_sub': post.get('subreddit', None),
                        'created_utc': post['created_utc']
                    }
                except Exception:
                    post['crosspost_info'] = {}
            else:
                post['crosspost_info'] = {}

    # Calculate derived properties for comments
    for comment in comments_data:
        if 'is_mod_comment' not in comment:
            comment['is_mod_comment'] = comment.get('distinguished') == 'moderator'

    users = set()
    active_users = defaultdict(int)
    cross_posts = []
    vote_patterns = []
    response_times = []

    cutoff_date = datetime.utcnow() - timedelta(days=days_back)

    # Filter posts and comments by cutoff_date
    posts_data = [p for p in posts_data if datetime.utcfromtimestamp(p['created_utc']) >= cutoff_date]
    comments_data = [c for c in comments_data if datetime.utcfromtimestamp(c['created_utc']) >= cutoff_date]

    for post in posts_data:
        users.add(str(post.get('author')))
        active_users[str(post.get('author'))] += 1
        if post.get('is_crosspost'):
            cross_posts.append(post.get('crosspost_info', {}))
        vote_patterns.append({
            'score': post.get('score', 0),
            'upvote_ratio': post.get('upvote_ratio'),
            'type': 'post'
        })

    for comment in comments_data:
        users.add(str(comment.get('author')))
        active_users[str(comment.get('author'))] += 1
        vote_patterns.append({
            'score': comment.get('score', 0),
            'upvote_ratio': None,
            'type': 'comment'
        })

    # Calculate response times (time between post and first comment)
    post_comments = defaultdict(list)
    for comment in comments_data:
        post_comments[comment.get('post_id')].append(comment.get('created_utc'))
    for post in posts_data:
        c_times = post_comments.get(post.get('id'), [])
        if c_times:
            first_comment_time = min(c_times)
            response_time = first_comment_time - post.get('created_utc')
            response_times.append(response_time / 60)  # minutes

    # Calculate metrics
    metrics = {}
    metrics['total_posts'] = len(posts_data)
    metrics['total_comments'] = len(comments_data)
    metrics['total_users'] = len(users)
    metrics['days_analyzed'] = days_back
    metrics['comment_post_ratio'] = len(comments_data) / max(len(posts_data), 1)
    metrics['crosspost_count'] = len(cross_posts)
    metrics['crosspost_ratio'] = len(cross_posts) / max(len(posts_data), 1)
    if cross_posts:
        cross_post_sources = Counter([cp.get('from_sub') for cp in cross_posts if cp.get('from_sub')])
        metrics['top_crosspost_sources'] = dict(cross_post_sources.most_common(5))
    if vote_patterns:
        post_scores = [v['score'] for v in vote_patterns if v['type'] == 'post']
        comment_scores = [v['score'] for v in vote_patterns if v['type'] == 'comment']
        upvote_ratios = [v['upvote_ratio'] for v in vote_patterns if v['upvote_ratio'] is not None]
        metrics['avg_post_score'] = sum(post_scores) / max(len(post_scores), 1)
        metrics['avg_comment_score'] = sum(comment_scores) / max(len(comment_scores), 1)
        metrics['avg_upvote_ratio'] = sum(upvote_ratios) / max(len(upvote_ratios), 1) if upvote_ratios else 0
        metrics['post_score_distribution'] = {
            'negative': len([s for s in post_scores if s < 0]),
            'zero': len([s for s in post_scores if s == 0]),
            'low_positive': len([s for s in post_scores if 0 < s <= 10]),
            'high_positive': len([s for s in post_scores if s > 10])
        }
    if response_times:
        metrics['avg_response_time_minutes'] = sum(response_times) / len(response_times)
        metrics['median_response_time_minutes'] = sorted(response_times)[len(response_times)//2]
        metrics['quick_responses_under_hour'] = len([rt for rt in response_times if rt < 60])
    user_activity = list(active_users.values())
    metrics['avg_user_activity'] = sum(user_activity) / max(len(user_activity), 1)
    metrics['highly_active_users'] = len([u for u in user_activity if u >= 5])
    metrics['single_activity_users'] = len([u for u in user_activity if u == 1])
    metrics['user_activity_distribution'] = {
        'single_post': len([u for u in user_activity if u == 1]),
        'low_activity': len([u for u in user_activity if 2 <= u <= 4]),
        'moderate_activity': len([u for u in user_activity if 5 <= u <= 10]),
        'high_activity': len([u for u in user_activity if u > 10])
    }
    if posts_data:
        daily_posts = defaultdict(int)
        for post in posts_data:
            day = datetime.utcfromtimestamp(post.get('created_utc')).date()
            daily_posts[day] += 1
        daily_counts = list(daily_posts.values())
        if len(daily_counts) > 1:
            recent_avg = sum(daily_counts[-7:]) / min(7, len(daily_counts))
            overall_avg = sum(daily_counts) / len(daily_counts)
            metrics['recent_vs_overall_activity'] = recent_avg / max(overall_avg, 1)
            metrics['daily_post_variance'] = sum((x - overall_avg)**2 for x in daily_counts) / len(daily_counts)
    mod_posts = len([p for p in posts_data if p.get('is_mod_post')])
    mod_comments = len([c for c in comments_data if c.get('is_mod_comment')])
    metrics['mod_activity'] = {
        'mod_posts': mod_posts,
        'mod_comments': mod_comments,
        'mod_post_ratio': mod_posts / max(len(posts_data), 1),
        'mod_comment_ratio': mod_comments / max(len(comments_data), 1)
    }
    if posts_data:
        engaged_posts = len([p for p in posts_data if p.get('num_comments', 0) > 0])
        metrics['post_engagement_rate'] = engaged_posts / len(posts_data)
        avg_comments_per_post = sum(p.get('num_comments', 0) for p in posts_data) / len(posts_data)
        metrics['avg_comments_per_post'] = avg_comments_per_post
    return metrics

def print_health_summary(metrics, subreddit_name):
    """
    Print a formatted summary of community health metrics to the console.
    
    Input:
        metrics (dict): Dictionary of community health metrics as returned by get_community_health_metrics().
        subreddit_name (str): Name of the subreddit (e.g., 'python').
    Output:
        None. Prints formatted summary to stdout.
    """
    print("\n" + "="*60)
    print(f"COMMUNITY HEALTH METRICS SUMMARY FOR r/{subreddit_name}")
    print("="*60)
    print(f"\n📊 BASIC STATS:")
    print(f"   Total Posts: {metrics.get('total_posts', 0)}")
    print(f"   Total Comments: {metrics.get('total_comments', 0)}")
    print(f"   Total Users: {metrics.get('total_users', 0)}")
    print(f"   Comment/Post Ratio: {metrics.get('comment_post_ratio', 0):.2f}")
    print(f"\n🗳️  ENGAGEMENT QUALITY:")
    print(f"   Average Post Score: {metrics.get('avg_post_score', 0):.2f}")
    print(f"   Average Upvote Ratio: {metrics.get('avg_upvote_ratio', 0):.2f}")
    print(f"   Post Engagement Rate: {metrics.get('post_engagement_rate', 0):.2f}")
    print(f"   Avg Comments per Post: {metrics.get('avg_comments_per_post', 0):.2f}")
    print(f"\n👥 USER ACTIVITY:")
    print(f"   Highly Active Users (5+ actions): {metrics.get('highly_active_users', 0)}")
    print(f"   Single Activity Users: {metrics.get('single_activity_users', 0)}")
    print(f"   Average User Activity: {metrics.get('avg_user_activity', 0):.2f}")
    print(f"\n⚡ RESPONSE PATTERNS:")
    if 'avg_response_time_minutes' in metrics:
        print(f"   Average Response Time: {metrics['avg_response_time_minutes']:.1f} minutes")
        print(f"   Quick Responses (<1 hour): {metrics.get('quick_responses_under_hour', 0)}")
    print(f"\n🔄 CROSS-POSTING:")
    print(f"   Cross-posts: {metrics.get('crosspost_count', 0)}")
    print(f"   Cross-post Ratio: {metrics.get('crosspost_ratio', 0):.3f}")
    print(f"\n🛡️  MODERATION:")
    mod_stats = metrics.get('mod_activity', {})
    print(f"   Mod Posts: {mod_stats.get('mod_posts', 0)}")
    print(f"   Mod Comments: {mod_stats.get('mod_comments', 0)}")

def save_health_summary_markdown(metrics, subreddit_name, filename):
    """
    Save a formatted summary of community health metrics to a markdown file.
    
    Input:
        metrics (dict): Dictionary of community health metrics as returned by get_community_health_metrics().
        subreddit_name (str): Name of the subreddit (e.g., 'python').
        filename (str): Path to the markdown file to write.
    Output:
        None. Writes formatted summary to the specified markdown file.
    """
    lines = []
    lines.append(f"# COMMUNITY HEALTH METRICS SUMMARY FOR r/{subreddit_name}\n")
    lines.append("## 📊 BASIC STATS:")
    lines.append(f"- **Total Posts:** {metrics.get('total_posts', 0)}")
    lines.append(f"- **Total Comments:** {metrics.get('total_comments', 0)}")
    lines.append(f"- **Total Users:** {metrics.get('total_users', 0)}")
    lines.append(f"- **Comment/Post Ratio:** {metrics.get('comment_post_ratio', 0):.2f}\n")
    lines.append("## 🗳️  ENGAGEMENT QUALITY:")
    lines.append(f"- **Average Post Score:** {metrics.get('avg_post_score', 0):.2f}")
    lines.append(f"- **Average Upvote Ratio:** {metrics.get('avg_upvote_ratio', 0):.2f}")
    lines.append(f"- **Post Engagement Rate:** {metrics.get('post_engagement_rate', 0):.2f}")
    lines.append(f"- **Avg Comments per Post:** {metrics.get('avg_comments_per_post', 0):.2f}\n")
    lines.append("## 👥 USER ACTIVITY:")
    lines.append(f"- **Highly Active Users (5+ actions):** {metrics.get('highly_active_users', 0)}")
    lines.append(f"- **Single Activity Users:** {metrics.get('single_activity_users', 0)}")
    lines.append(f"- **Average User Activity:** {metrics.get('avg_user_activity', 0):.2f}\n")
    lines.append("## ⚡ RESPONSE PATTERNS:")
    if 'avg_response_time_minutes' in metrics:
        lines.append(f"- **Average Response Time:** {metrics['avg_response_time_minutes']:.1f} minutes")
        lines.append(f"- **Quick Responses (<1 hour):** {metrics.get('quick_responses_under_hour', 0)}\n")
    else:
        lines.append("No response times available")
    lines.append("## 🔄 CROSS-POSTING:")
    lines.append(f"- **Cross-posts:** {metrics.get('crosspost_count', 0)}")
    lines.append(f"- **Cross-post Ratio:** {metrics.get('crosspost_ratio', 0):.3f}\n")
    lines.append("## 🛡️  MODERATION:")
    mod_stats = metrics.get('mod_activity', {})
    lines.append(f"- **Mod Posts:** {mod_stats.get('mod_posts', 0)}")
    lines.append(f"- **Mod Comments:** {mod_stats.get('mod_comments', 0)}")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def assess_community_health(reddit, subreddit_name, num_posts=100, days_back=30):
    """
    High-level function to assess and summarize community health for a subreddit.
    
    Input:
        reddit (praw.Reddit): Authenticated Reddit client instance.
        subreddit_name (str): Name of the subreddit (e.g., 'python').
    Output:
        None. Prints summary to stdout and saves markdown summary to file.
    """
    posts = get_subreddit_posts(subreddit_name, num_posts=num_posts, days_back=days_back, sort_by='new')
    comments = get_posts_comments(posts)
    posts_dict = to_dict(posts)
    comments_dict = to_dict(comments)
    metrics = get_community_health_metrics(posts_dict, comments_dict)
    print_health_summary(metrics, subreddit_name)
    save_json(posts_dict, f"data/subreddits/{subreddit_name}/posts_raw.json")
    save_json(comments_dict, f"data/subreddits/{subreddit_name}/comments_raw.json")
    save_health_summary_markdown(metrics, subreddit_name, f"data/subreddits/{subreddit_name}/health_metrics.md")


