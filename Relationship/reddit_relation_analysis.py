import praw
import pandas as pd
import numpy as np
from textblob import TextBlob
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import re
import time
from datetime import datetime, timedelta
import warnings
import os
from dotenv import load_dotenv
import random
warnings.filterwarnings('ignore')

# Load environment variables from .env file
load_dotenv()

class RedditRelationshipAnalyzer:
    def __init__(self, client_id, client_secret, user_agent, username=None, password=None):
        """Initialize Reddit API connection with rate limiting"""
        print(f"🔧 Initializing Reddit API connection...")
        
        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                username=username,
                password=password,
                ratelimit_seconds=600  # Wait 10 minutes if rate limited
            )
            print("✅ Reddit API connection initialized with rate limiting")
            
            # Test basic connection
            print("🧪 Testing basic connection...")
            try:
                # Try a very simple request first
                subreddit = self.reddit.subreddit("announcements")
                print(f"✅ Basic connection successful")
                time.sleep(2)  # Always wait between requests
                
            except Exception as e:
                print(f"⚠️  Basic connection test failed: {e}")
                
        except Exception as e:
            print(f"❌ Error initializing Reddit API: {e}")
            raise e
    
    def safe_request(self, func, *args, **kwargs):
        """Make a safe Reddit API request with retry logic"""
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Add random delay to avoid hitting rate limits
                delay = base_delay + random.uniform(1, 3)
                time.sleep(delay)
                
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                if "403" in str(e) or "429" in str(e):  # Rate limited or forbidden
                    wait_time = (2 ** attempt) * 60  # Exponential backoff in minutes
                    print(f"⏳ Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Request failed: {e}")
                    break
        
        return None
    
    def get_relationship_subreddits_safe(self):
        """Get relationship subreddits with careful rate limiting"""
        print("\n🔍 Getting relationship subreddits (with heavy rate limiting)...")
        
        # Start with smaller, more permissive subreddits
        relationship_subreddits = [
            'relationships', 'dating', 'AskReddit',  # Try these first
            'relationship_advice', 'dating_advice', 'Marriage'
        ]
        
        subreddit_data = []
        
        for sub_name in relationship_subreddits:
            print(f"  Checking r/{sub_name}...")
            
            def get_subreddit_info():
                subreddit = self.reddit.subreddit(sub_name)
                return {
                    'name': sub_name,
                    'subscribers': subreddit.subscribers,
                    'description': subreddit.public_description[:100] if subreddit.public_description else "No description"
                }
            
            result = self.safe_request(get_subreddit_info)
            
            if result:
                subreddit_data.append(result)
                print(f"  ✅ r/{sub_name}: {result['subscribers']:,} members")
            else:
                print(f"  ❌ Could not access r/{sub_name}")
            
            # Always wait between subreddit requests
            time.sleep(3)
        
        if not subreddit_data:
            print("❌ No subreddit data collected.")
            return pd.DataFrame()
        
        df = pd.DataFrame(subreddit_data)
        df = df.sort_values('subscribers', ascending=False)
        
        print(f"\n🏆 Successfully retrieved {len(df)} subreddits:")
        for idx, row in df.iterrows():
            print(f"  {idx + 1}. r/{row['name']}: {row['subscribers']:,} members")
        
        return df
    
    def get_posts_safe(self, subreddit_name, limit=20):
        """Get posts with heavy rate limiting"""
        print(f"\n📝 Getting posts from r/{subreddit_name} (limit: {limit})...")
        
        def get_posts():
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            # Try hot posts instead of top posts (sometimes less restricted)
            for post in subreddit.hot(limit=limit):
                if not post.stickied:
                    posts.append({
                        'title': post.title,
                        'score': post.score,
                        'num_comments': post.num_comments,
                        'created_utc': post.created_utc,
                        'selftext': post.selftext[:500] if hasattr(post, 'selftext') else '',  # Limit text
                        'id': post.id
                    })
                    
                    # Add delay between each post
                    time.sleep(0.5)
                    
                    if len(posts) >= 10:  # Stop early if we get enough
                        break
            
            return posts
        
        posts = self.safe_request(get_posts)
        
        if posts:
            print(f"  ✅ Retrieved {len(posts)} posts from r/{subreddit_name}")
            return pd.DataFrame(posts)
        else:
            print(f"  ❌ Could not get posts from r/{subreddit_name}")
            return pd.DataFrame()
    
    def analyze_topics_simple(self, posts_df):
        """Simple topic analysis"""
        if posts_df.empty:
            return []
        
        print(f"  🔍 Analyzing topics from {len(posts_df)} posts...")
        
        # Simple keyword counting
        all_text = posts_df['title'].str.lower()
        
        keywords = {
            'relationship': ['relationship', 'dating', 'boyfriend', 'girlfriend'],
            'breakup': ['breakup', 'broke up', 'ex'],
            'advice': ['advice', 'help', 'what should i do'],
            'marriage': ['marriage', 'married', 'husband', 'wife'],
            'family': ['family', 'parents', 'mother', 'father']
        }
        
        topic_counts = {}
        for topic, words in keywords.items():
            count = sum(all_text.str.contains(word, na=False).sum() for word in words)
            if count > 0:
                topic_counts[topic] = count
        
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        
        print(f"  📊 Found topics: {[f'{t}({c})' for t, c in sorted_topics]}")
        return sorted_topics[:3]
    
    def run_conservative_analysis(self):
        """Run analysis with very conservative rate limiting"""
        print("🐌 Starting CONSERVATIVE Reddit Analysis")
        print("(This will be slow but should avoid rate limits)")
        print("=" * 60)
        
        # Step 1: Get subreddits
        subreddits_df = self.get_relationship_subreddits_safe()
        
        if subreddits_df.empty:
            print("❌ No subreddits retrieved. Cannot continue.")
            return
        
        # Step 2: Analyze just the top 2-3 subreddits
        results = {}
        max_subreddits = min(3, len(subreddits_df))
        
        for idx, row in subreddits_df.head(max_subreddits).iterrows():
            subreddit_name = row['name']
            print(f"\n📊 Analyzing r/{subreddit_name} ({idx + 1}/{max_subreddits})")
            print("-" * 40)
            
            # Get posts
            posts_df = self.get_posts_safe(subreddit_name, limit=15)
            
            if not posts_df.empty:
                # Analyze topics
                topics = self.analyze_topics_simple(posts_df)
                
                # Simple sentiment on titles only
                sentiments = []
                for title in posts_df['title']:
                    if len(title.strip()) > 0:
                        blob = TextBlob(title)
                        sentiments.append(blob.sentiment.polarity)
                
                avg_sentiment = np.mean(sentiments) if sentiments else 0
                sentiment_label = "Positive" if avg_sentiment > 0.1 else "Negative" if avg_sentiment < -0.1 else "Neutral"
                
                results[subreddit_name] = {
                    'subscribers': row['subscribers'],
                    'posts_analyzed': len(posts_df),
                    'top_topics': topics,
                    'avg_sentiment': avg_sentiment,
                    'sentiment_label': sentiment_label
                }
                
                print(f"  ✅ Analysis complete:")
                print(f"     Posts: {len(posts_df)}")
                print(f"     Sentiment: {sentiment_label} ({avg_sentiment:.3f})")
                print(f"     Top topics: {[t for t, _ in topics]}")
            
            # Long wait between subreddits
            if idx < max_subreddits - 1:
                print("  ⏳ Waiting 30 seconds before next subreddit...")
                time.sleep(30)
        
        # Display results
        print("\n" + "="*60)
        print("📈 ANALYSIS COMPLETE!")
        print("="*60)
        
        for subreddit, data in results.items():
            print(f"\n🎯 r/{subreddit}:")
            print(f"   Subscribers: {data['subscribers']:,}")
            print(f"   Posts analyzed: {data['posts_analyzed']}")
            print(f"   Overall sentiment: {data['sentiment_label']} ({data['avg_sentiment']:.3f})")
            print(f"   Top topics: {', '.join([t.title() for t, _ in data['top_topics']])}")
        
        return results

def main():
    """Main function with conservative approach"""
    print("🐌 Reddit Relationship Analysis - CONSERVATIVE VERSION")
    print("This version uses heavy rate limiting to avoid 403 errors")
    print("=" * 60)
    
    # Load credentials
    CLIENT_ID = os.getenv('CLIENT_ID') or os.getenv('REDDIT_CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET') or os.getenv('REDDIT_CLIENT_SECRET')
    USERNAME = os.getenv('REDDIT_USERNAME')
    PASSWORD = os.getenv('REDDIT_PASSWORD')
    USER_AGENT = os.getenv('USER_AGENT') or os.getenv('REDDIT_USER_AGENT')
    
    if not all([CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD, USER_AGENT]):
        print("❌ Missing credentials in .env file!")
        return
    
    try:
        analyzer = RedditRelationshipAnalyzer(
            CLIENT_ID, CLIENT_SECRET, USER_AGENT, USERNAME, PASSWORD
        )
        
        results = analyzer.run_conservative_analysis()
        
        if results:
            print(f"\n🎉 Successfully analyzed {len(results)} subreddits!")
            print("📊 Data collected for your YouTube/TikTok content!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

if __name__ == "__main__":
    main()