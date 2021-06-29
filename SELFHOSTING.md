# Self Hosting
## Steps (required)
1.  Clone the repo by running `git clone https://github.com/CircuitsBots/Starboard-2.git`
2.  Create a virtual environment (with conda or venv) and then run `pip install -r requirements.txt`
3.  Go to the discord developer portal and create a new bot application (don't forget to add a bot user)
4.  Create a PostgreSQL user with a password.
5.  Create a new database owned by the user you created.
6.  Make sure gettext is installed with `apt-get install gettext`.
7.  Create copies of `.env.example` and `.config.py.example` and name them `.env` and `.config.py`. Fill out these files.
8.  Run `openssl req -new -x509 -days 1460 -nodes -out localhost.pem -keyout localhost.pem` and follow the prompts.
9.  Run `./run.sh python`. Replace `python` with whatever python executable you want (py, py3, python3, etc)

At this point, the bot should run correctly. You can follow the steps below to setup completely:

## Steps (dashboard)
Follow these steps if you want to run the dashboard
1.  In the command line, run `python -c "import secrets; print(secrets.token_bytes(32))"` to generate your quart key.
2.  Copy the output, and put the result in the `QUART_KEY` field in `.env`
3.  In the developer portal, copy the client secret (NOT bot token) and put that in the `CLIENT_SECRET` field of `.env`
4.  On the OAuth2 page of your bot, add `http://0.0.0.0:5000/api/callback/` to the list of Redirect URIs.

Now, after running `launcher.py`, run the `run_dashboard.py` file in a seperate window, and it will launch on https://localhost:5000/
