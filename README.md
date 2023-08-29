# Overview

Setup script for quickly setting up macOS installations for a more efficient work computer.

<details>
<summary>Show what installation includes</summary>

- git
- git-lfs
- python3.9 & tk
- python3.11 & tk
- jq
- ipsw
- cmake
- ripgrep
- libffi
- defaultbrowser
- bat
- fzf
- xonsh
- wget
- htop
- ncdu
- watch
- bash-completion
- node
- drawio
- dockutil
- iTerm
- PyCharm CE
- Visual Studio Code
- Sublime Text
- DB Browser for SQLite
- Google Chrome
- Wireshark
- Rectangle
- Discord
- Flycut
- RayCast
- Alt-Tab

</details>

# Perquisites

Install Homebrew:

```shell
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install `python3.11`:

```shell
brew install python@3.11
```

Make sure to have an SSH keypair:

```shell
ssh-keygen
```

Prepare setup:

```shell
mkdir ~/dev
cd ~/dev
git clone git@github.com:doronz88/worksetup.git
cd worksetup
python3.11 -m pip install -r requirements.txt
```

# Usage

```shell
# pass -a/--automated for doing everything without prompting (unless certain removals are required)
python3.11 install_mac.py everything
```