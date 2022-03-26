from abc import ABC, abstractmethod


class PluginABC(ABC):
    """
    Base plugin class
    """
    @property
    def name(self):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def is_enabled():
        """Plugins must implement is_enabled"""

    @staticmethod
    @abstractmethod
    def get_config_template():
        """Plugins must implement get_config_template"""


class MergeAllSubclassesConfigsMixin:
    """
    This mixin implements th get_config_templates method
    by iterating over all subclasses and merging their config templates
    """

    @classmethod
    def get_config_template(cls):
        return {
            subclass.name: subclass.get_config_template()
            for subclass in cls.__subclasses__()
        }


class GetEnabledSubclassesMixin:
    """
    This mixin provides a method that returns
    all subclasses that are enabled.
    It should be used with abstract plugins
    """

    @classmethod
    def get_enabled(cls, *args):
        """Retuns a list of instances of cls that are enabled"""
        return [
            subclass(*args)
            for subclass in cls.__subclasses__()
            if subclass.is_enabled()
        ]
