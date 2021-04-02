# Contributing to Starboard-2

If you want to contribute, that's great! Please just follow the guidelines, as they are written here.

## Code Contributions:
1. Fork this repo, and then clone that fork to your computer.
2. Create a virtual env, either with conda or venv. Make sure you are always inside this environment, wether you're running or installing libs
3. Run `pip install -r requirements.txt` to install required dependencies for running the bot.
4. Run `pre-commit install`. If you don't do this, `black` and `isort` will not run automatically.
5. Make your changes, then push. `black` will automatically format the code.
6. Create a pull request from your repo to this repo
