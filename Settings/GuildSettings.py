import discord
from Settings.settings import Setting

def all_guild_settings(u) -> list:
    return [
        BigEmojisGuild(u),
        NickInCtx(u),
    ]

class BigEmojisGuild(Setting):

    def __init__(self, u):
        super().__init__(
            u=u,
            name = "Guild Big Emojis",
            desc = "Enlarge custom emojis for a better viewing experience (only works on non-default emojis)",
            emoji = "😂",
            table = "SERVERS",
            col = "big_emojis"
        )

class NickInCtx(Setting):

    def __init__(self, u):
        super().__init__(
            u=u,
            name = "Guild Nicknames in Context",
            desc = "Whether or not to use nicknames when referencing users in embeds",
            emoji = "✏",
            table = "SERVERS",
            col = "nickname_in_ctx"
        )