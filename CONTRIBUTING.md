# Contributing to Starboard-2

If you want to contribute, that's great! Please just follow the guidelines, as they are written here.

## Code Contributions:
1. Fork this repo, and then clone that fork to your computer.
2. Create a virtual env, either with conda or venv. Make sure you are always inside this environment, wether you're running or installing libs
3. Run `pip install -r requirements.txt` to install required dependencies for running the bot.
4. Run `pre-commit install`. If you don't do this, `black` and `isort` will not run automatically.
5. Make your changes, then push. `black` will automatically format the code.
6. Create a pull request from your repo to this repo

## Adding/Updating Translations:
Translation files are found in `app/locale/<locale name>/LC_MESSAGES/bot.po`. They are formated like this:
```
msgid "Original Message"
msgstr "Translated Message"
```

If you see any missing or incorrect translations, you can follow the instructions below.

### Method 1:
1. Create a fork of Starboard-2.
2. Edit the files that need editing.
3. Create a PR (pull request) to have the changes merged.

### Method 2:
1. Go to the file that needs editing (on this GitHub repo) and click "Raw".
2. Download the contents of the page (or copy+paste them into a text editor).
3. Edit the file as needed.
4. Send me a copy of the edited file over discord (`Circuit#5585`). You'll need to [join the server](https://discord.gg/3gK8mSA), as I ignore friend request for those I don't know.
