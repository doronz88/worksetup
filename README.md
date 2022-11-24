# Overview

Setup script for quickly setting up macOS installations for a more efficient work computer.

# Perquisites

Install Homebrew:

```shell
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install `python3.11` & `git`:

```shell
brew install python@3.11 git
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
python3.11 -m install_mac.py everything
```