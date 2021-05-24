import os
from typing import Dict, Optional, Tuple, Union

import dotenv
import humanize
from quart import Quart, redirect, render_template, request, url_for
from quart.helpers import flash
from quart_csrf import CSRFProtect
from quart_discord import AccessDenied, DiscordOAuth2Session, Unauthorized
from quart_discord.utils import requires_authorization

import config
from app.classes.ipc_connection import WebsocketConnection
from app.dashboard.db_wrapper import Wrapper

from . import app_config

dotenv.load_dotenv()

app = Quart(__name__)
CSRFProtect(app)

app.secret_key = os.getenv("QUART_KEY")
app.config["DISCORD_CLIENT_ID"] = config.BOT_ID
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = config.WEBSITE_URL + "/api/callback/"
app.config["DISCORD_BOT_TOKEN"] = os.getenv("TOKEN")

app.config["STATS"] = {}

app.config["WEBSOCKET"] = None

discord = DiscordOAuth2Session(app)
db = Wrapper()


async def get_guild(guild_id: int):
    guilds = await discord.fetch_guilds()
    guild = None
    for g in guilds:
        if g.id == guild_id:
            guild = g
            break
    return guild


async def get_guild_channels(guild_id: int) -> Dict[str, Dict[int, str]]:
    channels: Dict[str, Dict[int, str]] = {}
    for c in await app.config["WEBSOCKET"].send_command(
        "guild_channels", {"guild_id": guild_id}, expect_resp=True
    ):
        channels.update(c["data"])
    return channels


async def handle_login(after_login: str = ""):
    return await discord.create_session(
        scope=["identify", "guilds"],
        data={"type": "user", "next": after_login},
    )


async def handle_invite(guild_id: int):
    return await discord.create_session(
        scope=["bot"],
        data={"type": "guild"},
        permissions=config.BOT_PERM_INT,
        guild_id=guild_id,
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


def bot_stats() -> Tuple[str, str, str]:
    return (
        humanize.intcomma(7124),
        humanize.intcomma(3579381),
        humanize.intcomma(3179750),
    )
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


async def does_share(guild) -> bool:
    try:
        resp = await app.config["WEBSOCKET"].send_command(
            "is_mutual", {"gid": guild.id}, expect_resp=True
        )
    except Exception as e:
        print(e)
        return False
    return any([s["data"] for s in resp])


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

    mutual_ids = []
    try:
        msgs = await app.config["WEBSOCKET"].send_command(
            "get_mutual", [g.id for g in guilds], expect_resp=True
        )
        for msg in msgs:
            mutual_ids += msg["data"]
    except Exception as e:
        print(e)

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


@app.route("/dashboard/servers/<int:guild_id>/")
@requires_authorization
async def server_general(guild_id: int):
    user = await discord.fetch_user()

    guild = await get_guild(guild_id)

    if not guild:
        return redirect(url_for("servers"))
    if not can_manage(guild):
        return redirect(url_for("servers"))

    if not await does_share(guild):
        return await handle_invite(guild.id)

    return await render_template(
        "dashboard/server/general.jinja", user=user, guild=guild
    )


@app.route("/dashboard/servers/<int:guild_id>/starboards/")
@requires_authorization
async def server_starboards(guild_id: int):
    user = await discord.fetch_user()
    guild = await get_guild(guild_id)

    if not guild or not can_manage(guild):
        return redirect(url_for("servers"))

    if not await does_share(guild):
        return await handle_invite(guild.id)

    starboards = [dict(s) for s in await db.get_starboards(guild_id)]
    names = await app.config["WEBSOCKET"].send_command(
        "channel_names",
        {"channel_ids": [int(s["id"]) for s in starboards]},
        expect_resp=True,
    )
    name_dict = {}
    for c in names:  # each cluster returns it's own response
        for cid, name in c["data"].items():
            if name:
                name_dict[int(cid)] = name

    categories = await get_guild_channels(guild_id)

    for s in starboards:
        s["name"] = name_dict[int(s["id"])]

    return await render_template(
        "dashboard/server/starboard/list.jinja",
        user=user,
        guild=guild,
        starboards=starboards,
        categories=categories,
    )


@app.route(
    "/dashboard/servers/<int:guild_id>/starboards/create/",
    methods=["POST"],
)
@requires_authorization
async def create_starboard(guild_id: int):
    form = await request.form
    channel_id = form["channel_id"]

    guild = await get_guild(guild_id)

    if not guild or not can_manage(guild):
        return redirect(url_for("servers"))

    if not await does_share(guild):
        return await handle_invite(guild.id)

    _channels = await get_guild_channels(guild.id)
    channels = []
    for _, cat in _channels.items():
        for k, _ in cat.items():
            channels.append(k)

    if channel_id not in channels:
        await flash("Channel ID was not valid.", "error")
        return redirect(url_for("server_starboards", guild_id=guild_id))

    try:
        await db.db.starboards.create(channel_id, guild_id)
    except Exception as e:
        await flash(str(e), "error")
        return redirect(url_for("server_starboards", guild_id=guild_id))

    return redirect(
        url_for("manage_starboard", guild_id=guild_id, starboard_id=channel_id)
    )


@app.route(
    "/dashboard/servers/<int:guild_id>/starboards/<int:starboard_id>/delete/",
    methods=["POST"],
)
@requires_authorization
async def delete_starboard(guild_id: int, starboard_id: int):
    guild = await get_guild(guild_id)
    if not guild or not can_manage(guild):
        return redirect(url_for("servers"))

    if not await does_share(guild):
        return await handle_invite(guild.id)

    starboard_ids = [int(s["id"]) for s in await db.get_starboards(guild_id)]
    if starboard_id not in starboard_ids:
        return redirect(url_for("server_starboards", guild_id=guild_id))

    await db.db.starboards.delete(starboard_id)
    await flash("Starboard deleted.")

    return redirect(url_for("server_starboards", guild_id=guild_id))


@app.route("/dashboard/servers/<int:guild_id>/starboards/<int:starboard_id>/")
@requires_authorization
async def manage_starboard(guild_id: int, starboard_id: int):
    user = await discord.fetch_user()
    guild = await get_guild(guild_id)
    if not guild or not can_manage(guild):
        return redirect(url_for("servers"))

    if not await does_share(guild):
        return await handle_invite(guild.id)

    starboard_ids = [int(s["id"]) for s in await db.get_starboards(guild_id)]
    if starboard_id not in starboard_ids:
        return redirect(url_for("servers"))

    starboard = dict(await db.get_starboard(starboard_id))
    for c in await app.config["WEBSOCKET"].send_command(
        "channel_names",
        {"channel_ids": [int(starboard["id"])]},
        expect_resp=True,
    ):
        if c["data"][str(starboard["id"])]:
            starboard["name"] = c["data"][str(starboard["id"])]
            break
    else:
        starboard["name"] = "deleted"

    categories = await get_guild_channels(guild.id)

    return await render_template(
        "dashboard/server/starboard/manage.jinja",
        user=user,
        guild=guild,
        starboard=starboard,
        categories=categories,
    )


@app.route("/dashboard/servers/<int:guild_id>/autostar/")
@requires_authorization
async def server_autostar(guild_id: int):
    user = await discord.fetch_user()
    guild = await get_guild(guild_id)

    if not guild or not can_manage(guild):
        return redirect(url_for("servers"))

    if not await does_share(guild):
        return await handle_invite(guild.id)

    return await render_template(
        "dashboard/server/autostar/list.jinja", user=user, guild=guild
    )


# Base Routes
@app.route("/")
async def index():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None
    guilds, members, messages = bot_stats()
    return await render_template(
        "home.jinja",
        user=user,
        sections=app_config.SECTIONS,
        members=members,
        guilds=guilds,
        messages=messages,
    )


@app.route("/premium/")
async def premium():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None
    return await render_template("premium.jinja", user=user)


# Error Routes
@app.errorhandler(404)
async def err404(err):
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None
    return await render_template("error/404.jinja", user=user)


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
    elif data["type"] == "guild":
        _gid = request.args.get("guild_id")
        try:
            gid = int(_gid)
        except ValueError:
            return redirect(url_for("servers"))
        return redirect(url_for("server_general", guild_id=gid))


@app.route("/api/donatebot/", methods=["POST"])
async def handle_donate_event():
    data = {
        "data": await request.get_json(),
        "auth": request.headers["Authorization"],
    }
    await app.config["WEBSOCKET"].send_command(
        "donate_event", data, expect_resp=False
    )
    return "OK"


# Other
@app.errorhandler(Unauthorized)
async def handle_unauthorized(e):
    return await handle_login(request.path)


@app.errorhandler(AccessDenied)
async def handle_access_denied(e):
    return redirect(url_for("index"))


@app.before_first_request
async def before_first_request():
    try:
        await db.init()
    except Exception as e:
        print("Unable to connect to db:", e)
    try:
        app.config["WEBSOCKET"] = WebsocketConnection(
            "Dashboard", handle_command
        )
        await app.config["WEBSOCKET"].ensure_connection()
    except Exception as e:
        print("Unable to launch ipc, running with out it.")
        print(e)


@app.after_serving
async def after_serving():
    if app.config["WEBSOCKET"]:
        await app.config["WEBSOCKET"].close()
