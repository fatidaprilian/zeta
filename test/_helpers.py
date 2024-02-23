import datetime
import unittest
try:
    # Python 3
    import unittest.mock as mock
except ImportError:
    import mock


from functools import partial, wraps
from hypothesis.strategies import just, lists, text
from lala import config
from os import close, remove
from tempfile import mkstemp
from twisted.internet.defer import Deferred


class LalaTestCase(unittest.TestCase):
    def setUp(self):
        (fd, self.configfile) = mkstemp()
        close(fd)
        with open(self.configfile, "w") as _file:
            self.writeConfigFile(_file)
        config._initialize(filename=self.configfile)

        bot_patcher = mock.patch('lala.util._BOT')
        bot_patcher.start()
        self.addCleanup(bot_patcher.stop)

    def writeConfigFile(self, _file):
        pass

    def tearDown(self):
        # For tests executed with hypothesis' execute_example, tearDown is
        # called twice.
        if self.configfile is not None:
            remove(self.configfile)
        self.configfile = None


class NewDate(datetime.date):
    @classmethod
    def today(cls):
        return cls(2012, 12, 10)


class NewDateTime(datetime.datetime):
    @classmethod
    def now(cls):
        return cls(2012, 12, 10, 00, 00, 00, 00, None)


class DeferredHelper(Deferred):
    def __init__(self, data=None):
        Deferred.__init__(self)
        self.data = data

    def callback(self, result=None):
        if result is None:
            result = self.data
        return Deferred.callback(self, result)

    def errback(self, failure=None):
        if failure is None:
            failure = self.data
        return Deferred.errback(self, failure)

    def __call__(self, *args):
        self.args = args
        return self


def mock_is_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with mock.patch("lala.pluginmanager.is_admin") as mocked:
            mocked.return_value = True
            return f(*args, **kwargs)
    return wrapper


#: Like :meth:`text`, but preconfigured for irc nicknames
irc_nickname = partial(text,
                       alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ|",  # noqa
                       min_size=1)

#: A function returning a list of IRC nicknames
irc_nickname_list = partial(lists, irc_nickname())


#: Like :meth:`text`, but preconfigured for bot commands
bot_command = partial(text,
                      alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ|,",  # noqa
                      min_size=1)

#: A function returning a list of bot command names
bot_command_list = partial(lists, bot_command())


#: A function returning a function returning a command function
command_func_generator = just(lambda: lambda user, channel, text: None)
