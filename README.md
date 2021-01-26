# Starboard-2
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Maintainability](https://api.codeclimate.com/v1/badges/a99a88d28ad37a79dbf6/maintainability)](https://codeclimate.com/github/codeclimate/codeclimate/maintainability)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/CircuitsBots/Starboard-2/graphs/commit-activity)

:warning: This repo is under constant, daily development, and I'm making breaking changes on a daily basis. Until I finish the basics of this bot, I will not include database migrations. I would highly recommend waiting until I finish (maybe a month) before trying to self-host this bot. :warning:

A complete rewrite of Starboard

## Changes from Starboard-1
### Bug Fixes/Backend Improvements
 - Properly embed messages, handle spoilered messages better.
 - `None` no longer shows up as the point count on some messages when using `sb!random`
 - Fix duplicate starboard messages in the database
 - Store data more efficiently
 - Cluster the bot

### New settings 
 - `autoReact`: Whether or not the bot automatically adds reactions to its own messages
 - `removeReactions`: Whether or not the bot will remove invalid reactions (e.g. self-stars)
 - `noXp`: Whether or not to allow people to gain XP from this starboard
 - `allowRandom`: Whether or not to allow `sb!random` to pull from this starboard
 - `allowNSFW`: Whether or not messages from NSFW channels are allowed. Defaults to False. You'll need to enable this setting on any NSFW starboards you have.
 - `color`: Allows you to set the embed color of starboard messages
 - `displayEmoji`: Allows you to set what emoji shows up next to the number of points on a starboard message.

### New Features
 - You can now disable specific commands.

### New Commands
 - `sb!trashcan`: Shows a list of trashed messages
 - `sb!purge`: Trashes a large number of messages at once
 - `sb!logChannel`: Sets a channel for the bot to log problems/important info to
 - `sb!starboards changeSettings`: Change one or more settings for a starboard.
 - `sb!commands [enable/disable] [command]`: List/enable/disable commands

### Removed Commands
 - `sb!freeze`: Removed, since it seems to really have no use
 - `sb!unfreeze`: Same as above
 - `sb!frozen`: Same as above
 - `sb!starboards <setting>`: Removed in favor of `sb!starboards changeSettings`

### Changed Commands
 - `sb!force`: Instead of accepting a message_id and a channel_id, it now accepts a message link. You can also force to only some starboards, instead of having to force to all starboards.
 - `sb!unforce`: Same as above
 - `sb!trash`: Instead of accepting a message_id and a channel_id, it now accepts a message link.
 - `sb!untrash`: Same as above
 - `sb!random`: Added `--starboard` option, fix bugs.

## Credits
Thanks to TheNoob27 and [his starboard](https://top.gg/bot/655390915325591629) for inspiring me to create this bot and allowing me to base much of this bot on his.
