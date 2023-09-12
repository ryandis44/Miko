import discord
from Settings.settings import Setting

def all_guild_settings(u, p) -> list:
    return [
        BigEmojisGuild(u, p),
        NickInCtx(u, p),
        GreetNewMembers(u, p),
        NotifyMemberLeave(u, p),
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

class GreetNewMembers(Setting):

    def __init__(self, u, p):
        super().__init__(
            u=u,
            p=p,
            name = "Greet new members",
            desc = "Send a message to the system channel welcoming new members",
            emoji = "👋",
            table = "SERVERS",
            col = "greet_new_members"
        )

class NotifyMemberLeave(Setting):

    def __init__(self, u, p):
        super().__init__(
            u=u,
            p=p,
            name = "Member leave messages",
            desc = "Send a message to system channel when a member leaves the server",
            emoji = "✌",
            table = "SERVERS",
            col = "notify_member_leave"
        )