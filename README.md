## Start with a clean slate

Cider is a simple wrapper for [Homebrew](http://brew.sh) and [Homebrew Cask](http://caskroom.io) that allows you to save your setup across different machines. This lets you to restore a backup without having to deal with the mess that was the state of your previous installation, or painstakingly babysit the process step-by-step.

Simply run the following on a new machine:

    git clone [YOUR_REPO] ~/.cider
    cider restore


... and you'll be back up and running, with all of your applications and command line utilities re-installed (and configurations restored).


In addition to Homebrew, Cider also supports managing your user defaults, restoring symlinks, and running scripts to conveniently manage other settings such as your dotfiles.


## Installation

Cider is available directly from [PyPI](https://pypi.python.org/pypi/cider):

    pip install -U cider


## Configuration

All configuration files are stored in the `~/.cider` directory as JSON. For instance, here's an example bootstrap file:

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
		"icons": {
			"iTerm": "https://dribbble.com/shots/1702947-iTerm-Replacement-Icon/attachments/271548"
		},
		"symlinks": {
			"bash/.*": "~",
			"bin/*": "~/bin/",
			"git/.*": "~",
			"sh/.*": "~",
			"vim/.*": "~"
		},
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

Cider also supports YAML if you'd like to add comments to either of these. To see how this works out in practice, feel free to take a look at [my dotfiles](https://github.com/msanders/dotfiles).

## Backup your existing setup

To save the state of your existing setup:

    cider missing
    cider tap missing
    cider cask missing

## Manage symlinks

Cider supports the following commands to manage symlinks (inspired in part by [GNU Stow](http://brandon.invergo.net/news/2012-05-26-using-gnu-stow-to-manage-your-dotfiles.html)).

    cider addlink NAME ITEM...
    cider relink # (invoked automatically by restore)

For example, `cider addlink git ~/.gitconfig` will move `~/.gitconfig` to `~/.cider/symlinks/git/`, create a link back to its original location, and add an entry to your bootstrap denoting this:

    "symlinks": {
        "git/.*": "~"
    }

To undo this change, simply run `cider unlink git`.

Directories in targets are automatically expanded, so the entry `"bin/*": "~/bin/"` will first create the directory `~/bin/` if it doesn't exist already, and then link all items in `symlinks/bin/*` to children of that directory.

## Caveats

There doesn't seem to be a way to re-install purchases made from Mac App Store via the command line just yet, so those have to be done by hand.

**Note**: Cider is a work-in-progress, but it's well-tested and should be kind to your machine.
