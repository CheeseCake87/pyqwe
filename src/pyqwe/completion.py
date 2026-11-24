"""
Shell completion scripts, printed by `pyqwe --completion <shell>`.

The scripts call the hidden `pyqwe --commands` option, which prints one
command per line: the name, then a tab and the help text if there is any.

Options are only completed before the command name, everything after the
command name belongs to the command, so falls back to file completion.
"""

SHELLS = ("bash", "zsh", "fish")

_BASH = r"""

# pyqwe bash completion, add to ~/.bashrc:
#   eval "$(qwe --completion bash)"
_pyqwe_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"
    local IFS=$'\n'
    local i

    if [ "$prev" = "--completion" ]; then
        COMPREPLY=($(compgen -W $'bash\nzsh\nfish' -- "$cur"))
        return
    fi

    # Once the command name is given, leave the rest to file completion
    for ((i = 1; i < COMP_CWORD; i++)); do
        case "${COMP_WORDS[i]}" in
            -*) ;;
            *) return ;;
        esac
    done

    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W $'--help\n--version\n--list\n--dry-run\n--completion' -- "$cur"))
    else
        # bash splits words on ':', use bash-completion's helpers when
        # available so names like 'db:migrate' complete correctly
        if declare -F _get_comp_words_by_ref >/dev/null; then
            _get_comp_words_by_ref -n : cur
        fi
        COMPREPLY=($(compgen -W "$(pyqwe --commands 2>/dev/null | cut -f1)" -- "$cur"))
        if declare -F __ltrim_colon_completions >/dev/null; then
            __ltrim_colon_completions "$cur"
        fi
    fi
}
complete -o default -F _pyqwe_complete pyqwe qwe


"""

_ZSH = r"""

# pyqwe zsh completion, add to ~/.zshrc after compinit:
#   eval "$(qwe --completion zsh)"
_pyqwe_commands() {
    local -a commands
    local line name
    for line in ${(f)"$(pyqwe --commands 2>/dev/null)"}; do
        name=${line%%$'\t'*}
        name=${name//:/\\:}
        if [[ $line == *$'\t'* ]]; then
            commands+=("$name:${line#*$'\t'}")
        else
            commands+=("$name")
        fi
    done
    _describe -t commands 'pyqwe command' commands
}
_pyqwe() {
    _arguments -s -S -A '-*' \
        '(- *)'{-h,--help}'[show the help message]' \
        '(- *)'{-v,--version}'[show the version]' \
        '(- *)'{-l,--list}'[list all commands]' \
        '(-n --dry-run)'{-n,--dry-run}'[show what a command would run, without running it]' \
        '(- *)--completion[print a shell completion script]:shell:(bash zsh fish)' \
        '1:command:_pyqwe_commands' \
        '*::argument:_files'
}
compdef _pyqwe pyqwe qwe


"""

_FISH = r"""

# pyqwe fish completion, add to ~/.config/fish/config.fish:
#   qwe --completion fish | source
function __pyqwe_needs_command
    # True until a command name is given, options don't count
    for token in (commandline -opc)[2..-1]
        switch $token
            case '-*'
            case '*'
                return 1
        end
    end
    return 0
end
for cmd in pyqwe qwe
    complete -c $cmd -n __pyqwe_needs_command -f -a "(pyqwe --commands 2>/dev/null)"
    complete -c $cmd -n __pyqwe_needs_command -s h -l help -d "Show the help message"
    complete -c $cmd -n __pyqwe_needs_command -s v -l version -d "Show the version"
    complete -c $cmd -n __pyqwe_needs_command -s l -l list -d "List all commands"
    complete -c $cmd -n __pyqwe_needs_command -s n -l dry-run -d "Show what a command would run"
    complete -c $cmd -n __pyqwe_needs_command -l completion -x -a "bash zsh fish" -d "Print a shell completion script"
end


"""


def completion_script(shell: str) -> str:
    return {"bash": _BASH, "zsh": _ZSH, "fish": _FISH}[shell]
