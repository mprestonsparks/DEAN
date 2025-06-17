#!/bin/bash
# Bash completion script for the dean CLI
# 
# Installation:
#   1. Source this file in your .bashrc or .bash_profile:
#      source /path/to/dean-completion.bash
#   2. Or copy to system completion directory:
#      sudo cp dean-completion.bash /etc/bash_completion.d/dean

_dean_completion() {
    local cur prev words cword
    _init_completion || return

    local commands="deploy status interactive evolution config --help --version"
    local evolution_commands="start list --help"
    local config_commands="show set --help"

    # Main command completion
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
        return 0
    fi

    # Subcommand completion
    case "${words[1]}" in
        evolution)
            if [[ $cword -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "$evolution_commands" -- "$cur") )
            fi
            ;;
        config)
            if [[ $cword -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "$config_commands" -- "$cur") )
            fi
            ;;
        deploy)
            COMPREPLY=( $(compgen -W "--check-only --help" -- "$cur") )
            ;;
        *)
            ;;
    esac

    return 0
}

complete -F _dean_completion dean