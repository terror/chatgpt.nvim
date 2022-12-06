import json
import os
from dataclasses import dataclass
from enum import Enum
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

class Anchor(Enum):
  NE = "NE"
  NW = "NW"
  SE = "SE"
  SW = "SW"

class Align(Enum):
  E = "E"
  N = "N"
  NE = "NE"
  S = "S"
  SE = "SE"
  SW = "SW"
  W = "W"
  CENTER = "CENTER"

def get_parent_dim(vim, relative, win):
  if relative == "editor":
    total_width, total_height = vim.options["columns"], vim.options["lines"] - vim.options["cmdheight"]
  else:
    if win is None: win = vim.current.window
    total_width, total_height = win.width, win.height
  return (total_width, total_height)

def calc_dim(vim, width, height, relative, win):
  total_width, total_height = get_parent_dim(vim, relative, win)
  if isinstance(width, float):
    width = int(round(width * (total_width - 2)))
  if isinstance(height, float):
    height = int(round(height * (total_height - 2)))
  return width, height, total_width, total_height

def open_win(
  vim,
  buffer,
  align=Align.CENTER,
  anchor=Anchor.NW,
  border="shadow",
  col: int = 0,
  enter=True,
  height=0.9,
  relative="editor",
  row: int = 0,
  scrollable=False,
  width=0.9,
  win=None,
):
  width, height, total_width, total_height = calc_dim(
      vim, width, height, relative, win
  )

  if align is not None:
    if relative == "cursor":
      raise Exception("Align requires relative = win/editor")
    anchor, row, col = calc_alignment(
        align, width, height, total_width, total_height
    )

  window = vim.api.open_win(
    buffer,
    enter,
    {
      "anchor": anchor.value,
      "border": border,
      "col": col,
      "height": height,
      "relative": relative,
      "row": row,
      "style": "minimal",
      "width": width,
    },
  )

  if not scrollable:
    window.options['scrolloff'] = window.options['sidescrolloff'] = 0

  return window

def calc_alignment(
  align: Align, width: int, height: int, total_width: int, total_height: int
):
  anchor, row, col = Anchor.NW, 0, 0

  if align == Align.CENTER:
    row, col = (total_height - height) // 2, (total_width - width) // 2
  elif align == Align.N:
    row, col = 0, (total_width - width) // 2
  elif align == Align.NE:
    anchor, row, col = Anchor.NE, 0, total_width
  elif align == Align.E:
    anchor = Anchor.NE
    row, col = (total_height - height) // 2, total_width
  elif align == Align.SE:
    anchor = Anchor.SE
    row, col = total_height, total_width
  elif align == Align.S:
    anchor = Anchor.SW
    row, col = total_height, (total_width - width) // 2
  elif align == Align.SW:
    anchor = Anchor.SW
    row, col = total_height, 0
  elif align == Align.W:
    row, col = (total_height - height) // 2, 0

  return (anchor, row, col)

class Chat:
  def __init__(self, client):
    self.client = client
    self.display_buffer = None
    self.display_window = None
    self.prompt_window = None
    self.count = 1

  def __prompt_buffer(self):
    buffer = self.client.api.create_buf(False, True)

    buffer.options['bufhidden'] = 'wipe'
    buffer.options['buftype'] = 'prompt'
    buffer.options['swapfile'] = False

    self.client.command(
      f'autocmd InsertLeave <buffer={buffer.number}> call _chat_query()'
    )

    self.client.command(
      f'autocmd BufWinLeave <buffer={buffer.number}> call _chat_closed()'
    )

    return buffer

  def __display_buffer(self):
    buffer = self.client.api.create_buf(False, True)

    buffer.options['bufhidden'] = 'wipe'
    buffer.options['swapfile'] = False

    return buffer

  def display_text(self, text):
    if self.display_buffer:
      self.display_buffer.append(text)

  def close(self, text):
    if self.prompt_window and self.prompt_window.valid:
      self.prompt_window.api.close(True)

    if self.display_window and self.display_window.valid:
      self.display_window.api.close(True)

    self.window = self.display = None

    self.count = 0

  def query(self, bot):
    if not self.prompt_window or not self.prompt_window.valid: return
    self.display_text(['', f'[{self.count}] Querying...', ''])
    self.count += 1
    self.display_text(bot.query(self.prompt_window.buffer[0]).split('\n'))

  def show(self):
    prompt_buffer, display_buffer = self.__prompt_buffer(), self.__display_buffer()

    self.display_buffer = display_buffer

    self.display_window = open_win(
      self.client, display_buffer, height=75, scrollable=True
    )

    self.prompt_window = open_win(
      self.client, prompt_buffer, height=1, align=Align.S
    )

    self.client.funcs.prompt_setprompt(prompt_buffer, '> ')

    self.client.command('startinsert!')

class Editor:
  def __init__(self, client):
    self.client = client
    self.chat = Chat(client)

  def show_chat(self):
    self.chat.show()

  def write(self, message):
    self.client.api.echo([[message, '']], True, {})

class Bot:
  def __init__(self, client):
    self.client = client

  def refresh(self):
    self.client.refresh_session()

  def query(self, message):
    return self.client.get_chat_response(message)['message']

@neovim.plugin
class Plugin:
  def __init__(self, client):
    self.bot = Bot(Chatbot(Config.load().as_dict()))
    self.editor = Editor(client)

  @neovim.function('_chat_query')
  def _chat_query(self, args):
    self.editor.chat.query(self.bot)

  @neovim.function('_chat_closed')
  def _chat_closed(self, args):
    self.editor.chat.close('foo')

  @neovim.command('ChatGPT', nargs='*', sync=True)
  def chat(self, args):
    self.bot.refresh()

    if not args:
      self.editor.show_chat()
    else:
      try:
        self.editor.write(self.bot.query(' '.join(args)))
      except Exception as error:
        self.editor.write(f'error: Failed to get response from ChatGPT')
