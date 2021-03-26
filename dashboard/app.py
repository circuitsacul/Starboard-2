import os
from typing import Optional, Union, Tuple

import dotenv
import humanize
from quart import Quart, render_template, redirect, url_for, request
from quart_discord import DiscordOAuth2Session, Unauthorized, AccessDenied
import quart_discord
from quart_discord.utils import requires_authorization

import config
from . import app_config
from app.database.database import Database
from app.classes.ipc_connection import WebsocketConnection

dotenv.load_dotenv()

app = Quart(__name__)

app.secret_key = os.getenv("QUART_KEY")
app.config["DISCORD_CLIENT_ID"] = config.BOT_ID
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = config.REDIRECT_URI
app.config["DISCORD_BOT_TOKEN"] = os.getenv("TOKEN")

app.config["STATS"] = {}

app.config["DATABASE"] = Database(
    os.getenv("DB_NAME"), os.getenv("DB_USER"), os.getenv("DB_PASSWORD")
)
app.config["WEBSOCKET"] = None

discord = DiscordOAuth2Session(app)


async def handle_login(next: str = ""):
    return await discord.create_session(
        scope=["identify", "guilds"], data={"type": "user", "next": next}
    )


async def handle_command(msg: dict) -> Optional[Union[dict, str]]:
    cmd = msg["name"]
    data = msg["data"]

    resp = None
    if cmd == "ping":
        resp = "pont"
    if cmd == "set_stats":
        app.config["STATS"][msg["author"]] = {
            "guilds": data["guild_count"],
            "members": data["member_count"],
        }

    return resp


def bot_stats() -> Tuple[str]:
    guilds = humanize.intword(
        sum([s["guilds"] for _, s in app.config["STATS"].items()])
    )
    members = humanize.intword(
        sum([s["members"] for _, s in app.config["STATS"].items()])
    )
    return guilds, members


def can_manage(guild) -> bool:
    return guild.permissions.manage_guild


def can_manage_list(guilds: list) -> list:
    result = []
    for g in guilds:
        if can_manage(g):
            result.append(g)
    return result


# Jump Routes
@app.route("/support/")
async def support():
    return redirect(config.SUPPORT_INVITE)


@app.route("/invite/")
async def invite():
    return redirect(config.BOT_INVITE)


@app.route("/slash-auth/")
async def slash_auth():
    return redirect(config.SLASH_AUTH)


@app.route("/docs/")
async def docs():
    return redirect(config.DOCS)


# Dashboard Routes
@app.route("/dashboard/servers/")
@requires_authorization
async def servers():
    user = await discord.fetch_user()
    guilds = can_manage_list(await discord.fetch_guilds())
    guilds.sort(key=lambda g: g.name)

    msgs = await app.config["WEBSOCKET"].send_command(
        "get_mutual", [g.id for g in guilds], expect_resp=True
    )
    mutual_ids = []
    for msg in msgs:
        mutual_ids += msg["data"]

    return await render_template(
        "dashboard/servers.jinja",
        user=user,
        guilds=guilds,
        mutual=mutual_ids,
    )


@app.route("/dashboard/profile/")
@requires_authorization
async def profile():
    user = await discord.fetch_user()
    return await render_template("dashboard/profile.jinja", user=user)


@app.route("/dashboard/profile/settings/")
@requires_authorization
async def settings():
    user = await discord.fetch_user()
    return await render_template("dashboard/settings.jinja", user=user)


@app.route("/dashboard/premium/")
@requires_authorization
async def profile_premium():
    user = await discord.fetch_user()
    return await render_template("dashboard/premium.jinja", user=user)


# Base Routes
@app.route("/")
async def index():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None
    guilds, members = bot_stats()
    return await render_template(
        "home.jinja",
        user=user,
        sections=app_config.SECTIONS,
        members=members,
        guilds=guilds,
    )


@app.route("/premium/")
async def premium():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None
    return await render_template("premium.jinja", user=user)


# Api routes
@app.route("/login/")
async def login():
    return await handle_login()


@app.route("/logout/")
async def logout():
    discord.revoke()
    return redirect(url_for("index"))


@app.route("/api/callback/")
async def login_callback():
    data = await discord.callback()
    if data["type"] == "user":
        if data["next"]:
            return redirect(data["next"])
        else:
            return redirect(url_for("index"))


# Other
@app.errorhandler(Unauthorized)
async def handle_unauthorized(e):
    return await handle_login(next=request.path)


@app.errorhandler(AccessDenied)
async def handle_access_denied(e):
    return redirect(url_for("index"))


@app.before_first_request
async def before_first_request():
    await app.config["DATABASE"].init_database()
    app.config["WEBSOCKET"] = WebsocketConnection("Dashboard", handle_command)
    await app.config["WEBSOCKET"].ensure_connection()


@app.after_serving
async def after_serving():
    await app.config["WEBSOCKET"].close()
