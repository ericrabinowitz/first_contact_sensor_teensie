
" be iMproved
set nocompatible
filetype off
" Vundle stuff
set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()
" let Vundle manage Vundle, required
Plugin 'VundleVim/Vundle.vim'
" My bundles here: (install with :PluginInstall)
"
"original repos on GitHub
Plugin 'scrooloose/nerdtree'
Plugin 'scrooloose/syntastic'
" vim-scripts repos
Plugin 'indentpython.vim'
Plugin 'nvie/vim-flake8'
Plugin 'pep8'
" non-GitHub repos
" Git repos on your local machine (i.e. when working on your own plugin)
filetype plugin indent on
syntax on
" Highlighted search
:set hlsearch
" Press Space to turn off highlighting and clear any message already displayed.
:nnoremap :nohlsearch:echo
" Numbered lines
:set nu
" Enable mouse scrolling
set mouse=a
map <ScrollWheelUp> <C-Y>
map <ScrollWheelDown> <C-E>
" Enable paste mode with F2
set pastetoggle=
" Reload vimrc with F3
:map :so $MYVIMRC
" Reload vimrc on write
augroup myvimrc
au!
autocmd bufwritepost .vimrc source ~/.vimrc
augroup END
" Easier buffer switching
:nnoremap :buffers:buffer
" Indentation
set shiftwidth=4
set tabstop=4
set expandtab
" Pep8
let g:pep8_map=''
" save session
:map :mksession! ~/env_files/.mysession.vim
" reload session
:map :so ~/env_files/.mysession.vim
"Remap the semicolon
map ; :
" Set swap file location
:set dir=~/backup/swap
:set ruler
function! CopyMatches(reg)
let hits = []
%s//=len(add(hits, submatch(0))) ? submatch(0) : ''/ge
let reg = empty(a:reg) ? '+' : a:reg
execute 'let @'.reg.' = join(hits, "\n") . "\n"'
endfunction
command! -register CopyMatches call CopyMatches()
" Move current tab into the specified direction.
"
" @param direction -1 for left, 1 for right.
function! TabMove(direction)
" get number of tab pages.
let ntp=tabpagenr("$")
" move tab, if necessary.
if ntp > 1
" get number of current tab page.
let ctpn=tabpagenr()
" move left.
if a:direction < 0
let index=((ctpn-1+ntp-1)%ntp)
else
let index=(ctpn%ntp)
endif
    " move tab page.
    execute "tabmove ".index
endif
endfunction
map :call TabMove(-1)
map :call TabMove(1)
function! CopyMatches(reg)
let hits = []
%s//=len(add(hits, submatch(0))) ? submatch(0) : ''/ge
let reg = empty(a:reg) ? '+' : a:reg
execute 'let @'.reg.' = join(hits, "\n") . "\n"'
endfunction
command! -register CopyMatches call CopyMatches()
