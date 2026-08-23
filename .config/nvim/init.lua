-- Базовые настройки
vim.opt.number = true          -- номера строк
vim.opt.tabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true

-- Подсветка синтаксиса встроенная
vim.cmd('syntax on')

-- Подключаем lazy.nvim
vim.opt.rtp:prepend("~/.local/share/nvim/lazy/lazy.nvim")

require("lazy").setup({
  -- Нормальная подсветка синтаксиса
  { "nvim-treesitter/nvim-treesitter", build = ":TSUpdate" },
})
