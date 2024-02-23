"""Helpers to be used with plugins"""
import lala.pluginmanager

from types import FunctionType
try:
    from inspect import getfullargspec
except ImportError:
    from inspect import getargspec

from re import compile
from six import string_types, PY3


_BOT = None


class command(object):  # noqa: N801
    """ Decorator to register a command. The name of the command is the
        `__name__` attribute of the decorated function.
        Example::

            @command
            def heyiamacommand(user, channel, text):
                pass

        You can also pass a ``command`` parameter to overwrite the name of the
        command::

            @command(command="yetanothercommand")
            def command_with_a_really_stupid_or_insanely_long_name(user,
            channel, text):
                pass

        ``aliases`` can be a list of names under which the function will be
        available in addition to its primary name.

        An additional argument, ``admin_only`` can be used to make a function
        available to admins only::

            @command(admin_only=True)
            def give_me_the_one_ring(user, channel, text):
                pass

        .. versionadded:: 0.5
        If the function returns a :class:`twisted.internet.defer.Deferred` or a
        generator function that's generating them, an
        `Errback <https://twistedmatrix.com/documents/current/core/howto/defer.html#errbacks>`_
        will automatically be added to the Deferred(s).

        .. versionchanged:: 0.5
        The third argument received by a command function used to include the
        name of the command itself. Since version 0.5 this is no longer the case.
    """  # noqa
    def __init__(self, command=None, admin_only=False, aliases=None):
        self.admin_only = admin_only
        self.aliases = aliases
        if isinstance(command, FunctionType):
            # Used like
            # @command
            # def foo(...):
            #     pass
            self.cmd = None
            self._handle_func(command)
        elif command is None:
            # This happens when any of the keyword arguments (but not `command`)
            # is set when decorating a function like
            # @command(admin_only=True)
            # def foo(user, channel, text):
            #   pass
            self.cmd = None
        elif not isinstance(command, string_types):
            raise TypeError(
                "The command should be either a str or unicode but it's %s"
                % type(command))
        else:
            self.cmd = command

    def __call__(self, func):
        self._handle_func(func)

    def _handle_func(self, f):
        if _check_args(f):
            self.cmd = self.cmd or f.__name__
            self.func = f
            self._register()
        else:
            raise TypeError(
                "A callback function should take exactly 3 arguments")

    def _register(self):
        lala.pluginmanager.register_callback(self.cmd,
                                             self.func,
                                             self.admin_only,
                                             self.aliases)


def on_join(f):
    """Decorator for functions reacting to joins

    :param f: The function which should be called on joins."""
    if _check_args(f, 2):
        lala.pluginmanager.register_join_callback(f)
    else:
        raise TypeError("A callback function should takes exactly 2 arguments")


class regex(object):  # noqa: N801
    r"""Decorator to register a regex. Example::

           @regex("(https?://.+)\s?")
           def somefunc(user, channel, text, match_obj):
               pass

       ``match_obj`` is a :py:class:`re.MatchObject`.

       :param regex: A :py:class:`re.RegexObject` or a string representing a
                     regular expression.
    """
    def __init__(self, regex):
        if not hasattr(regex, "match") and isinstance(regex, string_types):
            regex = compile(regex)
        self.re = regex

    def __call__(self, func):
        if _check_args(func, 4):
            lala.pluginmanager.register_regex(self.re, func)
        else:
            raise TypeError(
                "A regex callback function should take exactly 4 arguments")


def msg(target, message, log=True):
    """Send a message to a target.

    :param str target: Target to send the message to. Can be a channel or user
    :param message: One or more messages to send
    :type message: str or [str]
    :param bool log: Whether or not to log the message
    """
    try:
        if not isinstance(message, string_types):
            for _message in iter(message):
                if _message == "":
                    continue
                _BOT.msg(target, _message, log)
        else:
            if message == "":
                return
            _BOT.msg(target, message, log)
    except TypeError:
        if message == "":
            return
        _BOT.msg(target, message, log)


def _check_args(f, count=3):
    """ Checks whether the number of arguments ``f`` takes equals
    ``count``."""
    if PY3:
        args, varargs, varkw, defaults, keywordonly, kwod, _ = getfullargspec(f)
        if defaults:
            args = args[:-defaults]
        return (varargs is not None or
                varkw is not None or
                len(keywordonly) != 0 or
                kwod is not None or
                len(args) == count)
    else:
        args, varargs, varkw, defaults = getargspec(f)
        if defaults:
            args = args[:-defaults]
        return (varargs is not None or
                varkw is not None or
                len(args) == count)
