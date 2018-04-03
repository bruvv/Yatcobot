from abc import abstractmethod

from yatcobot.config import TwitterConfig
from yatcobot.plugins import PluginABC


class FilterABC(PluginABC):
    """
    Superclass of filtering methods for filtering the queue
    """

    @abstractmethod
    def filter(self, queue):
        """Subclasses must implement filter"""

    @staticmethod
    @abstractmethod
    def is_enabled():
        """Action must implement is_enabled"""

    @staticmethod
    def get_enabled():
        """Retuns a list of instances of actions that are enabled"""
        enabled = list()
        for cls in FilterABC.__subclasses__():
            if cls.is_enabled():
                enabled.append(cls())
        return enabled


class FilterMinRetweets(FilterABC):

    def filter(self, queue):
        """
        Removes all post that have less rewteets than min_retweets defined at config
        :param queue: Posts Queue
        """
        ids_to_remove = list()

        for post_id, post in queue.items():
            if post['retweet_count'] < TwitterConfig.get().search.filter.min_retweets.number:
                ids_to_remove.append(post_id)

        for post_id in ids_to_remove:
            del queue[post_id]

    @staticmethod
    def is_enabled():
        return TwitterConfig.get().search.filter.min_retweets.enabled