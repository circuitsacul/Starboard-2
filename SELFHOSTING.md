# Steps (required)
 1. Clone the repo by running `git clone https://github.com/CircuitsBots/Starboard-2.git`
 2. Create a virtual environment (with conda or venv) and then run `pip install -r requirements.txt`
 3. Create copies of `.env.example` and `.config.py.example` and name them `.env` and `.config.py`
 4. Go to the discord developer portal and create a new bot application (don't forget to add a bot user)
 5. Add the bot token into the `TOKEN` field of `.env`
 6. Install PostgreSQL (Starboard-2 has only been tested with PostgreSQL 13)
 7. Create a PostgreSQL user with a password, and put the username and password into the `DB_USER` and `DB_PASSWORD` fields in `.env`
 8. Create a new database owned by the user you created, and put the database name into the `DB_NAME` field in `.env`
 9. Put your discord id into the `OWNER_IDS` list in `config.py`, so it looks like this: `OWNER_IDS = [your_id_here]` (keeping the `[ ]`)
 10. Put your bots id into the `BOT_ID` field in `config.py`
 11. Run `python launcher.py` (if python doesn't work, you can also try `python3`, `py`, and `py3`)

At this point, the bot should run correctly. You can follow the steps below to setup completely:

# Steps (dashboard)
Follow these steps if you want to run the dashboard
 1. In the command line, run `python -c "import secrets; print(secrets.token_bytes(32))"` to generate your quart key.
 2. Copy the output, and put the result in the `QUART_KEY` field in `.env`
 3. In the developer portal, copy the client secret (NOT bot token) and put that in the `CLIENT_SECRET` field of `.env`
 4. On the OAuth2 page of your bot, add `http://0.0.0.0:5000/api/callback/` to the list of Redirect URIs.

Now, after running `launcher.py`, run the `run_dashboard.py` file in a seperate window, and it will launch on https://localhost:5000/
