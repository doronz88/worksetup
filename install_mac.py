import logging
import os
import shutil
import sys
from functools import partial
from pathlib import Path
from typing import Callable, List

import click
import coloredlogs
import inquirer3
import requests
from plumbum import ProcessExecutionError, local
from plumbum.commands.base import BoundCommand

coloredlogs.install(level=logging.DEBUG)

DEV_PATH = Path('~/dev').expanduser()
VSCODE_EXTENSION_IDS = [
    'atommaterial.a-file-icon-vscode', 'ms-python.autopep8', 'ms-vscode.cpptools-extension-pack', 'ms-vscode.cpptools-themes',
    'llvm-vs-code-extensions.vscode-clangd', 'ms-vscode.cmake-tools', 'qingpeng.common-lisp', 'github.vscode-github-actions',
    'eamodio.gitlens', 'ms-python.isort', 'mattn.Lisp', 'zhuangtongfa.material-theme', 'ms-python.vscode-pylance',
    'ms-python.python', 'ms-python.python', 'infosec-intern.yara']
VSCODE_SETTINGS_FILE = Path('~/Library/Application Support/Code/User/settings.json').expanduser()

VSCODE_DEFAULT_SETTINGS = """
{
    "editor.cursorBlinking": "smooth",
    "security.workspace.trust.untrustedFiles": "open",
    "git.openRepositoryInParentFolders": "always",
    "files.associations": {
        "*.sb": "commonlisp"
    },
    "cmake.configureOnOpen": true,
    "python.analysis.autoFormatStrings": true,
    "python.analysis.autoImportCompletions": true,
    "python.analysis.diagnosticSeverityOverrides": {
    },
    "python.analysis.inlayHints.functionReturnTypes": true,
    "python.analysis.inlayHints.pytestParameters": true,
    "python.analysis.inlayHints.variableTypes": true,
    "python.analysis.typeCheckingMode": "basic",
    "workbench.colorTheme": "One Dark Pro Darker",
    "autopep8.args": [
        "--max-line-length",
        "127",
        "--experimental"
    ],
    "autopep8.showNotifications": "always",
    "window.zoomLevel": 1,
    "workbench.iconTheme": "a-file-icon-vscode"

}
"""

brew = local['brew']
python3 = local[sys.executable]
sudo = local['sudo']
defaults = local['defaults']
killall = local['killall']
git = local['git']
cp = local['cp']
chsh = local['chsh']
sh = local['sh']

logger = logging.getLogger(__name__)

AUTOMATION_MODE = False


def confirm_install(component: str, installer: Callable):
    if AUTOMATION_MODE or inquirer3.confirm(f'To {component}?', default=False):
        installer()


def insert_number_install(message: str, installer: BoundCommand, default_number: int):
    installer[default_number if AUTOMATION_MODE else inquirer3.text(message, default=str(default_number))]()


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

    confirm_install(
        'disable master system policy (this would enable execution from everywhere without "open anyway" prompt',
        sudo['spctl', '--master-disable'])

    confirm_install('disable Library Validation',
                    sudo['defaults', 'write', '/Library/Preferences/com.apple.security.libraryvalidation.plist',
                         'DisableLibraryValidation', '-bool', 'true'])

    # -- Finder
    confirm_install('show every file extension',
                    defaults['write', 'NSGlobalDomain', 'AppleShowAllExtensions', '-bool', 'true'])
    confirm_install('show path bar on finder', defaults['write', 'com.apple.finder', 'ShowPathbar', '-bool', 'true'])
    confirm_install('set finder to details view',
                    defaults['write', 'com.apple.finder', 'FXPreferredViewStyle', '-string', '-Nlsv'])

    # -- Keyboard (applied only after logout and login)
    confirm_install('change delay until key repeat',
                    partial(insert_number_install, 'How much delay? mac normal is between 15 (225ms) to 120 (1.8s)',
                            defaults['write', '-g', 'InitialKeyRepeat', '-int'], 12))
    confirm_install('change key repeat rate',
                    partial(insert_number_install, 'How much delay? mac normal is between 2 (30ms) to 120 (1.8s)',
                            defaults['write', '-g', 'KeyRepeat', '-int'], 2))
    confirm_install('disable accent menu when holding key',
                    defaults['write', '-g', 'ApplePressAndHoldEnabled', '-bool', 'false'])

    killall('Finder')


def install_brew_packages(disable: List[str]):
    logger.info('installing brew packages')

    brew_list = brew('list').split('\n')

    packages = ['git', 'git-lfs', 'cmake', 'openssl@3', 'libffi', 'defaultbrowser', 'bat', 'fzf', 'wget', 'htop',
                'ncdu', 'watch', 'bash-completion', 'ripgrep', 'python-tk@3.9', 'python-tk@3.11', 'node', 'drawio',
                'jq', 'difftastic']

    for p in disable:
        if p in packages:
            logger.info(f'skipping {p}')
            packages.remove(p)

    for p in packages:
        if p in disable:
            logger.info(f'skipping {p}')
            continue

        if p not in brew_list:
            confirm_install(f'install {p}', brew['install', p, '--force'])

    if 'git-lfs' not in brew_list and 'git-lfs' in brew('list').split('\n'):
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
        'Raycast.app': 'raycast',
        'AltTab.app': 'alt-tab',
    }

    for app, cask in casks.items():
        if cask in disable:
            logger.info(f'skipping {cask}')
            continue

        if cask in brew_list:
            # skip already installed through brew
            continue

        if not (Path('/Applications') / app).exists():
            confirm_install(f'install {cask}', brew['install', '--cask', cask, '--force'])
        # Specific confirmation that included in automation mode
        elif inquirer3.confirm(
                f'{app} is already installed, but not through brew. would you like to install from brew instead?',
                default=False):
            try:
                brew('uninstall', cask)
            except ProcessExecutionError as e:
                if 'is not installed' not in e.stderr:
                    raise

            brew('install', '--cask', cask, '--force')

    confirm_install('install ipsw', brew['install', 'blacktop/tap/ipsw'])

    if 'google-chrome' not in brew_list and 'defaultbrowser' in brew_list:
        brew_list = brew('list').split('\n')
        if 'google-chrome' in brew_list:
            confirm_install('set google chrome to be your default browser', local['defaultbrowser']['chrome'])


def install_python_packages():
    logger.info('installing python packages')

    confirm_install('upgrade pip', python3['-m', 'pip', 'install', '-U', 'pip'])

    python_packages = ['xattr', 'pyfzf', 'artifactory', 'humanfriendly', 'pygments', 'ipython', 'plumbum',
                       'pymobiledevice3', 'harlogger', 'cfprefsmon', 'pychangelog2']

    for package in python_packages:
        confirm_install(f'install {package}', python3['-m', 'pip', 'install', '-U', package])


def install_ohmyzsh() -> None:
    logger.info('installing ohmyzsh')
    try:
        confirm_install('install ohmyzsh',
                        sh['-c', requests.get(
                            'https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh').text])
    except ProcessExecutionError as e:
        if 'The $ZSH folder already exists' not in e.stdout:
            raise


def install_xonsh():
    logger.info('installing xonsh')

    confirm_install('upgrade pip', python3['-m', 'pip', 'install', '-U', 'pip'])

    python3('-m', 'pip', 'install', '-U', 'xonsh')

    confirm_install('install xonsh attributes', python3['-m', 'pip', 'install', '-U', 'xontrib-argcomplete',
                    'xontrib-fzf-widgets', 'xontrib-z', 'xontrib-up', 'xontrib-vox', 'xontrib-jedi'])

    xonsh_path = shutil.which('xonsh')
    if xonsh_path not in open('/etc/shells', 'r').read():
        sudo('sh', '-c', f'echo {xonsh_path} >> /etc/shells')

    confirm_install('install/reinstall fzf', brew['reinstall', 'fzf'])
    confirm_install('install/reinstall bash-completion', brew['reinstall', 'bash-completion'])

    confirm_install('set xonsh to be the default shell', chsh['-s', xonsh_path])

    def set_xonshrc():
        DEV_PATH.mkdir(parents=True, exist_ok=True)

        os.chdir(DEV_PATH)
        git_clone('git@github.com:doronz88/worksetup.git', 'main')
        cp('worksetup/.xonshrc', Path('~/').expanduser())

    confirm_install('set ready-made .xonshrc file', set_xonshrc)


def overwrite_vscode_settings_file() -> None:
    VSCODE_SETTINGS_FILE.write_text(VSCODE_DEFAULT_SETTINGS)


def configure_vscode() -> None:
    logger.info('configuring vscode')
    for ext_id in VSCODE_EXTENSION_IDS:
        local['code']('--install-extension', ext_id)

    confirm_install('overwrite vscode settings file', overwrite_vscode_settings_file)


def set_automation(ctx, param, value):
    if value:
        global AUTOMATION_MODE
        AUTOMATION_MODE = True


class BaseCommand(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params[:0] = [
            click.Option(('-a', '--automated'), is_flag=True, callback=set_automation, expose_value=False,
                         help='do everything without prompting (unless certain removals are required)')]


@click.group()
def cli():
    """ Automate selected installs """
    pass


@cli.command('configure-preferences', cls=BaseCommand)
def cli_configure_preferences():
    """ Configure several preferences """
    configure_preferences()


@cli.command('brew-packages', cls=BaseCommand)
@click.option('-d', '--disable', multiple=True)
def cli_brew_packages(disable: List[str]):
    """ Install selected brew packages """
    install_brew_packages(disable)


@cli.command('python-packages', cls=BaseCommand)
def cli_python_packages():
    """ Install selected python packages """
    install_python_packages()


@cli.command('ohmyzsh', cls=BaseCommand)
def cli_ohmyzsh():
    """ Install ohmyzsh """
    install_ohmyzsh()


@cli.command('xonsh', cls=BaseCommand)
def cli_xonsh():
    """ Install xonsh """
    install_xonsh()


@cli.command('configure-vscode', cls=BaseCommand)
def cli_configure_vscode():
    """ Configure vscode """
    configure_vscode()


@cli.command('everything', cls=BaseCommand)
@click.option('-d', '--disable', multiple=True)
def cli_everything(disable: List[str]):
    """ Install everything """
    configure_preferences()
    install_brew_packages(disable)
    configure_vscode()
    install_python_packages()
    install_ohmyzsh()
    install_xonsh()


if __name__ == '__main__':
    cli()
