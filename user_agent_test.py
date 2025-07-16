import requests
import json
import time

def test_reddit_json_comprehensive():
    print("Testing Reddit's public JSON API...")
    print("=" * 50)
    
    # Test different endpoints and headers
    test_cases = [
        {
            'url': 'https://www.reddit.com/r/funny/hot.json?limit=3',
            'headers': {'User-Agent': 'python:RedditAnalyzer:v1.0.0 (by /u/External_Necessary48)'}
        },
        {
            'url': 'https://www.reddit.com/r/AskReddit/hot.json?limit=3',
            'headers': {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        },
        {
            'url': 'https://www.reddit.com/r/python/hot.json?limit=3',
            'headers': {'User-Agent': 'DataAnalyzer/1.0'}
        },
        {
            'url': 'https://old.reddit.com/r/sysadmin/hot.json?limit=3',
            'headers': {'User-Agent': 'python:RedditAnalyzer:v1.0.0 (by /u/External_Necessary48)'}
        }
    ]
    
    working_configs = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 Test {i+1}: {test_case['url']}")
        print(f"   User-Agent: {test_case['headers']['User-Agent']}")
        
        try:
            response = requests.get(test_case['url'], headers=test_case['headers'], timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    posts = data['data']['children']
                    
                    print(f"   ✅ SUCCESS! Retrieved {len(posts)} posts")
                    
                    # Show first post as proof
                    if posts:
                        first_post = posts[0]['data']
                        print(f"   📝 Sample post: {first_post['title'][:40]}...")
                        print(f"   📊 Score: {first_post['score']}, Comments: {first_post['num_comments']}")
                    
                    working_configs.append(test_case)
                    
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON response")
                    
            elif response.status_code == 429:
                print(f"   ⏰ Rate limited - need to wait")
            elif response.status_code == 403:
                print(f"   🚫 Forbidden - blocked")
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        
        # Small delay between requests
        time.sleep(2)
    
    print(f"\n📊 Results Summary:")
    print(f"✅ Working configurations: {len(working_configs)}")
    print(f"❌ Failed configurations: {len(test_cases) - len(working_configs)}")
    
    if working_configs:
        print(f"\n🎯 Use this working configuration:")
        best_config = working_configs[0]
        print(f"   URL pattern: {best_config['url']}")
        print(f"   User-Agent: {best_config['headers']['User-Agent']}")
        return True
    else:
        print(f"\n❌ No working configurations found")
        return False

if __name__ == "__main__":
    test_reddit_json_comprehensive()