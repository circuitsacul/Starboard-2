# Contributing to Starboard-2

If you want to contribute, that's great! Please just follow the guidelines, as they are written here.

## Steps:
1. Fork this repo, and then clone that fork to your computer.
2. Create a virtual env, either with conda or venv. Make sure you are always inside this environment, wheter you're running or installing libs required to run the bot.
3. Run `pip install -r requirements.txt` to install required dependencies for running the bot.
4. Make your changes.
5. If you added any imports, and how to install any files, run `pip freeze > requirements.txt`.
6. Run `isort --recursive .` to format imports. (run this *before* running black)
7. Run `black . -l 79` while in the Starboard-2 directory to auto-format code.
8. Push your changes.
9. Create a pull request from your repo to this repo
