import discord
from Settings.settings import Setting, MikoMember


def all_channel_settings(u) -> list:
    return [
        ChatGPT(u),
    ]
    
    
class ChatGPT(Setting):

    def __init__(self, u):
        super().__init__(
            u=u,
            name = "ChatGPT Integration",
            desc = "Choose to enable ChatGPT Integration and what mode to use",
            emoji = "🎮",
            table = "CHANNELS",
            col = "chatgpt_mode",
            options=[
                discord.SelectOption(
                    label="Enabled: Normal Mode",
                    description="Enable normal ChatGPT responses in this channel",
                    value="NORMAL",
                    emoji="🌐"
                ),
                discord.SelectOption(
                    label="Enabled: Sarcastic Mode",
                    description="Enable sarcastic ChatGPT responses in this channel",
                    value="SARCASTIC",
                    emoji="🤡"
                ),
                discord.SelectOption(
                    label="Disabled",
                    description="Disable ChatGPT in this channel",
                    value="DISABLED",
                    emoji="❌"
                )
            ]
        )