import discord
from Settings.settings import Setting

def all_guild_settings(u, p) -> list:
    return [
        BigEmojisGuild(u, p),
        NickInCtx(u, p),
    ]

class BigEmojisGuild(Setting):

    def __init__(self, u, p):
        super().__init__(
            u=u,
            p=p,
            name = "Guild Big Emojis",
            desc = "Enlarge custom emojis for a better viewing experience (only works on non-default emojis)",
            emoji = "😂",
            table = "SERVERS",
            col = "big_emojis"
        )

class NickInCtx(Setting):

    def __init__(self, u, p):
        super().__init__(
            u=u,
            p=p,
            name = "Guild Nicknames in Context",
            desc = "Whether or not to use nicknames when referencing users in embeds",
            emoji = "✏",
            table = "SERVERS",
            col = "nickname_in_ctx"
        )