# `wtgo <branch>` — go to a branch's dev session, creating whatever is missing
# (worktree, tmux session, even the branch). Same engine as `make go`; the
# function exists so bash can tab-complete branch names, which make cannot do
# for variable values.
#
# Install once:  echo 'source ~/code/resslab-hub/scripts/wt-go.bash' >> ~/.bashrc
# Then:          wtgo feat/<TAB>     lists worktrees and branches starting feat/
_WTGO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

wtgo() { "$_WTGO_ROOT/scripts/wt-new.sh" "$@"; }

_wtgo() {
  local cur=${COMP_WORDS[COMP_CWORD]}
  local refs
  refs=$( { git -C "$_WTGO_ROOT" worktree list --porcelain | sed -n 's#^branch refs/heads/##p'
            git -C "$_WTGO_ROOT" for-each-ref --format='%(refname:short)' refs/heads refs/remotes/origin |
              sed 's#^origin/##'; } 2>/dev/null | grep -Ev '^(HEAD|origin)$' | sort -u )
  COMPREPLY=( $(compgen -W "$refs" -- "$cur") )
}
complete -F _wtgo wtgo
