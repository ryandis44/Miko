import discord
from Settings.settings import Setting, MikoMember


def all_channel_settings(u, p) -> list:
    return [
        ChatGPT(u, p),
    ]
    
    
class ChatGPT(Setting):

    def __init__(self, u, p):
        super().__init__(
            u=u,
            p=p,
            name = "ChatGPT Integration",
            desc = "**WORK IN PROGRESS BETA FEATURE. May not always work as intended.** Choose to enable ChatGPT Integration and what personality to use",
            emoji = "🌐",
            table = "CHANNELS",
            col = "chatgpt",
            options=[
                discord.SelectOption(
                    label="Enabled: Normal",
                    description="Normal ChatGPT responses. Will answer questions.",
                    value="NORMAL",
                    emoji="🌐"
                ),
                discord.SelectOption(
                    label="Enabled: Sarcastic",
                    description="Sarcastic responses. May go on a tangent or get offended.",
                    value="SARCASTIC",
                    emoji="🤡"
                ),
                discord.SelectOption(
                    label="Enabled: Asshole",
                    description="Short and sweet sarcastic asshole responses.",
                    value="ASSHOLE",
                    emoji="😡"
                ),
                discord.SelectOption(
                    label="Enabled: UwU/lolcat",
                    description="Lolcat and uwu speak with emojis. A lot. SOOO CUWTE UWU.",
                    value="UWU",
                    emoji="🐱"
                ),
                discord.SelectOption(
                    label="Enabled: Relentless",
                    description="Unfiltered and profane responses. Does not give a f*ck.",
                    value="RELENTLESS",
                    emoji="⚠"
                ),
                discord.SelectOption(
                    label="Disabled",
                    description="Disable ChatGPT in this channel",
                    value="DISABLED",
                    emoji="❌"
                )
            ]
        )