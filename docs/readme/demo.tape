# Terminal demo shown in README.md, recorded with VHS (https://github.com/charmbracelet/vhs).
# Re-record from the repository root after a CLI change:  vhs docs/readme/demo.tape
# Shows the help and the topic menu only. It never drafts a post: that calls a provider
# API with a key. QC_POST_DATA_DIR and QC_POST_ENV_FILE point at a throwaway folder,
# so ~/QuestCast and ~/.qc_post_env are never read. Needs uv sync run once in the clone.

Output docs/readme/demo.gif

Require uv

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 500
Set Padding 24
Set TypingSpeed 40ms
Set Theme { "name": "Bearing Quest Night", "background": "#10213A", "foreground": "#F4F6F8", "cursor": "#E8894F", "selection": "#2E4A72", "black": "#10213A", "red": "#FF8A80", "green": "#8FD19E", "yellow": "#F2C46B", "blue": "#7DB8F0", "magenta": "#E3A1D6", "cyan": "#7FD6E8", "white": "#C9D3DF", "brightBlack": "#8EA0B5", "brightRed": "#FFB4AB", "brightGreen": "#B5E3C0", "brightYellow": "#F7D99A", "brightBlue": "#A9D0F5", "brightMagenta": "#EFC4E8", "brightCyan": "#A8E6F2", "brightWhite": "#FFFFFF" }

Hide
Type `export PS1='$ ' && VIRTUAL_ENV_DISABLE_PROMPT=1 source .venv/bin/activate && export QC_POST_DATA_DIR="$(mktemp -d)" && export QC_POST_ENV_FILE="$QC_POST_DATA_DIR/no-env-file" && printf '## Topics\n\n- Supply-chain security for open-source packages\n- Guardrails for AI coding agents\n- Cloud cost controls\n\n## Beat\n\nDemo profile with made-up content.\n\n## Voice\n\nDemo profile with made-up content.\n' > "$QC_POST_DATA_DIR/author_profile.md" && clear`
Enter
Sleep 2s
Show

Type `qc --help | head -n 14`
Sleep 300ms
Enter
Sleep 4s

Type `qc --list-topics`
Sleep 300ms
Enter
Sleep 3.5s
