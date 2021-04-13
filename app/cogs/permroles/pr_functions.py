import discord

from app.i18n import t_


def pretty_permrole_string(
    role: dict[str, bool], guild: discord.Guild
) -> tuple[str, str]:
    obj = guild.get_role(role["role_id"])
    role_name = obj.name if obj else f"Delete Role {role['role_id']}"
    role_name = "{0}. {1}".format(role["index"], role_name)

    def setting(name: str) -> str:
        return role[name] or t_("Default")

    result = (
        f"allowCommands: {setting('allow_commands')}\n"
        f"recvStars: {setting('recv_stars')}\n"
        f"giveStars: {setting('give_stars')}\n"
        f"gainXp: {setting('gain_xp')}\n"
        f"posRoles: {setting('pos_roles')}\n"
        f"xpRoles: {setting('xp_roles')}\n"
    )

    return role_name, result
