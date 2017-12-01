import unittest
import os
import logging
import random
from unittest.mock import patch, MagicMock

import json


from tests.helper_func import create_post

from yatcobot.bot import Yatcobot, Config, PeriodicScheduler
from yatcobot.client import TwitterClientRetweetedException

NotficationService = patch('yatcobot.bot.NotificationService').start()

logging.disable(logging.ERROR)


class TestBot(unittest.TestCase):

    tests_path = path = os.path.dirname(os.path.abspath(__file__))

    @patch('yatcobot.bot.TwitterClient')
    @patch('yatcobot.bot.IgnoreList')
    @patch('yatcobot.bot.Config')
    def setUp(self, config_mock, ignore_list_mock, client_mock):
        self.config = config_mock
        self.client = client_mock
        self.bot = Yatcobot('test')

    def test_get_original_tweet_no_retweet(self):
        post = {'id': 1000}
        original = self.bot._get_original_tweet(post)
        self.assertEqual(post, original)

    def test_get_original_tweet_retweet(self):
        post = {'id': 1000, 'retweeted_status': {'id': 1001}}
        original = self.bot._get_original_tweet(post)
        self.assertEqual(post['retweeted_status'], original)

    def test_get_quoted_tweet_similar(self):
        quoted = {'id': 1, 'text': 'test'}
        post = {'id': 2, 'text': 'test', 'quoted_status': quoted}
        quoted_post_full = {'id': 1, 'text': 'test', 'user': {'id:1'}}
        self.bot.client.get_tweet.return_value = quoted_post_full

        r = self.bot._get_quoted_tweet(post)
        self.assertEqual(r, quoted_post_full)

    def test_get_quoted_tweet_quote_of_quotes(self):

        def mock_return(id):
            return mock_return.posts[id]
        mock_return.posts = dict()
        mock_return.posts[1] = {'id': 1, 'text': 'test', 'user': {'id:1'}}
        mock_return.posts[2] = {'id': 2, 'text': 'test', 'quoted_status': mock_return.posts[1]}
        mock_return.posts[3] = {'id': 3, 'text': 'test', 'quoted_status': mock_return.posts[2]}

        self.bot.client.get_tweet.side_effect = mock_return

        r = self.bot._get_quoted_tweet(mock_return.posts[3])
        self.assertEqual(r, mock_return.posts[1])

    def test_get_quoted_tweet_not_similar(self):
        quoted = {'id': 1, 'text': 'test'}
        post = {'id': 2, 'text': 'test sdfsdfsf', 'quoted_status': quoted}
        quoted_post_full = {'id': 1, 'text': 'test', 'user': {'id:1'}}
        self.bot.client.get_tweet.return_value = quoted_post_full

        r = self.bot._get_quoted_tweet(post)
        self.assertEqual(r, post)

    def test_get_quoted_tweet_real_post(self):
        with open(self.tests_path + '/fixtures/post_with_quote.json') as f:
            post = json.load(f)
        quoted_post_full = post.copy()
        quoted_post_full['user'] = {'id': 1}
        self.bot.client.get_tweet.return_value = quoted_post_full

        r = self.bot._get_quoted_tweet(post)
        self.assertEqual(r, quoted_post_full)

    def test_clear_queue_empty(self):
        Config.max_queue = 60
        self.bot.post_queue = MagicMock()
        self.bot.post_queue.__len__.return_value = 0
        self.bot.clear_queue()
        self.assertFalse(self.bot.post_queue.popitem.called)

    def test_clear_queue_full(self):
        self.config.max_queue = 60
        self.bot.post_queue = MagicMock()
        self.bot.post_queue.__len__.return_value = self.config.max_queue + 1

        self.bot.clear_queue()
        self.assertTrue(self.bot.post_queue.popitem.called)
        self.bot.post_queue.popitem.assert_called_with()

    def test_remove_oldest_follow_empty(self):
        follows = [x for x in range(Config.max_follows - 1)]
        self.bot.client.get_friends_ids.return_value = follows
        self.bot.remove_oldest_follow()
        self.assertFalse(self.bot.client.unfollow.called)

    def test_remove_oldest_follow_full(self):
        follows = [x for x in range(Config.max_follows + 1)]
        self.bot.client.get_friends_ids.return_value = follows
        self.bot.remove_oldest_follow()
        self.bot.client.unfollow.assert_called_with(Config.max_follows)

    def test_update_blocked_users(self):
        users = [x for x in range(10)]
        self.bot.ignore_list = list()
        self.bot.client.get_blocks.return_value = users
        self.bot.update_blocked_users()
        self.assertEqual(users, self.bot.ignore_list)

    def test_run(self):
        mock_scheduler = MagicMock(PeriodicScheduler)
        self.bot.scheduler = mock_scheduler
        self.bot.run()
        self.assertEqual(mock_scheduler.enter.call_count, 5)
        self.assertEqual(mock_scheduler.enter_random.call_count, 1)
        self.assertTrue(mock_scheduler.run.called)

    def test_enter_contest_simple_post(self):
        posts = 10
        for i in range(posts):
            self.bot.post_queue[i] = {'id': i, 'text': 'test', 'score': 0, 'user': {'id': random.randint(1, 1000), 'screen_name': 'test'}}

        self.bot.enter_contest()

        self.assertEqual(len(self.bot.post_queue), posts - 1)
        self.assertTrue(self.bot.client.retweet.called)
        self.bot.client.retweet.assert_called_with(0)

    def test_enter_contest_alredy_retweeted(self):
        posts = 10
        self.bot.ignore_list = list()
        for i in range(posts):
            self.bot.post_queue[i] = {'id': i, 'text': 'test', 'score': 0, 'user': {'id': random.randint(1, 1000)}}
        self.bot.client.retweet.side_effect = TwitterClientRetweetedException()

        self.bot.enter_contest()

        self.assertEqual(len(self.bot.post_queue), posts - 1)
        self.assertTrue(self.bot.client.retweet.called)
        self.bot.client.retweet.assert_called_with(0)

        self.assertIn(0, self.bot.ignore_list)

    def test_enter_contest_ignored_id(self):
        posts = 10
        self.bot.ignore_list = [0]
        for i in range(posts):
            self.bot.post_queue[i] = {'id': i, 'text': 'test', 'score': 0, 'user': {'id': 0}}

        self.bot.enter_contest()

        self.assertEqual(len(self.bot.post_queue), posts - 1)
        self.assertFalse(self.bot.client.retweet.called)

    def test_insert_post_to_queue(self):
        post = {'id': 0, 'text': 'test', 'user': {'id': random.randint(1, 1000), 'screen_name': 'test'}, 'retweeted': False}

        self.bot._insert_post_to_queue(post)

        self.assertIn(post['id'], self.bot.post_queue)

    def test_insert_post_to_queue_ignore(self):
        post = {'id': 0, 'text': 'test', 'user': {'id': random.randint(1, 1000), 'screen_name': 'test'}, 'retweeted': False}
        self.bot.ignore_list = [0]
        self.bot._insert_post_to_queue(post)

        self.assertNotIn(post['id'], self.bot.post_queue)

    def test_insert_post_to_queue_retweeted(self):
        post = {'id': 0, 'text': 'test', 'user': {'id': random.randint(1, 1000), 'screen_name': 'test'}, 'retweeted': True}
        self.bot.ignore_list = [0]
        self.bot._insert_post_to_queue(post)

        self.assertNotIn(post['id'], self.bot.post_queue)

    def test_insert_post_to_queue_blocked_user(self):
        post = {'id': 0, 'text': 'test', 'user': {'id': 1, 'screen_name': 'test'}, 'retweeted': False}
        self.bot.ignore_list = [1]
        self.bot._insert_post_to_queue(post)

        self.assertNotIn(post['id'], self.bot.post_queue)

    def test_insert_post_to_queue_that_has_a_quote_thats_deleted(self):
        with open(self.tests_path + '/fixtures/deleted_quote.json') as f:
            post = json.load(f)

        self.bot._insert_post_to_queue(post)

        self.assertNotIn(post['id'], self.bot.post_queue)

    def test_scan_new_contests(self):
        Config.search_queries = ['test1']
        posts = list()
        for i in range(2):
            posts.append({'id': i, 'text': 'test', 'retweet_count': 1,
                          'user': {'id': random.randint(1, 1000), 'screen_name': 'test'}, 'retweeted': False,
                          'created_at':'Thu Oct 08 08:34:51 +0000 2015'})

        self.bot.client = MagicMock()
        self.bot.client.search_tweets.return_value = posts

        self.bot.scan_new_contests()

        self.bot.client.search_tweets.assert_called_once_with('test1', 50, language=None)
        self.assertEqual(len(self.bot.post_queue), 2)

    def test_favorite(self):
        Config.fav_keywords = [' favorite ']
        self.bot.client = MagicMock()
        post = ({'id': 0, 'text': 'test favorite tests', 'user': {'id': random.randint(1, 1000), 'screen_name': 'test'}, 'retweeted': False})

        self.bot.check_for_favorite(post)

        self.bot.client.favorite.assert_called_once_with(post['id'])

    def test_follow(self):
        Config.follow_keywords = [' follow ']
        self.bot.client = MagicMock()
        post = ({'id': 0, 'text': 'test follow tests', 'user': {'id': random.randint(1, 1000), 'screen_name': 'test'}, 'retweeted': False})

        self.bot.check_for_follow(post)

        self.bot.client.follow.assert_called_once_with(post['user']['screen_name'])

    def test_get_keyword_mutations(self):
        keyword = 'keyword'
        target_mutations = ['#keyword', ' keyword ', '.keyword', 'keyword ', ' keyword', 'keyword.', ',keyword', 'keyword,']
        mutations = self.bot._get_keyword_mutations(keyword)
        self.assertEqual(len(mutations), len(target_mutations))
        for mutation in mutations:
            self.assertIn(mutation, target_mutations)

    def test_check_new_mentions_empty(self):
        posts = [create_post()]
        self.bot.client.get_mentions_timeline = MagicMock(return_value=posts)

        self.bot.check_new_mentions()

        self.bot.client.get_mentions_timeline.assert_called_once_with(count=1)
        self.assertEqual(self.bot.last_mention, posts[0])

    def test_check_new_mentions(self):
        posts = [create_post()]
        self.bot.client.get_mentions_timeline = MagicMock(return_value=posts)
        self.bot.last_mention = create_post()
        last_id = self.bot.last_mention['id']

        self.bot.check_new_mentions()

        self.bot.client.get_mentions_timeline.assert_called_once_with(since_id=last_id)
        self.assertEqual(self.bot.last_mention, posts[0])
        self.assertTrue(NotficationService.return_value.send_notification.called)

    def test_check_new_mentions_no_notifiers_enabled(self):

        self.bot.client.get_mentions_timeline = MagicMock()
        self.bot.notification = MagicMock()
        self.bot.notification.is_enabled.return_value = False
        NotficationService.reset_mock()

        self.bot.check_new_mentions()

        self.assertFalse(self.bot.client.get_mentions_timeline.called)
        self.assertFalse(NotficationService.return_value.send_notification.called)
        self.assertTrue(self.bot.notification.is_enabled)

