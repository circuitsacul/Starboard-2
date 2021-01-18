# Starboard-2
A complete rewrite of Starboard

## Changes from Starboard-1
### Bug Fixes/Backend Improvements
 - Properly embed messages, handle spoilered messages better.
 - `None` no longer shows up as the point count on some messages when using `sb!random`
 - Fix duplicate starboard-messages in the database
 - Store data more efficiently

### New settings
`autoReact`: Wether or not the bot automatically adds reactions to it's own messages
`removeReactions`: Wether or not the bot will remove invalid reaction (e.g. self-stars)
`noXp`: Wether or not to allow people to gain XP from this starboard
`explore`: Wether or not to allow `sb!random` to pull from this starboard
`allowNSFW`: Wether or not messages from NSFW channels are allowed. Defaults to False. You'll need to enable this setting on any NSFW starboards you have.

### New Features
Added `displayEmoji` option to each starboard, which defaults to :star:.
Original: `<points> | <channel>`
Now: `<displayEmoji> <points> | <channel>`
Example: **:star: 5 | #general**

### New Commands
`sb!trashcan`: Shows a list of trashed messages
`sb!purge`: Trashes a large number of messages at once

`sb!logChannel`: Sets a channel for the bot to log problems/important info to

`sb!starboards changeSettings`: Change one or more settings for a starboard.
Example: `sb!s cs #starboard --required 1 --requiredRemove 0 --selfStar False`

`sb!starworthy`: A fun command that gives you a ~~random~~ percentage for how "star worthy" a command is.

### Removed Commands
`sb!freeze`: Removed, since it seems to really have no use
`sb!unfreeze`: Same as above
`sb!frozen`: Same as above

`sb!starboards <setting>`: Removed in favor of `sb!starboards changeSettings`

### Changed Commands
`sb!force`: Instead of excepting a message_id and a channel_id, it now accepts a message link. You can also force to only some starboards, instead of having to force to all starboards.
`sb!unforce`: Same as above
`sb!trash`: Instead of excepting a message_id and a channel_id, it now accepts a message link. 
`sb!untrash`: Same as above

`sb!random`: Added `--starboard` option, fix bugs.
