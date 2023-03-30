import discord
from Settings.settings import Setting, MikoMember

def all_user_settings(u) -> list:
    return [
        TrackPlaytime(u),
        TrackVoicetime(u),
        BigEmojis(u),
    ]

class TrackPlaytime(Setting):

    def __init__(self, u):
        super().__init__(
            u=u,
            name = "Playtime Tracking",
            desc = "Track your playtime (only works when status set to ONLINE and your activity status is enabled for this guild)",
            emoji = "🎮",
            table = "USER_SETTINGS",
            col = "track_playtime"
        )

# class PublicPlaytime(Setting):

#     def __init__(self, u):
#         super().__init__(
#             u=u,
#             name = "Public Playtime (WIP)",
#             desc = "Track playtime but only you can see your tracked stats.",
#             emoji = "🎮",
#             table = "USER_SETTINGS",
#             col = "public_playtime"
#         )

class TrackVoicetime(Setting):

    def __init__(self, u):
        super().__init__(
            u=u,
            name = "Voicetime Tracking",
            desc = "Track your voicetime per guild Miko is in.",
            emoji = "🔈",
            table = "USER_SETTINGS",
            col = "track_voicetime"
        )

# class PublicVoicetime(Setting):

#     def __init__(self, u):
#         super().__init__(
#             u=u,
#             name = "Public Voicetime (WIP)",
#             desc = "Track voicetime but only you can see your tracked stats.",
#             emoji = "🎮",
#             table = "USER_SETTINGS",
#             col = "public_voicetime"
#         )

class BigEmojis(Setting):

    def __init__(self, u):
        super().__init__(
            u=u,
            name = "Big Emojis",
            desc = "Enlarge custom emojis for a better viewing experience (only works on non-default emojis)",
            emoji = "😂",
            table = "USER_SETTINGS",
            col = "big_emojis"
        )