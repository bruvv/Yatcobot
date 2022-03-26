import argparse
import json
from yatcobot.client import TwitterClient
from yatcobot.config import TwitterConfig, Config

parser = argparse.ArgumentParser(description='Download a tweet to json')
parser.add_argument('tweet_id', metavar='id', type=int)
parser.add_argument('--config', '-c', dest='config', default='../config.yaml', help='Path of the config file')

args = parser.parse_args()

Config.load(args.config)

client = TwitterClient(TwitterConfig.get().consumer_key,
                       TwitterConfig.get().consumer_secret,
                       TwitterConfig.get().access_token_key,
                       TwitterConfig.get().access_token_secret)

tweet = client.get_tweet(args.tweet_id)

with open(f'{args.tweet_id}.json', 'w') as f:
    json.dump(tweet, f, indent=2)

