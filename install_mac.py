import logging
import os
import platform
import shutil
import sys
from pathlib import Path

import click
import coloredlogs
import inquirer
from plumbum import local, ProcessExecutionError

coloredlogs.install(level=logging.DEBUG)

DEV_PATH = Path('~/dev').expanduser()

brew = local['brew']
python3 = local[sys.executable]
sudo = local['sudo']
defaults = local['defaults']
killall = local['killall']
git = local['git']
cp = local['cp']
chsh = local['chsh']

logger = logging.getLogger(__name__)


def git_clone(repo_url: str, branch='master'):
    try:
        git('clone', '--recurse-submodules', '-b', branch, repo_url)
    except ProcessExecutionError as e:
        if 'already exists and is not an empty directory' not in e.stderr:
            raise
        cwd = os.getcwd()
        os.chdir(repo_url.rsplit('/', 1)[1].rsplit('.git', 1)[0])
        try:
            git('pull', 'origin', branch)
        except ProcessExecutionError as e:
            if ('Please commit your' not in e.stderr) and ('You have unstaged' not in e.stderr) and (
                    'Need to specify' not in e.stderr):
                raise
            logger.warning(f'failed to pull {repo_url}')
        os.chdir(cwd)


def configure_preferences():
    logger.info('configuring preferences')

    # enable execution from everywhere without the annoying "open anyway" from preferences
    sudo('spctl', '--master-disable')

    # -- Finder
    defaults('write', 'NSGlobalDomain', 'AppleShowAllExtensions', '-bool', 'true')
    defaults('write', 'com.apple.finder', 'ShowPathbar', '-bool', 'true')
    defaults('write', 'com.apple.finder', 'FXPreferredViewStyle', '-string', '-Nlsv')

    # -- Keyboard (applied only after logout and login)
    defaults('write', '-g', 'InitialKeyRepeat', '-int', '12')  # normal minimum is 15 (225 ms)
    defaults('write', '-g', 'KeyRepeat', '-int', '12')  # normal minimum is 2 (30 ms)
    defaults('write', '-g', 'ApplePressAndHoldEnabled', '-bool', 'false')  # normal minimum is 15 (225 ms)

    killall('Finder')


def install_brew_packages():
    logger.info('installing brew packages')

    brew_list = brew('list')

    packages = ['git', 'git-lfs', 'cmake', 'openssl@3', 'libffi', 'defaultbrowser', 'bat', 'fzf', 'wget', 'htop',
                'ncdu', 'watch', 'bash-completion', 'ripgrep', 'python-tk@3.9', 'python-tk@3.11', 'node', 'drawio',
                'jq']

    for p in packages:
        if p not in brew_list.split('\n'):
            brew('reinstall', p, '--force')

    git('lfs', 'install')
    sudo('git', 'lfs', 'install', '--system')

    casks = {
        'iTerm.app': 'iterm2',
        'Sublime Text.app': 'sublime-text',
        'DB Browser for SQLite.app': 'db-browser-for-sqlite',
        'Google Chrome.app': 'google-chrome',
        'Wireshark.app': 'wireshark',
        'PyCharm CE.app': 'pycharm-ce',
        'Visual Studio Code.app': 'visual-studio-code',
        'Rectangle.app': 'rectangle',
        'Discord.app': 'discord',
        'Flycut.app': 'flycut',
    }

    for app, cask in casks.items():
        if cask in brew_list.split('\n'):
            # skip already installed through brew
            continue

        if not (Path('/Applications') / app).exists() or inquirer.confirm(
                f'{app} is already installed. would you like to install latest from brew instead?', default=False):
            logger.info(f'installing {app}')

            try:
                brew('uninstall', cask)
            except ProcessExecutionError as e:
                if 'is not installed' not in e.stderr:
                    raise

            brew('install', '--cask', cask, '--force')

    logger.info('installing blacktop\'s ipsw')
    brew('install', 'blacktop/tap/ipsw')

    logger.info('setting default browser to google chrome')
    local['defaultbrowser']('chrome')


def install_python_packages():
    logger.info('installing python packages')

    python3('-m', 'pip', 'install', '-U', 'pip')

    python3('-m', 'pip', 'install', '-U', 'xonsh', 'pyfzf', 'artifactory', 'humanfriendly', 'pygments', 'ipython',
            'plumbum', 'xontrib-argcomplete', 'xontrib-fzf-widgets', 'xontrib-z', 'xontrib-up', 'pymobiledevice3',
            'harlogger', 'cfprefsmon', 'pychangelog2')


def install_xonsh():
    logger.info('installing xonsh')

    xonsh_path = shutil.which('xonsh')
    if xonsh_path not in open('/etc/shells', 'r').read():
        sudo('sh', '-c', f'echo {xonsh_path} >> /etc/shells')

    brew('reinstall', 'fzf')
    brew('reinstall', 'bash-completion')

    DEV_PATH.mkdir(parents=True, exist_ok=True)

    os.chdir(DEV_PATH)
    git_clone('git@github.com:doronz88/worksetup.git', 'main')
    cp('worksetup/.xonshrc', Path('~/').expanduser())
    chsh('-s', xonsh_path)


@click.group()
def cli():
    pass


@cli.command('configure-preferences')
def cli_configure_preferences():
    configure_preferences()


@cli.command('brew-packages')
def cli_brew_packages():
    install_brew_packages()


@cli.command('python-packages')
def cli_python_packages():
    install_python_packages()


@cli.command('xonsh')
def cli_xonsh():
    install_python_packages()
    install_xonsh()


@cli.command('everything')
def cli_everything():
    configure_preferences()
    install_brew_packages()
    install_python_packages()
    install_xonsh()


if __name__ == '__main__':
    cli()
