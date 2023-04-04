## chatgpt.vim 🤖

**chatgpt.nvim** is a Neovim plugin that lets you query ChatGPT inside a Neovim
buffer.

### Demo

[![asciicast](https://asciinema.org/a/kDqlcFdEH0W3aifrXn06mpoMh.svg)](https://asciinema.org/a/kDqlcFdEH0W3aifrXn06mpoMh)

### Installation

_n.b. You must have [python3](https://www.python.org/downloads/) installed on your machine in order to
install and use this plugin._

You can install this plugin with [packer](https://github.com/wbthomason/packer.nvim)
or any other vim plugin manager:

```lua
use({
  'terror/chatgpt.nvim',
  run = 'pip3 install -r requirements.txt'
})
```

### Configuration

The plugin looks for a configuration file in your home directory called
`.chatgpt-nvim.json`, and it expects a valid OpenAI api key to be set for
queries to work:

```
{ 'api_key': '<API-KEY>' }
```

You can get an api key from OpenAI via their [website](https://platform.openai.com/account/api-keys).

### Commands

Below are the available commands this plugin supports:

| Name    | Arguments | Description                                                        |
| ------- | --------- | ------------------------------------------------------------------ |
| ChatGPT |           | Open a new interactive ChatGPT environment                         |
| ChatGPT | \[query\] | Load a ChatGPT response to `query` into the Neovim command prompt. |
