import json
import os
from dataclasses import dataclass
from math import ceil

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

@dataclass
class Window:
  height: int
  width: int

  @staticmethod
  def from_stats(stats):
    return Window(stats['height'], stats['width'])

  @property
  def window_height(self):
    return ceil(self.height * 0.8)

  @property
  def window_width(self):
    return ceil(self.width * 0.8)

class Neovim:
  def __init__(self, client):
    self.client = client

  def write(self, message):
    self.client.api.echo([[message, '']], True, {})

  def open_window(self):
    window = Window.from_stats(self.client.api.list_uis()[0])

    self.client.api.open_win(
      self.client.api.create_buf(False, True),
      True,
      {
        'border': 'rounded',
        'col': ceil((window.width - window.window_width) / 2),
        'height': window.window_height,
        'relative': 'win',
        'row': ceil((window.height - window.window_height) / 2) - 1,
        'width': window.window_width,
      }
    )

class Bot:
  def __init__(self, client):
    self.client = client

  def refresh(self):
    self.client.refresh_session()

  def query(self, message):
    return self.client.get_chat_response(message)['message']

@neovim.plugin
class ChatGPTPlugin:
  def __init__(self, nvim):
    self.bot = Bot(Chatbot(Config.load().as_dict()))
    self.nvim = Neovim(nvim)

  @neovim.command('ChatGPT', nargs='+')
  def chat(self, args):
    self.bot.refresh()

    if not args:
      self.nvim.open_window()
    else:
      try:
        self.nvim.write(self.bot.query(' '.join(args)))
      except Exception as error:
        self.nvim.write(f'error: Failed to get response from ChatGPT')
