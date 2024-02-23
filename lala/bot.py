import logging
import lala.pluginmanager

from twisted.words.protocols import irc
from lala import config, __version__

# From https://www.alien.net.au/irc/irc2numerics.html
# This tells us a user has registered and identified for his nick
irc.symbolic_to_numeric["RPL_WHOISREGNICK"] = "307"
irc.numeric_to_symbolic["307"] = "RPL_WHOISREGNICK"


class Lala(irc.IRCClient):
    versionName = "lala"
    versionNum = __version__
    lineRate = 1

    def __init__(self, *args, **kwargs):
        self.identified_admins = []

    @property
    def nickname(self):
        return self.factory.nickname

    @nickname.setter
    def nickname(self, value):
        self.factory.nickname = value

    def signedOn(self):  # noqa: N802
        """ Called after a connection to the server has been established.

        Joins all configured channels and identifies with Nickserv."""
        self.factory.resetDelay()
        logging.debug("Joining %s" % self.factory.channel)
        if self.factory.channel:
            self.join(self.factory.channel)
        if self.factory.nspassword is not None:
            logging.info("Identifying with Nickserv")
            self.msg("Nickserv", "identify %s" % self.factory.nspassword,
                     log=False)

        if config._CFG.getboolean("base", "nickserv_admin_tracking"):
            for admin in self._list_of_admins():
                self.whois(admin)

    def joined(self, channel):
        """ Called after joining a channel."""
        logging.info("Successfully joined %s" % channel)

    def userJoined(self, user, channel):  # noqa: N802
        """ Handles join events."""
        logging.debug("%s joined %s" % (user, channel))
        lala.pluginmanager.on_join(user, channel)

    def privmsg(self, user, channel, message):
        """ Handles received messages."""
        user = user.split("!")[0]
        if channel == self.nickname:
            # This is true if the bot was queried
            channel = user
        message = self._decode_if_required(message)
        logging.debug("%s: %s" % (user, message))
        lala.pluginmanager._handle_message(user, channel, message)

    def msg(self, channel, message, log, length=None):
        """ Sends ``message`` to ``channel``.

        Depending on ``log``, the message will be logged or not.

        Do not use this method from plugins, use :meth:`lala.util.msg` instead.
        """
        if log:
            logging.debug("%s: %s" % (self.nickname, message))
        irc.IRCClient.msg(self, channel, message, length)

    def action(self, user, channel, data):
        """ Called when a user performs an ACTION on a channel."""
        user = user.split("!")[0]
        logging.info("ACTION: %s %s" % (user, data))

    def noticed(self, user, channel, message):
        """ Same as :py:meth:`lala.bot.Lala.privmsg` for NOTICEs."""
        user = user.split("!")[0]
        message = self._decode_if_required(message)
        logging.info("NOTICE: %s: %s" % (user, message))

    def irc_RPL_WHOISREGNICK(self, prefix, params):  # noqa: N802
        user = params[1]
        logging.debug("%s is a registered nick" % user)
        if (self.factory.nspassword is not None and
            user in self._list_of_admins()):
            self.identified_admins.append(user)

    def userLeft(self, user, channel):  # noqa: N802
        self._potential_admin_left(user)

    def userQuit(self, user, message):  # noqa: N802
        self._potential_admin_left(user)

    def userKicked(self, user, message):  # noqa: N802
        self._potential_admin_left(user)

    def modeChanged(self, user, channel, set, modes, args):  # noqa: N802
        """The mode of a user has been changed. If it was added by ``Chanserv``
        and the user is in the admin list, append him to ``identified_admins``.
        """
        if self.factory.nspassword is not None and set and user == "Chanserv"\
           and user in self._list_of_admins():
            logging.info("Assuming %s is identified" % user)
            self.identified_admins.append(user)

    def _potential_admin_left(self, user):
        """Someone has left a channel or the network. Check if ``user`` is an
        an admin and remove him from the ``identified_admins`` list because
        if he joins again we don't know if it's still the same user."""
        if not config._CFG.getboolean("base", "nickserv_admin_tracking"):
            return
        if user in self._list_of_admins() and user in self.identified_admins:
            logging.debug("Removing %s from the admin list" % user)
            self.identified_admins.remove(user)

    def _potential_admin_joined(self, user):
        if not config._CFG.getboolean("base", "nickserv_admin_tracking"):
            return
        if (user in self._list_of_admins() and
            user not in self.identified_admins):
            logging.debug("WHOISing %s" % user)
            self.whois(user)

    @staticmethod
    def _list_of_admins():
        return config._get("base", "admins").split(config._LIST_SEPARATOR)

    @staticmethod
    def _decode_if_required(message):
        if isinstance(message, bytes):
            try:
                message = message.decode("utf-8")
            except Exception:
                message = message.decode(config._get("base",
                                                     "fallback_encoding"))
        return message
