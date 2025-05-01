import discord

from cogs_cmd.Settings.settings import Setting
from Database.tunables import tunables


def all_channel_settings(mc) -> list:
    return [
        TextAI(mc),
        TextAIThreads(mc),
        KarutaOps(mc)
    ]
    
    
class TextAI(Setting):

    def __init__(self, mc):
        super().__init__(
            mc=mc,
            name = "Generative Text AI Integration",
            desc = "Choose to enable Generative Text AI Integration and what personality to use.",
            emoji = "🌐",
            table = "CHANNEL_SETTINGS",
            col = "ai_mode",
            options=tunables('GENERATIVE_AI_MODES')
        )

class TextAIThreads(Setting):

    def __init__(self, mc):
        super().__init__(
            mc=mc,
            name = "Generative AI Threads",
            desc = "Create threads (private chat sessions) in this channel when interacting with Generative Text AI. Helps prevent clutter.",
            emoji = "🧵",
            table = "CHANNEL_SETTINGS",
            col = "ai_threads",
            options=[
                [
                    1,
                    discord.SelectOption(
                        label=f"Enabled: Always",
                        description=f"Create a thread for every response.",
                        value="ALWAYS",
                        emoji="🟢"
                    )
                ],
                [
                    1,
                    discord.SelectOption(
                        label=f"Enabled: Auto (default)",
                        description=f"Let Miko decide when to create a thread.",
                        value="AUTO",
                        emoji="🤖"
                    )
                ],
                [
                    0,
                    discord.SelectOption(
                        label=f"Disabled",
                        description=f"Always respond in this channel.",
                        value="DISABLED",
                        emoji="❌"
                    )
                ]
            ]
        )



class KarutaOps(Setting):

    def __init__(self, mc):
        super().__init__(
            mc=mc,
            name = "Karuta Ops",
            desc = "Delete specific or all Karuta commands for better readability.",
            emoji = "🃏",
            table = "CHANNEL_SETTINGS",
            col = "karuta_ops",
            options=[
                [
                    1,
                    discord.SelectOption(
                        label=f"Enabled: ALL",
                        description=f"Delete all Karuta commands.",
                        value="ALL",
                        emoji="🟢"
                    )
                ],
                [
                    1,
                    discord.SelectOption(
                        label=f"Enabled: Visual commands",
                        description=f"Delete kv, ka",
                        value="VISUAL",
                        emoji="🖼️"
                    )
                ],
                [
                    0,
                    discord.SelectOption(
                        label=f"Disabled",
                        description=f"Do not delete any Karuta commands.",
                        value="DISABLED",
                        emoji="❌"
                    )
                ]
            ]
        )