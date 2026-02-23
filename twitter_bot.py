import os
import sys
import tweepy
import json
from datetime import datetime

base_dir = os.path.dirname(__file__)
infographic_path = os.path.join(base_dir, "infographic.png")
data_path = os.path.join(base_dir, "data.json")

# Authentication credentials - PLEASE FILL THESE IN
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
ACCESS_SECRET = "YOUR_ACCESS_SECRET"
BEARER_TOKEN = "YOUR_BEARER_TOKEN"

def generate_tweet_text(data):
    date_str = data['date'] # Can format nicely if needed
    
    # Example format capturing attention visually
    text = f"📊 TEFAS Günlük Fon Özeti ({date_str})\n\n"
    text += "Bugün paranın en çok girdiği ve çıktığı fonlar ile takipteki fonların (TLY, DFI, PHE) hem günlük hem de haftalık performansı tablomuzda! 🚀📉\n\n"
    text += "İncelemek için görsele göz atın 👇\n\n"
    text += "#Borsa #Fon #Yatırım #TEFAS"
    
    return text

def main():
    if not os.path.exists(infographic_path):
        print(f"Error: Could not find image at {infographic_path}")
        sys.exit(1)
        
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    tweet_text = generate_tweet_text(data)
    print("Generated Tweet Text:\n--------------")
    print(tweet_text)
    print("--------------")
    
    # 1. Authenticate with Twitter API v1.1 for media upload
    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
    api = tweepy.API(auth)
    
    try:
        print("Uploading image to Twitter...")
        media = api.media_upload(infographic_path)
        print(f"Media uploaded successfully. Media ID: {media.media_id}")
        
        # 2. Authenticate with Twitter API v2 for posting tweet (since free/basic tiers usually only allow v2 for posting)
        client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_SECRET
        )
        
        print("Posting tweet...")
        response = client.create_tweet(text=tweet_text, media_ids=[media.media_id])
        print(f"Tweet posted successfully! ID: {response.data['id']}")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        
if __name__ == "__main__":
    main()
