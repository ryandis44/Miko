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
            desc = "Choose to enable ChatGPT Integration and what mode to use",
            emoji = "🎮",
            table = "CHANNELS",
            col = "chatgpt",
            options=[
                discord.SelectOption(
                    label="Enabled: Normal Mode",
                    description="Normal ChatGPT responses. Will answer questions.",
                    value="NORMAL",
                    emoji="🌐"
                ),
                discord.SelectOption(
                    label="Enabled: Sarcastic Mode",
                    description="Sarcastic responses. May go on a tangent or might get offended.",
                    value="SARCASTIC",
                    emoji="🤡"
                ),
                discord.SelectOption(
                    label="Enabled: Asshole Mode",
                    description="Short and sweet sarcastic asshole responses.",
                    value="ASSHOLE",
                    emoji="😡"
                ),
                discord.SelectOption(
                    label="Enabled: UwU/lolcat Mode",
                    description="Lolcat and uwu speak. I don't think it even knows how to answer questions.",
                    value="UWU",
                    emoji="🐱"
                ),
                discord.SelectOption(
                    label="Enabled: Unfiltered Mode",
                    description="Unfiltered and profane responses. Will not answer questions. At all.",
                    value="UNFILTERED",
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