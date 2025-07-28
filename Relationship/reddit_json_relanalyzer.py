import requests
import pandas as pd
import numpy as np
from textblob import TextBlob
import matplotlib.pyplot as plt
import seaborn as sns
import time
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class RedditJSONAnalyzer:
    def __init__(self):
        """Initialize Reddit JSON API analyzer (no authentication needed)"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RedditAnalyzer/1.0 (Educational Research)'
        })
        print("🔓 Using Reddit's public JSON API (no authentication required)")
    
    def get_subreddit_info(self, subreddit_name):
        """Get subreddit information using JSON API"""
        try:
            url = f"https://www.reddit.com/r/{subreddit_name}/about.json"
            print(f"  📡 Fetching info for r/{subreddit_name}...")
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    sub_data = data['data']
                    return {
                        'name': subreddit_name,
                        'subscribers': sub_data.get('subscribers', 0),
                        'description': sub_data.get('public_description', '')[:200],
                        'active_users': sub_data.get('active_user_count', 0)
                    }
            else:
                print(f"    ❌ HTTP {response.status_code} for r/{subreddit_name}")
                
        except Exception as e:
            print(f"    ❌ Error fetching r/{subreddit_name}: {e}")
        
        return None
    
    def get_posts_json(self, subreddit_name, limit=25, sort='hot'):
        """Get posts using Reddit's JSON API"""
        try:
            url = f"https://www.reddit.com/r/{subreddit_name}/{sort}.json?limit={limit}"
            print(f"  📡 Fetching {limit} {sort} posts from r/{subreddit_name}...")
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                if 'data' in data and 'children' in data['data']:
                    for post in data['data']['children']:
                        post_data = post['data']
                        posts.append({
                            'title': post_data.get('title', ''),
                            'score': post_data.get('score', 0),
                            'num_comments': post_data.get('num_comments', 0),
                            'upvote_ratio': post_data.get('upvote_ratio', 0),
                            'created_utc': post_data.get('created_utc', 0),
                            'selftext': post_data.get('selftext', '')[:500],
                            'url': post_data.get('url', ''),
                            'id': post_data.get('id', ''),
                            'subreddit': subreddit_name
                        })
                
                print(f"    ✅ Retrieved {len(posts)} posts from r/{subreddit_name}")
                return posts
            else:
                print(f"    ❌ HTTP {response.status_code} for r/{subreddit_name}")
                
        except Exception as e:
            print(f"    ❌ Error fetching posts from r/{subreddit_name}: {e}")
        
        return []
    
    def get_relationship_subreddits(self):
        """Get top relationship subreddits using JSON API"""
        print("\n🔍 Fetching relationship subreddits using JSON API...")
        
        relationship_subreddits = [
            'relationships', 'relationship_advice', 'dating_advice',
            'dating', 'Marriage', 'breakups', 'AmItheAsshole',
            'TwoXChromosomes', 'AskMen', 'AskWomen', 'datingoverthirty'
        ]
        
        subreddit_data = []
        
        for sub_name in relationship_subreddits:
            info = self.get_subreddit_info(sub_name)
            if info:
                subreddit_data.append(info)
                print(f"    ✅ r/{sub_name}: {info['subscribers']:,} members")
            
            time.sleep(1)  # Be respectful with requests
        
        if subreddit_data:
            df = pd.DataFrame(subreddit_data)
            df = df.sort_values('subscribers', ascending=False).head(7)
            
            print(f"\n🏆 Top 7 Relationship Subreddits:")
            print("=" * 50)
            for idx, row in df.iterrows():
                print(f"{idx + 1}. r/{row['name']}: {row['subscribers']:,} members")
            
            return df
        
        return pd.DataFrame()
    
    def analyze_topics(self, posts_df, top_n=3):
        """Analyze topics from posts"""
        if posts_df.empty:
            return []
        
        print(f"  🔍 Analyzing topics from {len(posts_df)} posts...")
        
        # Combine title and text
        all_text = (posts_df['title'] + ' ' + posts_df['selftext']).str.lower()
        
        relationship_keywords = {
            'breakup': ['breakup', 'broke up', 'breaking up', 'split up', 'ended'],
            'cheating': ['cheating', 'cheated', 'affair', 'unfaithful', 'infidelity'],
            'dating': ['dating', 'first date', 'tinder', 'bumble', 'online dating'],
            'marriage': ['marriage', 'married', 'wedding', 'husband', 'wife', 'spouse'],
            'communication': ['communication', 'talking', 'conversation', 'discuss'],
            'family': ['family', 'parents', 'in-laws', 'mother', 'father'],
            'trust': ['trust', 'lying', 'lies', 'honest', 'honesty'],
            'commitment': ['commitment', 'future', 'moving in', 'exclusive'],
            'long_distance': ['long distance', 'ldr', 'far away'],
            'intimacy': ['intimacy', 'physical', 'bedroom', 'affection']
        }
        
        topic_counts = {}
        for topic, keywords in relationship_keywords.items():
            count = sum(all_text.str.contains(keyword, case=False, na=False).sum() 
                       for keyword in keywords)
            if count > 0:
                topic_counts[topic] = count
        
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_topics[:top_n]
    
    def analyze_sentiment(self, posts_df, topics):
        """Analyze sentiment for each topic"""
        if posts_df.empty or not topics:
            return {}
        
        sentiment_results = {}
        
        # Define keyword mappings for topics
        topic_keywords = {
            'breakup': ['breakup', 'broke up', 'breaking up'],
            'cheating': ['cheating', 'cheated', 'affair'],
            'dating': ['dating', 'first date', 'tinder'],
            'marriage': ['marriage', 'married', 'wedding'],
            'communication': ['communication', 'talking', 'argue'],
            'family': ['family', 'parents', 'in-laws'],
            'trust': ['trust', 'lying', 'honest'],
            'commitment': ['commitment', 'future', 'exclusive'],
            'long_distance': ['long distance', 'ldr'],
            'intimacy': ['intimacy', 'physical', 'bedroom']
        }
        
        for topic, count in topics:
            if topic in topic_keywords:
                keywords = topic_keywords[topic]
                
                # Filter posts related to this topic
                topic_mask = posts_df['title'].str.lower().str.contains(
                    '|'.join(keywords), case=False, na=False
                ) | posts_df['selftext'].str.lower().str.contains(
                    '|'.join(keywords), case=False, na=False
                )
                
                topic_posts = posts_df[topic_mask]
                
                if len(topic_posts) > 0:
                    sentiments = []
                    for _, post in topic_posts.iterrows():
                        text = post['title'] + ' ' + str(post['selftext'])
                        if text.strip():
                            blob = TextBlob(text)
                            sentiments.append(blob.sentiment.polarity)
                    
                    if sentiments:
                        avg_sentiment = np.mean(sentiments)
                        sentiment_label = (
                            "Positive" if avg_sentiment > 0.1 else
                            "Negative" if avg_sentiment < -0.1 else
                            "Neutral"
                        )
                        
                        sentiment_results[topic] = {
                            'avg_sentiment': avg_sentiment,
                            'sentiment_label': sentiment_label,
                            'post_count': len(topic_posts),
                            'mention_count': count
                        }
        
        return sentiment_results
    
    def run_analysis(self, posts_per_subreddit=30):
        """Run the complete analysis using JSON API"""
        print("🚀 Starting Reddit Relationship Analysis (JSON API)")
        print("=" * 60)
        
        # Get top subreddits
        top_subreddits = self.get_relationship_subreddits()
        
        if top_subreddits.empty:
            print("❌ Could not retrieve subreddit data")
            return {}
        
        all_results = {}
        
        # Analyze each subreddit
        for idx, row in top_subreddits.iterrows():
            subreddit_name = row['name']
            print(f"\n📊 Analyzing r/{subreddit_name} ({idx + 1}/7)")
            print("-" * 40)
            
            # Get posts
            posts = self.get_posts_json(subreddit_name, limit=posts_per_subreddit)
            
            if posts:
                posts_df = pd.DataFrame(posts)
                
                # Analyze topics
                topics = self.analyze_topics(posts_df)
                print(f"    📋 Top topics: {[topic for topic, count in topics]}")
                
                # Analyze sentiment
                sentiment_results = self.analyze_sentiment(posts_df, topics)
                
                all_results[subreddit_name] = {
                    'subscriber_count': row['subscribers'],
                    'posts_analyzed': len(posts_df),
                    'top_topics': topics,
                    'sentiment_analysis': sentiment_results
                }
                
                print(f"    ✅ Completed analysis for r/{subreddit_name}")
                
                # Print sentiment summary
                for topic, sentiment in sentiment_results.items():
                    print(f"      {topic.title()}: {sentiment['sentiment_label']} "
                          f"({sentiment['avg_sentiment']:.3f}) - {sentiment['post_count']} posts")
            
            # Be respectful with timing
            time.sleep(2)
        
        # Print final summary
        self.print_summary(all_results)
        return all_results
    
    def save_results(self, results):
        """Save results to multiple file formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Save detailed JSON results
        json_filename = f"reddit_analysis_detailed_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"📄 Detailed results saved to: {json_filename}")
        
        # 2. Save summary CSV
        csv_data = []
        for subreddit, data in results.items():
            for i, (topic, count) in enumerate(data['top_topics'][:3], 1):
                sentiment_info = data['sentiment_analysis'].get(topic, {})
                csv_data.append({
                    'subreddit': subreddit,
                    'subscribers': data['subscriber_count'],
                    'topic_rank': i,
                    'topic': topic.replace('_', ' ').title(),
                    'mention_count': count,
                    'sentiment': sentiment_info.get('sentiment_label', 'N/A'),
                    'sentiment_score': round(sentiment_info.get('avg_sentiment', 0), 3),
                    'posts_with_topic': sentiment_info.get('post_count', 0)
                })
        
        csv_filename = f"reddit_analysis_summary_{timestamp}.csv"
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_filename, index=False)
        print(f"📊 CSV summary saved to: {csv_filename}")
        
        # 3. Save readable text report
        txt_filename = f"reddit_analysis_report_{timestamp}.txt"
        with open(txt_filename, 'w') as f:
            f.write("REDDIT RELATIONSHIP SUBREDDITS ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("TOP 7 RELATIONSHIP SUBREDDITS BY SUBSCRIBERS:\n")
            f.write("-" * 45 + "\n")
            
            # Sort by subscribers for ranking
            sorted_results = sorted(results.items(), 
                                  key=lambda x: x[1]['subscriber_count'], 
                                  reverse=True)
            
            for rank, (subreddit, data) in enumerate(sorted_results, 1):
                f.write(f"{rank}. r/{subreddit}\n")
                f.write(f"   Subscribers: {data['subscriber_count']:,}\n")
                f.write(f"   Posts Analyzed: {data['posts_analyzed']}\n")
                f.write(f"   Top 3 Topics:\n")
                
                for i, (topic, count) in enumerate(data['top_topics'][:3], 1):
                    sentiment_info = data['sentiment_analysis'].get(topic, {})
                    if sentiment_info:
                        f.write(f"     {i}. {topic.replace('_', ' ').title()}: {count} mentions "
                              f"({sentiment_info['sentiment_label']} sentiment, "
                              f"score: {sentiment_info['avg_sentiment']:.3f})\n")
                    else:
                        f.write(f"     {i}. {topic.replace('_', ' ').title()}: {count} mentions\n")
                f.write("\n")
            
            # Add insights section
            f.write("\nKEY INSIGHTS FOR CONTENT CREATION:\n")
            f.write("-" * 35 + "\n")
            
            # Most discussed topics overall
            all_topics = {}
            for data in results.values():
                for topic, count in data['top_topics']:
                    all_topics[topic] = all_topics.get(topic, 0) + count
            
            top_overall = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:5]
            f.write("Most Discussed Topics Across All Subreddits:\n")
            for i, (topic, count) in enumerate(top_overall, 1):
                f.write(f"  {i}. {topic.replace('_', ' ').title()}: {count} total mentions\n")
            
            # Sentiment patterns
            f.write("\nSentiment Patterns:\n")
            sentiment_counts = {'Positive': 0, 'Neutral': 0, 'Negative': 0}
            for data in results.values():
                for sentiment_info in data['sentiment_analysis'].values():
                    sentiment_counts[sentiment_info['sentiment_label']] += 1
            
            for sentiment, count in sentiment_counts.items():
                percentage = (count / sum(sentiment_counts.values()) * 100) if sum(sentiment_counts.values()) > 0 else 0
                f.write(f"  {sentiment}: {count} topics ({percentage:.1f}%)\n")
        
        print(f"📋 Text report saved to: {txt_filename}")
        return json_filename, csv_filename, txt_filename

    def print_summary(self, results):
        """Print analysis summary and save files"""
        print("\n" + "="*60)
        print("📈 ANALYSIS COMPLETE!")
        print("="*60)
        
        for subreddit, data in results.items():
            print(f"\n🎯 r/{subreddit}:")
            print(f"   Subscribers: {data['subscriber_count']:,}")
            print(f"   Posts analyzed: {data['posts_analyzed']}")
            print(f"   Top 3 topics:")
            
            for i, (topic, count) in enumerate(data['top_topics'][:3], 1):
                sentiment_info = data['sentiment_analysis'].get(topic, {})
                if sentiment_info:
                    print(f"     {i}. {topic.replace('_', ' ').title()}: {count} mentions "
                          f"({sentiment_info['sentiment_label']} sentiment)")
                else:
                    print(f"     {i}. {topic.replace('_', ' ').title()}: {count} mentions")
        
        # Save results to files
        print(f"\n💾 SAVING RESULTS...")
        json_file, csv_file, txt_file = self.save_results(results)
        
        print(f"\n📁 FILES SAVED:")
        print(f"   • Detailed JSON: {json_file}")
        print(f"   • Summary CSV: {csv_file}")
        print(f"   • Text Report: {txt_file}")
        
        print(f"\n🎬 READY FOR CONTENT CREATION!")
        print(f"Use the CSV file for charts/graphs in your video")
        print(f"Use the text report for talking points")
        print(f"Use the JSON file for deeper analysis")

def main():
    """Main execution function"""
    print("🌐 Reddit Relationship Analysis - JSON API Version")
    print("No authentication required!")
    print("=" * 50)
    
    try:
        analyzer = RedditJSONAnalyzer()
        results = analyzer.run_analysis(posts_per_subreddit=25)
        
        if results:
            print(f"\n🎉 Successfully analyzed {len(results)} subreddits!")
            print("📊 Perfect data for your YouTube/TikTok content!")
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()