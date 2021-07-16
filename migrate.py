from __future__ import annotations

import asyncio
import getpass
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    TypeVar,
)

import asyncpg
import cachetools
import discord
import progressbar as pb
from discord import Client

from app.cogs.leveling.leveling_funcs import current_level
from app.database.database import Database

T = TypeVar("T")
C = asyncpg.Connection


class DBInfo:
    def __init__(
        self,
        db_name: str,
        db_user: str,
        db_password: str,
        db_url: str,
    ):
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.db_url = db_url


async def aenumerate(
    iterable: AsyncIterator[T, Any] | AsyncGenerator[T, Any], start: int = 0
) -> AsyncGenerator[tuple[int, T], None]:
    current = start
    async for val in iterable:
        yield current, val
        current += 1


async def migrate_guilds(old: C, new: C, p: pb.ProgressBar):
    p.max_value = await old.fetchval("SELECT COUNT(1) FROM guilds")
    async for x, guild_data in aenumerate(
        old.cursor("""SELECT * FROM guilds""", prefetch=1_000)
    ):
        if x % 1_000 == 0:
            p.update(x)
        await new.execute(
            """INSERT INTO guilds
            (id, prefixes, qa_enabled, premium_end)
            VALUES ($1, $2, $3, $4)""",
            guild_data["id"],
            guild_data["prefixes"],
            guild_data["is_qa_on"],
            guild_data["premium_end"],
        )


async def migrate_users(old: C, new: C, p: pb.ProgressBar):
    p.max_value = await old.fetchval("SELECT COUNT(1) FROM users")
    async for x, user_data in aenumerate(
        old.cursor("""SELECT * FROM users""", prefetch=1_000)
    ):
        if x % 1_000 == 0:
            p.update(x)
        votes = await old.fetchval(
            """SELECT COUNT(1) FROM votes WHERE user_id=$1""",
            user_data["id"],
        )
        await new.execute(
            """INSERT INTO users
            (id, is_bot, credits, votes)
            VALUES ($1, $2, $3, $4)""",
            user_data["id"],
            user_data["is_bot"],
            user_data["credits"],
            votes,
        )


async def migrate_members(old: C, new: C, p: pb.ProgressBar):
    p.max_value = await old.fetchval("SELECT COUNT(1) FROM members")
    async for x, member_data in aenumerate(
        old.cursor("""SELECT * FROM members""", prefetch=1_000)
    ):
        if x % 1_000 == 0:
            p.update(x)
        await new.execute(
            """INSERT INTO members
            (user_id, guild_id, stars_given,
            stars_received, xp, level)
            VALUES ($1, $2, $3, $4, $5, $6)""",
            member_data["user_id"],
            member_data["guild_id"],
            member_data["given"],
            member_data["received"],
            member_data["xp"],
            current_level(int(member_data["xp"])),
        )
        if member_data["autoredeem"] is True:
            await new.execute(
                """INSERT INTO autoredeem (guild_id, user_id)
                VALUES ($1, $2)""",
                member_data["guild_id"],
                member_data["user_id"],
            )


async def migrate_starboards(old: C, new: C, p: pb.ProgressBar):
    p.max_value = await old.fetchval("SELECT COUNT(1) FROM starboards")
    async for x, sb_data in aenumerate(
        old.cursor("""SELECT * FROM starboards""", prefetch=1_000)
    ):
        if x % 1_000 == 0:
            p.update(x)
        sb_data = dict(sb_data)
        if sb_data["required"] < 1:
            sb_data["required"] = 1
        elif sb_data["required"] > 500:
            sb_data["required"] = 500
        if sb_data["rtl"] < -1:
            sb_data["rtl"] = -1
        elif sb_data["rtl"] > 495:
            sb_data["rtl"] = 495
        star_emojis = await old.fetch(
            """SELECT * FROM sbemojis WHERE starboard_id=$1""",
            sb_data["id"],
        )
        channel_bl_wl = await old.fetch(
            """SELECT * FROM channelbl WHERE starboard_id=$1""", sb_data["id"]
        )
        star_emojis = [se["name"] for se in star_emojis]
        channel_bl = [
            cb["channel_id"] for cb in channel_bl_wl if not cb["is_whitelist"]
        ]
        channel_wl = [
            cb["channel_id"] for cb in channel_bl_wl if cb["is_whitelist"]
        ]
        await new.execute(
            """INSERT INTO starboards
            (id, guild_id,
            required, required_remove, star_emojis,
            self_star, link_edits, link_deletes,
            allow_bots, images_only,
            channel_bl, channel_wl)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
            sb_data["id"],
            sb_data["guild_id"],
            sb_data["required"],
            sb_data["rtl"],
            star_emojis,
            sb_data["self_star"],
            sb_data["link_edits"],
            sb_data["link_deletes"],
            sb_data["bots_on_sb"],
            sb_data["require_image"],
            channel_bl,
            channel_wl,
        )


async def migrate_aschannels(old: C, new: C, p: pb.ProgressBar):
    p.max_value = await old.fetchval("SELECT COUNT(1) FROM aschannels")
    async for x, asc_data in aenumerate(
        old.cursor("""SELECT * FROM aschannels""", prefetch=1_000)
    ):
        if x % 1_000 == 0:
            p.update(x)
        asemojis = await old.fetch(
            """SELECT * FROM asemojis WHERE aschannel_id=$1""",
            asc_data["id"],
        )
        asemojis = [ase["name"] for ase in asemojis]
        await new.execute(
            """INSERT INTO aschannels
            (id, guild_id,
            min_chars, require_image, delete_invalid,
            emojis)
            VALUES ($1, $2, $3, $4, $5, $6)""",
            asc_data["id"],
            asc_data["guild_id"],
            asc_data["min_chars"],
            asc_data["require_image"],
            asc_data["delete_invalid"],
            asemojis,
        )


async def migrate_xproles(old: C, new: C, p: pb.ProgressBar):
    p.max_value = await old.fetchval("SELECT COUNT(1) FROM xproles")
    async for x, xpr_data in aenumerate(
        old.cursor("""SELECT * FROM xproles""", prefetch=1_000)
    ):
        if x % 1_000 == 0:
            p.update(x)
        await new.execute(
            """INSERT INTO xproles (role_id, guild_id, required)
            VALUES ($1, $2, $3)""",
            xpr_data["id"],
            xpr_data["guild_id"],
            xpr_data["req_xp"],
        )


async def migrate_posroles(old: C, new: C, p: pb.ProgressBar):
    p.max_value = await old.fetchval("SELECT COUNT(1) FROM posroles")
    async for x, pr_data in aenumerate(
        old.cursor("""SELECT * FROM posroles""", prefetch=1_000)
    ):
        if x % 1_000 == 0:
            p.update(x)
        await new.execute(
            """INSERT INTO posroles (role_id, guild_id, max_users)
            VALUES ($1, $2, $3)""",
            pr_data["id"],
            pr_data["guild_id"],
            pr_data["max_users"],
        )


async def migrate_messages(old: C, new: C, p: pb.ProgressBar):
    p.max_value = await old.fetchval(
        "SELECT COUNT(1) FROM messages WHERE is_orig=true"
    )
    async for x, msg in aenumerate(
        old.cursor(
            """SELECT * FROM messages WHERE is_orig=true""", prefetch=1_000
        )
    ):
        if x % 1_000 == 0:
            p.update(x)
        forced = []
        if msg["is_forced"]:
            starboards = await new.fetch(
                """SELECT * FROM starboards WHERE guild_id=$1""",
                msg["guild_id"],
            )
            forced = [s["id"] for s in starboards]
        await new.execute(
            """INSERT INTO messages
            (id, guild_id, channel_id, author_id,
            is_nsfw, forced, trashed, frozen)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            msg["id"],
            msg["guild_id"],
            msg["channel_id"],
            msg["user_id"],
            msg["is_nsfw"],
            forced,
            msg["is_trashed"],
            msg["is_frozen"],
        )


async def migrate_starboard_messages(old: C, new: C, p: pb.ProgressBar) -> str:
    p.max_value = await old.fetchval(
        "SELECT COUNT(1) FROM messages WHERE is_orig=false"
    )
    failed = 0
    async for x, msg in aenumerate(
        old.cursor(
            """SELECT * FROM messages WHERE is_orig=false""", prefetch=1_000
        )
    ):
        if x % 1_000 == 0:
            p.update(x)
        try:
            await new.execute(
                """INSERT INTO starboard_messages
                (id, orig_id, starboard_id, points)
                VALUES ($1, $2, $3, $4)""",
                msg["id"],
                msg["orig_message_id"],
                msg["channel_id"],
                msg["points"] or 0,
            )
        except asyncpg.exceptions.ForeignKeyViolationError:
            failed += 1
    return f"{failed} failed due to bad foreign key."


async def migrate_reactions(old: C, new: C, p: pb.ProgressBar) -> str:
    p.max_value = await old.fetchval("SELECT COUNT(1) FROM reactions")

    cache = cachetools.LRUCache(100_000)
    guild_star_emojis: dict[int, set[str] | list[str]] = {}

    migrated = 0
    skipped = 0
    failed_u = 0

    for sb in await new.fetch("SELECT * FROM starboards"):
        guild_star_emojis.setdefault(sb["guild_id"], []).extend(
            sb["star_emojis"]
        )

    # Change the lists to sets to allow for faster `if ... in ...` checks.
    for key, lst in guild_star_emojis.items():
        guild_star_emojis[key] = set(lst)

    async for x, reaction in aenumerate(
        old.cursor("""SELECT * FROM reactions""", prefetch=1_000)
    ):
        if x % 1_000 == 0:
            p.update(x)
        if reaction["name"] not in guild_star_emojis.get(
            reaction["guild_id"], []
        ):
            skipped += 1
            continue
        reaction_id = cached = cache.get(
            (reaction["name"], reaction["message_id"]), None
        )
        if not reaction_id:
            existing = await new.fetchrow(
                "SELECT * FROM reactions WHERE emoji=$1 AND message_id=$2",
                reaction["name"],
                reaction["message_id"],
            )
            reaction_id = existing["id"] if existing else None
        if not reaction_id:
            await new.execute(
                """INSERT INTO reactions (emoji, message_id)
                VALUES($1, $2)""",
                reaction["name"],
                reaction["message_id"],
            )
            existing = await new.fetchrow(
                "SELECT * FROM reactions WHERE emoji=$1 AND message_id=$2",
                reaction["name"],
                reaction["message_id"],
            )
            reaction_id = existing["id"]
        if not cached:
            cache[(reaction["name"], reaction["message_id"])] = reaction_id

        try:
            await new.execute(
                """INSERT INTO reaction_users (reaction_id, user_id)
                VALUES ($1, $2)""",
                reaction_id,
                reaction["user_id"],
            )
        except asyncpg.exceptions.UniqueViolationError:
            failed_u += 1
            continue
        migrated += 1

    return (
        f"{migrated} reactions migrated, with {skipped} skipped. "
        f"{failed_u} failed due to duplication."
    )


async def convert_wl_bl_to_pg(
    old: C, _: C, p: pb.ProgressBar, client: Client, new: Database
) -> str | None:
    # Logic:
    # - Get list of starboard ids that have role blacklist/whitelists
    # - For each starboard_id:
    #   - Create a permgroup with the name role_blacklist_<starboard id>,
    #     make sure it only affects the one starboard
    #   - Select all blacklisted roles
    #     - If there are none, that must mean there are whitelisted roles.
    #       - Use the client to fetch the guild and get the default role.
    #       - Set the `giveStars` permission for the default (@everyone)
    #         role to False
    #     - Otherwise, set the `giveStars` permission for each role to False
    #   - Select all whitelisted roles
    #     - If there are more than 0
    #       - Create a permgroup with the name role_whitelist_<starboard id>,
    #         make sure it only affects one starboard
    #       - For each, set the `giveStars` permission to True
    # Creating the blacklisted permgroup first ensures it applies first.
    print("Converting role blacklists/whitelist to permgroups...")

    starboard_guild_ids = list(
        set(
            [
                (r["starboard_id"], r["guild_id"])
                for r in await old.fetch(
                    """SELECT starboard_id, guild_id FROM rolebl"""
                )
            ]
        )
    )

    failed = 0

    p.max_value = len(starboard_guild_ids)
    curr = 0
    for starboard_id, guild_id in starboard_guild_ids:
        p.update(curr)
        curr += 1
        bl_name = f"role_bl_{starboard_id}"
        wl_name = f"role_wl_{starboard_id}"

        await new.permgroups.create(guild_id, bl_name)
        bl_id = (await new.permgroups.get_name(guild_id, bl_name))["id"]
        await new.permgroups.set_starboards(bl_id, [starboard_id])

        bl_roles = await old.fetch(
            """SELECT * FROM rolebl
            WHERE starboard_id=$1 AND is_whitelist=false""",
            starboard_id,
        )
        if len(bl_roles) == 0:
            try:
                guild = await client.fetch_guild(int(guild_id))
            except discord.Forbidden:
                failed += 1
            except discord.NotFound:
                continue
            else:
                default_role = guild.default_role.id
                await new.permroles.create(bl_id, default_role)
                await new.permroles.edit(default_role, bl_id, give_stars=False)
        else:
            for r in bl_roles:
                rid = r["role_id"]
                await new.permroles.create(bl_id, rid)
                await new.permroles.edit(rid, bl_id, give_stars=False)

        wl_roles = await old.fetch(
            """SELECT * FROM rolebl
            WHERE starboard_id=$1 AND is_whitelist=true""",
            starboard_id,
        )
        if len(wl_roles) > 0:
            await new.permgroups.create(guild_id, wl_name)
            wl_id = (await new.permgroups.get_name(guild_id, wl_name))["id"]
            await new.permgroups.set_starboards(wl_id, [starboard_id])
            for r in wl_roles:
                rid = r["role_id"]
                await new.permroles.create(wl_id, rid)
                await new.permroles.edit(rid, wl_id, give_stars=True)

    if failed > 0:
        return (
            f"{failed} weren't able to fully convert, because the bot "
            "wasn't in those guilds."
        )
    return None


async def run_migration(
    func: Callable[[C, C, pb.ProgressBar], Awaitable[str | None]],
    old: C,
    new_db: Database,
    check_table: bool = True,
    extra_args: tuple[Any] | None = None,
):
    extra_args = extra_args or ()
    print("")
    async with old.transaction():
        async with new_db.pool.acquire() as new:
            new: C
            if check_table:
                tablename = func.__name__.replace("migrate_", "")
                # NOTE: Using f-strings for SQL queries is a *terrible* idea.
                #       I only use it here because I know exactly what
                #       "tablename" is going to be, so there is no risk of sql
                #       injection.
                count = await new.fetchval(f"SELECT COUNT(1) FROM {tablename}")
                if count != 0:
                    print(
                        f'Skipping "{tablename}", as it appears to '
                        "already have been migrated."
                    )
                    return
                print(f'Migrating "{tablename}"...')

            p = pb.ProgressBar(max_value=1)
            p.widgets = p.default_widgets()
            p.widgets[-1] = pb.ETA(format_finished="ETA:  00:00:00")
            res = None
            try:
                res = await func(old, new, p, *extra_args)
            except Exception:
                p.finish(dirty=True)
                raise
            else:
                p.finish()
            finally:
                if res:
                    print(res)


async def main(
    olddb: asyncpg.Connection, newdb: Database, client: Client | None
):
    migrations = [
        migrate_guilds,
        migrate_users,
        migrate_members,
        migrate_starboards,
        migrate_aschannels,
        migrate_xproles,
        migrate_posroles,
        migrate_messages,
        migrate_starboard_messages,
        migrate_reactions,
    ]
    for func in migrations:
        await run_migration(func, olddb, newdb)
    if client:
        await run_migration(
            convert_wl_bl_to_pg,
            olddb,
            newdb,
            check_table=False,
            extra_args=(
                client,
                newdb,
            ),
        )
    print("\nMigration complete!")


def get_db_info() -> DBInfo:
    dbname = input("Database Name: ")
    dbuser = input("Database User: ")
    dbpwd = getpass.getpass("Database User Password: ")
    dburl = "localhost"
    return DBInfo(dbname, dbuser, dbpwd, dburl)


async def connect():
    print(
        "This is a script to allow migration from Starboard to Starboard-2 "
        "without losing any data. Continue? (Y/n)",
        end="",
    )
    if input(": ").lower().strip() != "y":
        return
    print("Info for the new database:")
    dbinfo = get_db_info()
    new_db = Database(dbinfo.db_name, dbinfo.db_user, dbinfo.db_password)
    try:
        await new_db.init_database(True)
    except Exception as e:
        print(
            f"Unable to connect to database: {e.__class__.__name__}: {str(e)}"
        )
        return

    print("Info for the old database:")
    dbinfo = get_db_info()
    try:
        oldcon: asyncpg.Connection = await asyncpg.connect(
            host=dbinfo.db_url,
            user=dbinfo.db_user,
            password=dbinfo.db_password,
            database=dbinfo.db_name,
        )
    except Exception as e:
        print(
            f"Unable to connect to database: {e.__class__.__name__}: {str(e)}"
        )
        await new_db.pool.close()
        return

    if (
        not input(
            "Do you want to convert role blacklist/whitelist to permgroups? "
            "If you choose not to, and you previously used role blacklist/"
            "whitelist, Starboard may not function as expected.\n(Y/n): ",
        )
        .lower()
        .strip()
        .startswith("y")
    ):
        token = None
        print("Role blacklist/whitelists will not be migrated.")
    else:
        print(
            "In order to convert properly, a bot token is required. "
            "The token doesn't have to belong to the starboard bot, "
            "but the bot does have to be in any guilds you want to "
            "convert role blacklists/whitelists in."
        )
        token = getpass.getpass("Bot Token: ")

    if token is not None:
        client = Client()
        try:
            await client.login(token)
        except Exception as e:
            print(e.__class__.__name__ + ": " + str(e))
            await client.close()
            return
    else:
        client = None

    try:
        await main(oldcon, new_db, client)
    finally:
        await new_db.pool.close()
        await oldcon.close()
        if client:
            await client.close()


if __name__ == "__main__":
    asyncio.run(connect())
