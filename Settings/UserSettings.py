import discord
from Settings.settings import Setting

def all_user_settings() -> list:
    return [
        TrackPlaytime(),
        TrackVoicetime(),
        BigEmojis(),
    ]

class TrackPlaytime(Setting):

    def __init__(self):
        super().__init__(
            name = "Playtime Tracking",
            desc = "Track your playtime (only works when status set to ONLINE and your activity status is enabled for this guild)",
            emoji = "🎮",
            table = "USER_SETTINGS",
            col = "track_playtime",
            toggleable = True
        )

# class PublicPlaytime(Setting):

#     def __init__(self):
#         super().__init__(
#             name = "Public Playtime (WIP)",
#             desc = "Track playtime but only you can see your tracked stats.",
#             emoji = "🎮",
#             table = "USER_SETTINGS",
#             col = "public_playtime",
#             toggleable = False
#         )

class TrackVoicetime(Setting):

    def __init__(self):
        super().__init__(
            name = "Voicetime Tracking",
            desc = "Track your voicetime per guild Miko is in.",
            emoji = "🔈",
            table = "USER_SETTINGS",
            col = "track_voicetime",
            toggleable = True
        )

# class PublicVoicetime(Setting):

#     def __init__(self):
#         super().__init__(
#             name = "Public Voicetime (WIP)",
#             desc = "Track voicetime but only you can see your tracked stats.",
#             emoji = "🎮",
#             table = "USER_SETTINGS",
#             col = "public_voicetime",
#             toggleable = False
#         )

class BigEmojis(Setting):

    def __init__(self):
        super().__init__(
            name = "Big Emojis",
            desc = "Enlarge custom emojis for a better viewing experience (only works on non-default emojis)",
            emoji = "😂",
            table = "USER_SETTINGS",
            col = "big_emojis"
        )