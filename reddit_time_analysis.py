import requests
import pandas as pd
import datetime
import time
import json
import os

# Configuration - Change this to analyze different subreddits
SUBREDDIT_TO_ANALYZE = "sysadmin"  # Change this to analyze different subreddits

def collect_reddit_data_json(subreddit_name, num_posts=500):
    """
    Collect Reddit data using JSON API (bypasses PRAW issues)
    """
    print(f"🚀 Collecting data from r/{subreddit_name} using Reddit JSON API...")
    
    # Working User-Agent from our test
    headers = {
        'User-Agent': 'python:RedditAnalyzer:v1.0.0 (by /u/External_Necessary48)'
    }
    
    posts_data = []
    
    # Different data sources to get a good mix of posts
    endpoints = [
        {
            'name': 'hot',
            'url': f'https://www.reddit.com/r/{subreddit_name}/hot.json?limit={num_posts//4}',
            'description': 'Currently popular posts'
        },
        {
            'name': 'new',
            'url': f'https://www.reddit.com/r/{subreddit_name}/new.json?limit={num_posts//4}',
            'description': 'Recent posts'
        },
        {
            'name': 'top_week',
            'url': f'https://www.reddit.com/r/{subreddit_name}/top.json?t=week&limit={num_posts//4}',
            'description': 'Top posts this week'
        },
        {
            'name': 'top_month',
            'url': f'https://www.reddit.com/r/{subreddit_name}/top.json?t=month&limit={num_posts//4}',
            'description': 'Top posts this month'
        }
    ]
    
    for endpoint in endpoints:
        print(f"  📥 Collecting {endpoint['name']} posts ({endpoint['description']})...")
        
        try:
            response = requests.get(endpoint['url'], headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                posts = data['data']['children']
                
                print(f"    ✅ Retrieved {len(posts)} posts")
                
                for post in posts:
                    try:
                        post_data = post['data']
                        
                        # Convert timestamp to datetime
                        post_time = datetime.datetime.fromtimestamp(post_data['created_utc'])
                        
                        # Extract relevant data
                        post_info = {
                            'id': post_data['id'],
                            'title': post_data['title'],
                            'score': post_data['score'],
                            'upvote_ratio': post_data.get('upvote_ratio', 0),
                            'num_comments': post_data['num_comments'],
                            'created_utc': post_data['created_utc'],
                            'created_datetime': post_time,
                            'hour': post_time.hour,
                            'day_of_week': post_time.weekday(),  # 0=Monday, 6=Sunday
                            'day_name': post_time.strftime('%A'),
                            'is_weekend': post_time.weekday() >= 5,
                            'author': post_data.get('author', '[deleted]'),
                            'is_self_post': post_data.get('is_self', False),
                            'url': post_data.get('url', ''),
                            'subreddit': post_data['subreddit'],
                            'post_type': endpoint['name'],
                            'flair': post_data.get('link_flair_text', ''),
                            'is_stickied': post_data.get('stickied', False)
                        }
                        
                        posts_data.append(post_info)
                        
                    except Exception as e:
                        print(f"    ⚠️  Error processing post: {e}")
                        continue
                
            elif response.status_code == 403:
                print(f"    ❌ 403 Forbidden - may be a private subreddit")
            elif response.status_code == 404:
                print(f"    ❌ 404 Not Found - subreddit doesn't exist")
            elif response.status_code == 429:
                print(f"    ⏰ Rate limited - waiting 10 seconds...")
                time.sleep(10)
            else:
                print(f"    ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Request failed: {e}")
        
        # Be respectful to Reddit's servers
        time.sleep(2)
    
    # Convert to DataFrame and remove duplicates
    df = pd.DataFrame(posts_data)
    
    if not df.empty:
        original_count = len(df)
        df = df.drop_duplicates(subset=['id'])
        final_count = len(df)
        
        print(f"\n📊 Data Collection Summary:")
        print(f"   - Posts collected: {original_count}")
        print(f"   - Unique posts: {final_count}")
        print(f"   - Duplicates removed: {original_count - final_count}")
        print(f"   - Date range: {df['created_datetime'].min().date()} to {df['created_datetime'].max().date()}")
    else:
        print(f"\n❌ No data collected from r/{subreddit_name}")
    
    return df

def calculate_engagement_metrics(df):
    """
    Calculate various engagement metrics
    """
    if df.empty:
        return df
    
    # Engagement score (weighted combination of score and comments)
    df['engagement_score'] = (df['score'] * 0.7) + (df['num_comments'] * 0.3)
    
    # Comments per upvote ratio
    df['comments_per_score'] = df['num_comments'] / (df['score'] + 1)  # +1 to avoid division by zero
    
    # Age of post in days
    now = datetime.datetime.now()
    df['days_old'] = (now - pd.to_datetime(df['created_datetime'])).dt.days
    
    # Normalized engagement (accounting for post age)
    df['normalized_engagement'] = df['engagement_score'] / (df['days_old'] + 1)
    
    return df

def analyze_posting_times(df, subreddit_name):
    """
    Analyze the best times to post based on engagement metrics
    """
    if df.empty:
        print("❌ No data to analyze")
        return None, None
    
    print("\n" + "="*70)
    print(f"📊 TIME SERIES ANALYSIS FOR r/{subreddit_name}")
    print("="*70)
    
    # Remove stickied posts (they don't represent natural engagement)
    df_clean = df[df['is_stickied'] == False].copy()
    
    if len(df_clean) < len(df):
        print(f"📌 Filtered out {len(df) - len(df_clean)} stickied posts for more accurate analysis")
    
    # Analysis by hour of day
    hourly_stats = df_clean.groupby('hour').agg({
        'score': ['mean', 'median', 'count'],
        'num_comments': ['mean', 'median'],
        'engagement_score': ['mean', 'median'],
        'upvote_ratio': 'mean',
        'normalized_engagement': 'mean'
    }).round(2)
    
    hourly_stats.columns = ['avg_score', 'median_score', 'post_count', 
                           'avg_comments', 'median_comments', 
                           'avg_engagement', 'median_engagement', 'avg_upvote_ratio',
                           'avg_normalized_engagement']
    
    print("\n🕐 BEST HOURS TO POST (by average engagement):")
    best_hours = hourly_stats.nlargest(5, 'avg_engagement')
    for idx, row in best_hours.iterrows():
        time_str = f"{idx:02d}:00"
        print(f"   {time_str} - Engagement: {row['avg_engagement']:.1f}, "
              f"Avg Score: {row['avg_score']:.1f}, "
              f"Avg Comments: {row['avg_comments']:.1f}, "
              f"Posts: {row['post_count']}")
    
    # Analysis by day of week
    daily_stats = df_clean.groupby(['day_of_week', 'day_name']).agg({
        'score': ['mean', 'median', 'count'],
        'num_comments': ['mean', 'median'],
        'engagement_score': ['mean', 'median'],
        'normalized_engagement': 'mean'
    }).round(2)
    
    daily_stats.columns = ['avg_score', 'median_score', 'post_count',
                          'avg_comments', 'median_comments', 
                          'avg_engagement', 'median_engagement',
                          'avg_normalized_engagement']
    
    print("\n📅 BEST DAYS TO POST:")
    best_days = daily_stats.nlargest(3, 'avg_engagement')
    for (day_num, day_name), row in best_days.iterrows():
        print(f"   {day_name} - Engagement: {row['avg_engagement']:.1f}, "
              f"Avg Score: {row['avg_score']:.1f}, "
              f"Posts: {row['post_count']}")
    
    # Weekend vs Weekday analysis
    weekend_stats = df_clean.groupby('is_weekend').agg({
        'score': 'mean',
        'num_comments': 'mean',
        'engagement_score': 'mean',
        'normalized_engagement': 'mean'
    }).round(2)
    
    print("\n🗓️  WEEKEND vs WEEKDAY PERFORMANCE:")
    for is_weekend, row in weekend_stats.iterrows():
        day_type = "Weekend" if is_weekend else "Weekday"
        post_count = len(df_clean[df_clean['is_weekend'] == is_weekend])
        print(f"   {day_type} - Engagement: {row['engagement_score']:.1f}, "
              f"Avg Score: {row['score']:.1f}, "
              f"Posts: {post_count}")
    
    # Content type analysis
    if 'is_self_post' in df_clean.columns:
        print("\n📝 CONTENT TYPE ANALYSIS:")
        content_stats = df_clean.groupby('is_self_post').agg({
            'score': 'mean',
            'num_comments': 'mean',
            'engagement_score': 'mean'
        }).round(2)
        
        for is_self, row in content_stats.iterrows():
            content_type = "Text Posts" if is_self else "Link Posts"
            post_count = len(df_clean[df_clean['is_self_post'] == is_self])
            print(f"   {content_type} - Engagement: {row['engagement_score']:.1f}, "
                  f"Avg Score: {row['score']:.1f}, "
                  f"Posts: {post_count}")
    
    return hourly_stats, daily_stats

def generate_actionable_recommendations(df, hourly_stats, daily_stats, subreddit_name):
    """
    Generate specific, actionable recommendations
    """
    if df.empty or hourly_stats is None:
        return
    
    print("\n" + "="*70)
    print("🎯 ACTIONABLE RECOMMENDATIONS FOR OPTIMAL POSTING")
    print("="*70)
    
    # Best posting times
    best_hours = hourly_stats.nlargest(3, 'avg_engagement').index.tolist()
    best_time_range = f"{min(best_hours):02d}:00 - {max(best_hours):02d}:00"
    
    print(f"⏰ OPTIMAL POSTING TIMES:")
    print(f"   🥇 Best hours: {', '.join([f'{h:02d}:00' for h in best_hours])}")
    print(f"   📈 Peak engagement window: {best_time_range}")
    
    # Best days
    if daily_stats is not None:
        best_days = daily_stats.nlargest(2, 'avg_engagement').index.get_level_values(1).tolist()
        print(f"\n📅 OPTIMAL POSTING DAYS:")
        print(f"   🥇 Best days: {', '.join(best_days)}")
    
    # Weekend vs weekday recommendation
    df_clean = df[df['is_stickied'] == False]
    weekend_avg = df_clean[df_clean['is_weekend'] == True]['engagement_score'].mean()
    weekday_avg = df_clean[df_clean['is_weekend'] == False]['engagement_score'].mean()
    
    print(f"\n🗓️  WEEKEND vs WEEKDAY STRATEGY:")
    if weekday_avg > weekend_avg * 1.1:  # 10% threshold
        print(f"   ✅ Focus on weekdays (avg: {weekday_avg:.1f} vs weekend: {weekend_avg:.1f})")
    elif weekend_avg > weekday_avg * 1.1:
        print(f"   ✅ Weekend posting is effective (avg: {weekend_avg:.1f} vs weekday: {weekday_avg:.1f})")
    else:
        print(f"   ➡️  Similar performance on weekdays and weekends")
    
    # Content type recommendation
    if 'is_self_post' in df_clean.columns:
        self_post_avg = df_clean[df_clean['is_self_post'] == True]['engagement_score'].mean()
        link_post_avg = df_clean[df_clean['is_self_post'] == False]['engagement_score'].mean()
        
        print(f"\n📝 CONTENT TYPE STRATEGY:")
        if self_post_avg > link_post_avg * 1.1:
            print(f"   ✅ Text posts perform better (avg: {self_post_avg:.1f} vs links: {link_post_avg:.1f})")
        elif link_post_avg > self_post_avg * 1.1:
            print(f"   ✅ Link posts perform better (avg: {link_post_avg:.1f} vs text: {self_post_avg:.1f})")
        else:
            print(f"   ➡️  Both text and link posts perform similarly")
    
    # Timing strategy
    print(f"\n⚡ POSTING STRATEGY FOR r/{subreddit_name}:")
    print(f"   1. 🎯 Post during: {best_time_range}")
    print(f"   2. 📅 Focus on: {', '.join(best_days) if daily_stats is not None else 'weekdays'}")
    print(f"   3. 🔄 Monitor for 1-2 weeks to optimize timing")
    print(f"   4. 📊 Track engagement patterns after posting")

def save_results(df, hourly_stats, daily_stats, subreddit_name):
    """
    Save results to CSV files
    """
    if df.empty:
        print("❌ No data to save")
        return
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save raw data
    raw_filename = f'{subreddit_name}_analysis_{timestamp}.csv'
    df.to_csv(raw_filename, index=False)
    
    # Save hourly analysis
    if hourly_stats is not None:
        hourly_filename = f'{subreddit_name}_hourly_{timestamp}.csv'
        hourly_stats.to_csv(hourly_filename)
    
    # Save daily analysis
    if daily_stats is not None:
        daily_filename = f'{subreddit_name}_daily_{timestamp}.csv'
        daily_stats.to_csv(daily_filename)
    
    print(f"\n💾 RESULTS SAVED:")
    print(f"   📁 Raw data: {raw_filename}")
    if hourly_stats is not None:
        print(f"   📁 Hourly analysis: {hourly_filename}")
    if daily_stats is not None:
        print(f"   📁 Daily analysis: {daily_filename}")

def main():
    """
    Main function to run the complete analysis
    """
    print(f"🚀 Reddit Time Series Analysis for r/{SUBREDDIT_TO_ANALYZE}")
    print(f"📡 Using Reddit JSON API (no authentication required)")
    print("="*70)
    
    # Collect data
    df = collect_reddit_data_json(SUBREDDIT_TO_ANALYZE, num_posts=600)
    
    if df.empty:
        print(f"❌ No data collected from r/{SUBREDDIT_TO_ANALYZE}")
        print("Possible reasons:")
        print("   - Subreddit is private or doesn't exist")
        print("   - Network connectivity issues")
        print("   - Reddit API temporarily unavailable")
        return
    
    # Calculate engagement metrics
    df = calculate_engagement_metrics(df)
    
    # Perform analysis
    hourly_stats, daily_stats = analyze_posting_times(df, SUBREDDIT_TO_ANALYZE)
    
    # Generate recommendations
    generate_actionable_recommendations(df, hourly_stats, daily_stats, SUBREDDIT_TO_ANALYZE)
    
    # Save results
    save_results(df, hourly_stats, daily_stats, SUBREDDIT_TO_ANALYZE)
    
    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE!")
    print(f"📊 Analyzed {len(df)} posts from r/{SUBREDDIT_TO_ANALYZE}")
    print(f"📈 Data covers {df['created_datetime'].min().date()} to {df['created_datetime'].max().date()}")
    print(f"⭐ Average engagement score: {df['engagement_score'].mean():.1f}")
    
    print(f"\n🔄 NEXT STEPS:")
    print(f"   1. Review the recommendations above")
    print(f"   2. Test posting at suggested times")
    print(f"   3. Run this analysis weekly to track trends")
    print(f"   4. Experiment with different content types")

if __name__ == "__main__":
    main()