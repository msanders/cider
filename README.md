## Start with a clean slate

Cider is a simple wrapper for [Homebrew](http://brew.sh) and [Homebrew Cask](http://caskroom.io) that allows you to save your setup across different machines. This lets you to restore a backup without having to deal with the mess that was the state of your previous installation, or painstakingly babysit the process step-by-step.

Simply run the following on a new machine:

    git clone [YOUR_DOTFILES] ~/.cider
    cider restore


... and you’ll be back up and running, with all of your applications and command line utilities re-installed (and config files restored).


## Installation

Cider is available directly from [PyPI](https://pypi.python.org/pypi/cider):

    pip install cider


## Configuration

All configuration files are stored in the `~/.cider` directory as JSON. E.g., here's an example bootstrap file:

    {
        "after-scripts": [
            "brew linkapps"
        ],
        "casks": [
            "adobe-creative-cloud",
            "dropbox",
            "firefox",
            "flash",
            "flux",
            "github",
            "google-chrome",
            "google-hangouts",
            "heroku-toolbelt",
            "iterm2",
            "mplayerx",
            "sublime-text",
            "transmission",
        ],
        "formulas": [
            "brew-cask",
            "emacs",
            "fish",
            "git",
            "go",
            "macvim --overwrite-system-vi",
            "python",
            "python3",
            "xctool"
        ],
        "taps": [
            "caskroom/cask"
        ]
    }

User defaults are stored similarly:

    {
        "NSGlobalDomain": {
            "ApplePressAndHoldEnabled": false
        }, 
        "com.apple.dock": {
            "tilesize": 48
        }, 
        "com.iconfactor.mac.xScope": {
            "generalShowDockIcon": false
        }
    }

## Caveats

There doesn't seem to be a way to re-install purchases made from Mac App Store via the command line just yet, so those have to be done by hand.

**Note**: Cider is a work-in-progress, don't use it for anything important yet!
