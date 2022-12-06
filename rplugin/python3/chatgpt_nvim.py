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

CHAT_GPT = r'''
      ___           ___           ___           ___           ___           ___           ___
     /\  \         /\__\         /\  \         /\  \         /\  \         /\  \         /\  \
    /::\  \       /:/  /        /::\  \        \:\  \       /::\  \       /::\  \        \:\  \
   /:/\:\  \     /:/__/        /:/\:\  \        \:\  \     /:/\:\  \     /:/\:\  \        \:\  \
  /:/  \:\  \   /::\  \ ___   /::\~\:\  \       /::\  \   /:/  \:\  \   /::\~\:\  \       /::\  \
 /:/__/ \:\__\ /:/\:\  /\__\ /:/\:\ \:\__\     /:/\:\__\ /:/__/_\:\__\ /:/\:\ \:\__\     /:/\:\__\
 \:\  \  \/__/ \/__\:\/:/  / \/__\:\/:/  /    /:/  \/__/ \:\  /\ \/__/ \/__\:\/:/  /    /:/  \/__/
  \:\  \            \::/  /       \::/  /    /:/  /       \:\ \:\__\        \::/  /    /:/  /
   \:\  \           /:/  /        /:/  /     \/__/         \:\/:/  /         \/__/     \/__/
    \:\__\         /:/  /        /:/  /                     \::/  /
     \/__/         \/__/         \/__/                       \/__/
'''

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

# Alot of the window math stuff was adapted
# from here: https://github.com/stevearc/gkeep.nvim
class WindowManager:
  def __init__(self, client):
    self.client = client

  def open(
    self,
    buffer,
    align=Align.CENTER,
    anchor=Anchor.NW,
    border="rounded",
    col: int = 0,
    enter=True,
    height=0.9,
    relative="editor",
    row: int = 0,
    scrollable=False,
    width=0.9,
    win=None,
  ):
    width, height, total_width, total_height = self.__dimensions(
        width, height, relative, win
    )

    if align is not None:
      if relative == "cursor":
        raise Exception("Align requires relative = win/editor")
      anchor, row, col = self.__alignment(
          align, width, height, total_width, total_height
      )

    window = self.client.api.open_win(
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

  def __alignment(
    self,
    align: Align,
    width: int,
    height: int,
    total_width: int,
    total_height: int
  ):
    anchor, row, col = Anchor.NW, 0, 0

    if align == Align.CENTER:
      row, col = (total_height - height) // 2, (total_width - width) // 2
    elif align == Align.N:
      row, col = 0, (total_width - width) // 2
    elif align == Align.NE:
      anchor, row, col = Anchor.NE, 0, total_width
    elif align == Align.E:
      anchor, row, col = Anchor.NE, (total_height - height) // 2, total_width
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

  def __dimensions(self, width, height, relative, win):
    total_width, total_height = self.__parent_dimensions(relative, win)

    if isinstance(width, float):
      width = int(round(width * (total_width - 2)))

    if isinstance(height, float):
      height = int(round(height * (total_height - 2)))

    return width, height, total_width, total_height

  def __parent_dimensions(self, relative, win):
    if relative == "editor":
      total_width = self.client.options["columns"]
      total_height = self.client.options["lines"] - self.client.options[
        "cmdheight"]
    else:
      if win is None: win = self.client.current.window
      total_width, total_height = win.width, win.height

    return (total_width, total_height)

class Chat:
  def __init__(self, client):
    self.client = client
    self.display_window = None
    self.prompt_window = None
    self.window_manager = WindowManager(client)

  def write(self, text):
    if self.display_window:
      self.display_window.buffer.append(text)

  def show(self):
    prompt_buffer, display_buffer = self.__prompt_buffer(), self.__display_buffer()

    self.display_window = self.window_manager.open(
      display_buffer,
      border='shadow',
      enter=False,
      height=80,
      relative='editor',
      scrollable=True,
    )

    self.prompt_window = self.window_manager.open(
      prompt_buffer,
      align=Align.S,
      border='shadow',
      enter=True,
      height=1,
      relative='editor'
    )

    self.display_window.buffer.append(CHAT_GPT.split('\n'))

    self.client.funcs.prompt_setcallback(prompt_buffer, "_chat_closed")
    self.client.funcs.prompt_setinterrupt(prompt_buffer, "_chat_closed")
    self.client.funcs.prompt_setprompt(prompt_buffer, '> ')

    self.client.command('startinsert!')

  def query(self, bot):
    if not self.prompt_window or not self.prompt_window.valid:
      return

    text = self.prompt_window.buffer[0]

    self.write([f'{text}', ''])

    try:
      self.write(
        list(
          map(
            lambda x: str(x),
            bot.query(self.prompt_window.buffer[0]).split('\n')
          )
        ) + ['']
      )
    except:
      self.write([f'error: Failed to get response from ChatGPT', ''])

  def close(self):
    if self.prompt_window and self.prompt_window.valid:
      self.prompt_window.api.close(True)

    if self.display_window and self.display_window.valid:
      self.display_window.api.close(True)

    self.prompt_window = self.display = None

  def __prompt_buffer(self):
    buffer = self.client.api.create_buf(False, True)

    buffer.options['bufhidden'] = 'wipe'
    buffer.options['buftype'] = 'prompt'
    buffer.options['swapfile'] = False

    self.client.command(
      f'autocmd InsertLeave <buffer={buffer.number}> call _chat_query()'
    )

    return buffer

  def __display_buffer(self):
    buffer = self.client.api.create_buf(False, True)

    buffer.options['bufhidden'] = 'wipe'
    buffer.options['swapfile'] = False

    return buffer

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
    self.editor.chat.close()

  @neovim.command(
    'ChatGPT',
    nargs='*',
  )
  def chat(self, args):
    self.bot.refresh()

    if not args:
      self.editor.show_chat()
    else:
      try:
        self.editor.write(self.bot.query(' '.join(args)))
      except:
        self.editor.write('error: Failed to get response from ChatGPT')
