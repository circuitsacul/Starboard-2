import os

import dotenv
from quart import Quart, render_template, redirect, url_for
from quart_discord import DiscordOAuth2Session, Unauthorized, AccessDenied
from quart_discord.utils import requires_authorization

import config

dotenv.load_dotenv()

app = Quart(__name__)

app.secret_key = os.getenv("QUART_KEY")
app.config["DISCORD_CLIENT_ID"] = config.BOT_ID
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = config.REDIRECT_URI
app.config["DISCORD_BOT_TOKEN"] = os.getenv("TOKEN")

discord = DiscordOAuth2Session(app)


# Dashboard Routes
@app.route("/manage/")
@requires_authorization
async def manage():
    user = await discord.fetch_user()
    guilds = await discord.fetch_guilds()
    return await render_template(
        "dashboard/server_picker.jinja", user=user, guilds=guilds
    )


# Base Routes
@app.route("/")
async def index():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None
    return await render_template("home.jinja", user=user)


@app.route("/login/")
async def login():
    return await discord.create_session()


@app.route("/logout/")
async def logout():
    discord.revoke()
    return redirect(url_for("index"))


@app.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()
    return await render_template("profile.jinja", user=user)


@app.route("/api/callback/")
async def login_callback():
    await discord.callback()
    return redirect(url_for("index"))


@app.errorhandler(Unauthorized)
async def handle_unauthorized(e):
    return redirect(url_for("login"))


@app.errorhandler(AccessDenied)
async def handle_access_denied(e):
    return redirect(url_for("index"))
