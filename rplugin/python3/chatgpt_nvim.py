import json
import os
from dataclasses import dataclass

import neovim
from dotenv import load_dotenv
from revChatGPT.revChatGPT import Chatbot

CONFIG_PATH = '~/.chatgpt-nvim.json'
DEFAULT_CONFIG = {'authorization': '', 'session_token': ''}

@dataclass
class Config:
  authorization: str
  session_token: str

  @staticmethod
  def load():
    path = os.path.expanduser(CONFIG_PATH)

    if not os.path.exists(path):
      with open(path, 'w') as file:
        json.dump(DEFAULT_CONFIG, file)

    with open(path, 'r') as file:
      return Config(**json.load(file))

  def as_dict(self):
    return {
      'Authorization': self.authorization, 'session_token': self.session_token
    }

@neovim.plugin
class ChatGPTPlugin:
  def __init__(self, nvim):
    self.nvim = nvim
    self.bot = self.__bot()

  def __bot(self):
    chatbot = Chatbot(Config.load().as_dict(), conversation_id=None)
    chatbot.reset_chat()
    chatbot.refresh_session()
    return chatbot

  @neovim.command('Chat', nargs='1')
  def chat(self, args):
    try:
      self.nvim.api.echo([[self.bot.get_chat_response(args[0])['message'], '']], True, {})
    except Exception as error:
      self.nvim.api.echo([[f'error: {error}', '']], True, {})
