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

class Neovim:
  def __init__(self, client):
    self.client = client

  def write(self, message):
    self.client.api.echo([[message, '']], True, {})

@neovim.plugin
class ChatGPTPlugin:
  def __init__(self, nvim):
    self.nvim = Neovim(nvim)
    self.bot = Chatbot(Config.load().as_dict())

  @neovim.command('ChatGPT', nargs='1')
  def chat(self, args):
    try:
      self.bot.refresh_session()
      self.nvim.write(self.bot.get_chat_response(args[0])['message'])
    except Exception as error:
      self.nvim.write(f'error: Failed to get response from ChatGPT')
