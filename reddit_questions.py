import requests
import pandas as pd
import re
import datetime
import time
from collections import Counter

# Configuration
SUBREDDIT_TO_ANALYZE = "sysadmin"
NUM_POSTS_TO_ANALYZE = 100  # Analyze more posts for better category distribution

def collect_posts_for_classification(subreddit_name, num_posts=100):
    """
    Collect recent posts with their content for classification
    """
    print(f"🔍 Collecting posts from r/{subreddit_name} for classification...")
    
    headers = {
        'User-Agent': 'python:RedditPostClassifier:v1.0.0 (by /u/External_Necessary48)'
    }
    
    all_posts = []
    
    # Get posts from different sources for variety
    endpoints = [
        {
            'name': 'hot',
            'url': f'https://www.reddit.com/r/{subreddit_name}/hot.json?limit={num_posts//3}',
            'description': 'Currently popular posts'
        },
        {
            'name': 'new',
            'url': f'https://www.reddit.com/r/{subreddit_name}/new.json?limit={num_posts//3}',
            'description': 'Recent posts'
        },
        {
            'name': 'top_week',
            'url': f'https://www.reddit.com/r/{subreddit_name}/top.json?t=week&limit={num_posts//3}',
            'description': 'Top posts this week'
        }
    ]
    
    for endpoint in endpoints:
        print(f"  📥 Getting {endpoint['name']} posts...")
        
        try:
            response = requests.get(endpoint['url'], headers=headers)
            
            if response.status_code == 200:
                posts_data = response.json()['data']['children']
                print(f"    ✅ Retrieved {len(posts_data)} posts")
                
                for post in posts_data:
                    post_data = post['data']
                    post_time = datetime.datetime.fromtimestamp(post_data['created_utc'])
                    
                    # Combine title and self-text for classification
                    full_text = post_data['title']
                    if post_data.get('selftext'):
                        full_text += " " + post_data['selftext']
                    
                    all_posts.append({
                        'id': post_data['id'],
                        'title': post_data['title'],
                        'selftext': post_data.get('selftext', ''),
                        'full_text': full_text,
                        'score': post_data['score'],
                        'upvote_ratio': post_data.get('upvote_ratio', 0),
                        'num_comments': post_data['num_comments'],
                        'created_time': post_time,
                        'days_ago': (datetime.datetime.now() - post_time).days,
                        'author': post_data.get('author', '[deleted]'),
                        'is_self_post': post_data.get('is_self', False),
                        'url': post_data.get('url', ''),
                        'permalink': f"https://reddit.com{post_data['permalink']}",
                        'flair': post_data.get('link_flair_text', ''),
                        'post_type': endpoint['name']
                    })
                
            else:
                print(f"    ❌ Failed with status {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
        
        time.sleep(1)  # Rate limiting
    
    # Remove duplicates and convert to DataFrame
    df = pd.DataFrame(all_posts)
    if not df.empty:
        df = df.drop_duplicates(subset=['id'])
        print(f"✅ Collected {len(df)} unique posts for classification")
    
    return df

def classify_posts(posts_df):
    """
    Classify posts into predefined categories using keyword matching
    """
    print("🏷️  Classifying posts into categories...")
    
    if posts_df.empty:
        return posts_df
    
    # Enhanced category definitions with more keywords
    categories = {
        'backup_recovery': {
            'keywords': ['backup', 'restore', 'recovery', 'disaster recovery', 'failover', 'redundancy', 
                        'snapshot', 'replication', 'backup solution', 'data protection', 'business continuity'],
            'description': 'Backup and disaster recovery solutions'
        },
        'security': {
            'keywords': ['security', 'vulnerability', 'breach', 'password', 'authentication', 'encryption', 
                        'firewall', 'antivirus', 'malware', 'phishing', 'ssl', 'certificate', 'audit', 
                        'compliance', 'threat', 'intrusion'],
            'description': 'Security and compliance topics'
        },
        'monitoring_alerting': {
            'keywords': ['monitoring', 'alert', 'dashboard', 'metrics', 'logging', 'performance', 
                        'nagios', 'zabbix', 'prtg', 'scom', 'grafana', 'prometheus', 'uptime'],
            'description': 'System monitoring and alerting'
        },
        'automation_scripting': {
            'keywords': ['automation', 'script', 'powershell', 'bash', 'python', 'ansible', 'puppet', 
                        'chef', 'terraform', 'devops', 'ci/cd', 'jenkins', 'automated'],
            'description': 'Automation and scripting solutions'
        },
        'infrastructure': {
            'keywords': ['server', 'network', 'router', 'switch', 'dns', 'dhcp', 'hardware', 'datacenter', 
                        'rack', 'cables', 'switches', 'infrastructure', 'topology'],
            'description': 'Network and server infrastructure'
        },
        'cloud_services': {
            'keywords': ['cloud', 'aws', 'azure', 'google cloud', 'saas', 'iaas', 'paas', 'office 365', 
                        'migration', 'hybrid cloud', 'multi-cloud'],
            'description': 'Cloud platforms and services'
        },
        'software_management': {
            'keywords': ['software', 'application', 'deployment', 'update', 'patch', 'install', 
                        'package', 'licensing', 'wsus', 'sccm', 'software center'],
            'description': 'Software deployment and management'
        },
        'documentation': {
            'keywords': ['documentation', 'document', 'wiki', 'knowledge base', 'procedures', 'runbook', 
                        'confluence', 'sharepoint', 'process', 'standard operating procedure'],
            'description': 'Documentation and knowledge management'
        },
        'team_management': {
            'keywords': ['team', 'staff', 'management', 'leadership', 'hiring', 'training', 'employee', 
                        'onboarding', 'meeting', 'budget', 'vendor management'],
            'description': 'Team and project management'
        },
        'career_advice': {
            'keywords': ['career', 'job', 'salary', 'promotion', 'certification', 'skills', 'resume', 
                        'interview', 'ccna', 'mcsa', 'comptia', 'training'],
            'description': 'Career development and advice'
        },
        'troubleshooting': {
            'keywords': ['troubleshooting', 'problem', 'issue', 'error', 'fix', 'broken', 'not working', 
                        'help', 'debug', 'diagnose'],
            'description': 'Technical troubleshooting and problems'
        },
        'virtualization': {
            'keywords': ['vmware', 'hyper-v', 'virtualbox', 'vm', 'virtual machine', 'vcenter', 
                        'esxi', 'virtualization', 'container', 'docker'],
            'description': 'Virtualization technologies'
        }
    }
    
    classified_posts = []
    
    for idx, row in posts_df.iterrows():
        # Combine title and text for classification
        text_to_classify = (row['title'] + ' ' + row['selftext']).lower()
        
        # Score each category
        category_scores = {}
        for category, info in categories.items():
            score = 0
            for keyword in info['keywords']:
                # Count occurrences of each keyword
                score += text_to_classify.count(keyword.lower())
            category_scores[category] = score
        
        # Find the category with highest score
        if max(category_scores.values()) > 0:
            primary_category = max(category_scores, key=category_scores.get)
            confidence_score = category_scores[primary_category]
            
            # Find all categories with scores > 0
            matching_categories = [cat for cat, score in category_scores.items() if score > 0]
        else:
            primary_category = 'general'
            confidence_score = 0
            matching_categories = ['general']
        
        classified_posts.append({
            'id': row['id'],
            'title': row['title'],
            'selftext': row['selftext'],
            'score': row['score'],
            'num_comments': row['num_comments'],
            'created_time': row['created_time'],
            'days_ago': row['days_ago'],
            'author': row['author'],
            'is_self_post': row['is_self_post'],
            'permalink': row['permalink'],
            'flair': row['flair'],
            'primary_category': primary_category,
            'all_categories': matching_categories,
            'confidence_score': confidence_score,
            'post_type': row['post_type']
        })
    
    classified_df = pd.DataFrame(classified_posts)
    
    print(f"✅ Classified {len(classified_df)} posts into categories")
    
    return classified_df, categories

def analyze_category_distribution(classified_df, categories):
    """
    Analyze the distribution of posts across categories
    """
    print("\n" + "="*80)
    print("📊 POST CATEGORY DISTRIBUTION")
    print("="*80)
    
    # Category counts
    category_counts = classified_df['primary_category'].value_counts()
    
    print("\n📈 Posts by Category:")
    for category, count in category_counts.items():
        percentage = (count / len(classified_df)) * 100
        category_desc = categories.get(category, {}).get('description', 'General discussions')
        print(f"   {category.replace('_', ' ').title()}: {count} posts ({percentage:.1f}%)")
        print(f"      └── {category_desc}")
    
    # Top posts by category
    print(f"\n🏆 TOP POST IN EACH CATEGORY:")
    for category in category_counts.index[:8]:  # Show top 8 categories
        top_post = classified_df[classified_df['primary_category'] == category].nlargest(1, 'score')
        if not top_post.empty:
            post = top_post.iloc[0]
            print(f"\n   {category.replace('_', ' ').title()}:")
            print(f"   📝 {post['title']}")
            print(f"   📊 Score: {post['score']} | 💬 Comments: {post['num_comments']} | 📅 {post['days_ago']} days ago")
            print(f"   🔗 {post['permalink']}")
    
    return category_counts

def analyze_trending_topics(classified_df):
    """
    Analyze trending topics (recent posts with high engagement)
    """
    print(f"\n🔥 TRENDING TOPICS (High engagement in recent posts)")
    print("="*60)
    
    # Focus on recent posts (last 7 days) with good engagement
    recent_posts = classified_df[classified_df['days_ago'] <= 7].copy()
    
    if recent_posts.empty:
        print("❌ No recent posts found")
        return
    
    # Calculate engagement score
    recent_posts['engagement_score'] = (recent_posts['score'] * 0.7) + (recent_posts['num_comments'] * 0.3)
    
    # Top trending by category
    trending_by_category = recent_posts.groupby('primary_category')['engagement_score'].mean().sort_values(ascending=False)
    
    print("\n📈 Most Engaging Categories (Recent Posts):")
    for category, avg_engagement in trending_by_category.head(5).items():
        post_count = len(recent_posts[recent_posts['primary_category'] == category])
        print(f"   {category.replace('_', ' ').title()}: {avg_engagement:.1f} avg engagement ({post_count} posts)")
    
    # Individual trending posts
    print(f"\n🚀 TOP TRENDING POSTS (Last 7 days):")
    trending_posts = recent_posts.nlargest(5, 'engagement_score')
    
    for i, (idx, post) in enumerate(trending_posts.iterrows(), 1):
        print(f"\n{i}. 📝 {post['title']}")
        print(f"   🏷️  Category: {post['primary_category'].replace('_', ' ').title()}")
        print(f"   📊 Score: {post['score']} | 💬 Comments: {post['num_comments']} | 📅 {post['days_ago']} days ago")
        print(f"   🔗 {post['permalink']}")

def save_classification_results(classified_df, subreddit_name):
    """
    Save classification results to CSV
    """
    if classified_df.empty:
        print("❌ No data to save")
        return
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'{subreddit_name}_post_classification_{timestamp}.csv'
    
    # Select relevant columns for export
    export_df = classified_df[['title', 'primary_category', 'all_categories', 'confidence_score', 
                              'score', 'num_comments', 'days_ago', 'author', 'is_self_post', 
                              'permalink', 'flair']].copy()
    
    export_df.to_csv(filename, index=False)
    print(f"\n💾 Classification results saved to: {filename}")
    return filename

def main():
    """
    Main function to run post classification analysis
    """
    print(f"🚀 Post Classification Analysis for r/{SUBREDDIT_TO_ANALYZE}")
    print("="*70)
    
    # Collect posts
    posts_df = collect_posts_for_classification(SUBREDDIT_TO_ANALYZE, NUM_POSTS_TO_ANALYZE)
    
    if posts_df.empty:
        print("❌ No posts collected")
        return
    
    # Classify posts
    classified_df, categories = classify_posts(posts_df)
    
    # Analyze distribution
    category_counts = analyze_category_distribution(classified_df, categories)
    
    # Analyze trending topics
    analyze_trending_topics(classified_df)
    
    # Save results
    save_classification_results(classified_df, SUBREDDIT_TO_ANALYZE)
    
    print(f"\n" + "="*70)
    print("✅ CLASSIFICATION ANALYSIS COMPLETE!")
    print(f"📊 Analyzed {len(classified_df)} posts")
    print(f"🏷️  Identified {len(category_counts)} active categories")
    print(f"📈 Found trending topics and engagement patterns")
    print(f"💾 Results exported for further analysis")

if __name__ == "__main__":
    main()