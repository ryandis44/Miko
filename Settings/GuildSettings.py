import discord
from Settings.settings import Setting

def all_guild_settings() -> list:
    return [
        BigEmojisGuild(),
        NickInCtx(),
    ]

class BigEmojisGuild(Setting):

    def __init__(self):
        super().__init__(
            name = "Big Emojis",
            desc = "Enlarge custom emojis for a better viewing experience (only works on non-default emojis)",
            emoji = "😂",
            table = "SERVERS",
            col = "big_emojis"
        )

class NickInCtx(Setting):

    def __init__(self):
        super().__init__(
            name = "Nicknames in Context",
            desc = "Whether or not to use nicknames when referencing users in embeds",
            emoji = "✏",
            table = "SERVERS",
            col = "nickname_in_ctx"
        )