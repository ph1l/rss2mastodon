# rss2mastodon

A quick set of python scripts for auto-posting an RSS or Atom feed to Mastodon. Created by AI6YR (Ben)

## Mastodon setup

In order to have this script work, you need the following:
1. A dedicated Mastodon user account created on a server.
2. An "access key" for your app created for that user account. (under yourserver/settings/applications)

## Python setup

Install the application in a virtual environment to containerize and isolate it's runtime.

    python3 -m venv ~/venvs/rss2mastodon
    ~/venvs/rss2astodon/bin/pip install .

## Script setup

All configuration for the script will ultimately reside in an ini config file. `config.ini` is provided here as an example.


### Mastodon configuration
* access_token = Mastodon access token
* app_url = Mastodon server
* max_image_size = max image size accepted by server

### Feed configuration
* feed_url = URL of the RSS feed you want to query
* feed_name = What you want to name this feed
* feed_visibility = public, unlisted, etc. (per Mastodon.py)
* feed_tags = #your #additional #tags here will be appended to the toot
* feed_delay = delay in seconds between checking on the RSS/Atom feed
* feed_link = whether or not to include the "link" in RSS/Atom in the post

## Running the script

    ~/venvs/rss2astodon/bin/rss2mastodon -c config.ini

## Unattended/background operation

I suggest you run the script as a daemon w/ a systemd user service. Use the
provided template file (`rss2mastodon@.service`.)

On a debian based system you can set this up in a user's homedir, this example
assumes you're using the user `bots`. You'll need to make modifications
otherwise.

as root:

    # loginctl enable-linger bots

as bots:

    $ mkdir -p ~bots/.config/systemd/user ~bots/.config/rss2mastodon
    $ cp src/rss2mastodon/rss2mastodon@.service ~bots/.config/systemd/user/
    $ cp src/rss2mastodon/config.ini ~bots/.config/rss2mastodon/instance_name.ini
    $ systemctl --user enable rss2mastodon@instance_name
    $ systemctl --user start rss2mastodon@instance_name
