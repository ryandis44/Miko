from Settings.settings import Setting, tunables


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
            options=tunables('OPENAI_PERSONALITIES')
        )