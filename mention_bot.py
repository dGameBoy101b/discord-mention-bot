import discord
import logging
from asyncio import sleep, create_task

class MentionBot(discord.Client):
    '''Initialiser
    delete_delay: The number of seconds before a mention is deleted
    repeat_delay: The number of seconds until another mention is created in each channel'''
    def __init__(self, delete_delay:float=60, repeat_delay:float=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger('mention_bot')
        self.targets = dict()
        self.delete_delay = float(delete_delay)
        self.repeat_delay = float(repeat_delay)
        if self.delete_delay < 0:
            raise ValueError('delete_delay must be greater than 0')
        if self.repeat_delay < 0:
            raise ValueError('repeat_delay must be greater than 0')
        return
    '''Mention the targets on the given channel multiple times
    channel: The TextChannel to mention the targets on'''
    async def _mention_channel(self, channel:discord.TextChannel):
        if channel in self.targets:
            self.logger.debug(f'Will mention {",".join(map(lambda t: t.name, self.targets[channel]))} on {channel.guild.name}.{channel.name}')
            await channel.send(' '.join(map(lambda user: user.mention, self.targets[channel])), delete_after=self.delete_delay)
            self.logger.info(f'Mentioned {",".join(map(lambda t: t.name, self.targets[channel]))} on {channel.guild.name}.{channel.name}')
            remove = list()
            for user in self.targets[channel]:
                self.targets[channel][user] -= 1
                if self.targets[channel][user] < 1:
                    remove.append((channel,user))
            for (channel,user) in remove:
                del self.targets[channel][user]
                self.logger.debug(f'Removed {user.name} from {channel.guild.name}.{channel.name} target list')
            if len(self.targets[channel]) < 1:
                del self.targets[channel]
                self.logger.debug(f'Removed {channel.guild.name}.{channel.name} from target list')
            else:
                await sleep(self.repeat_delay)
                create_task(self._mention_channel(channel))
        return
    '''Parse a mantion command from the given message
    message: The message to parse for a command
    default_channel: If true and no channels are mentioned, default returned channels to message origin channel (None otherwise)
    default_author: If true and no roles or users are mentioned, default returned users and roles to message author (None otherwise)
    default_once: If true and no positive integers in message contents, default returned repeat to 1 (None otherwise)
    return: A tuple of parsed command arguments or None this bot is not mentioned
    return[0]: The list of channels to target
    return[1]: The list of roles and user to mention
    return[2]: The number of times to mention the target users and roles in the target channels'''
    def _parse_command(self,
                       message:discord.Message,
                       default_channel:bool=True,
                       default_author:bool=True,
                       default_once:bool=True)->([discord.TextChannel],[discord.User,discord.Role,discord.Member],int):
        if self.user not in message.mentions:
            return None
        channels = message.channel_mentions
        if len(channels) < 1:
            if default_channel:
                channels = [message.channel]
                self.logger.debug(f'Defaulting channels to {message.guild.name}.{message.channel.name}')
            else:
                channels = None
        targets = list(filter(lambda user: user != self.user, message.mentions)) + message.role_mentions
        if len(targets) < 1:
            if default_author:
                targets = [message.author]
                self.logger.debug(f'Defaulting targets to {message.author.name}')
            else:
                targets = None
        repeat = None
        for piece in message.content.split(' '):
            try:
                if int(piece) > 0:
                    repeat = int(piece)
                    break
            except ValueError:
                pass
        if default_once and repeat is None:
            repeat = 1
            self.logger.debug(f'Defaulting repeat to {repeat}')
        return (channels, targets, repeat)
    '''Add the given repeat mentions to the given targets in the given channels
    channels: The channels to add to
    targets: The roles and users to add to
    repeat: The number of mentions to add
    return: The given channels that are not currently running'''
    def _add_targets(self,
                     channels:[discord.TextChannel],
                     targets:[discord.User,discord.Role,discord.Member],
                     repeat:int)->[discord.TextChannel]:
        repeat = int(repeat)
        if repeat < 1:
            raise ValueError('repeat must be greater than 0')
        new_channels = list()
        for channel in channels:
            if isinstance(channel, discord.TextChannel):
                if channel not in self.targets:
                    self.targets[channel] = dict()
                    new_channels.append(channel)
                    self.logger.debug(f'Added {channel.guild.name}.{channel.name} to targets')
                for targ in targets:
                    if isinstance(targ, (discord.User, discord.Role, discord.Member)):
                        if targ not in self.targets[channel]:
                            self.targets[channel][targ] = 0
                            self.logger.debug(f'Added {targ.name} to {channel.guild.name}.{channel.name} target list')
                        self.targets[channel][targ] += repeat
                        self.logger.debug(f'Added {repeat} mentions to {targ.name} in {channel.guild.name}.{channel.name}: {self.targets[channel][targ]}')
                    else:
                        raise TypeError('target is not a user, member, or role')
            else:
                raise TypeError('channel is not a text channel')
        return new_channels
    '''Called when a message is posted in a channel mention bot is in
    self: The listening MentionBot instance
    message: The received message'''
    async def on_message(self, message:discord.Message):
        targs = self._parse_command(message)
        if targs is not None:
            self.logger.info(f'Will mention {",".join(map(lambda t: t.name, targs[1]))} {targs[2]} times in {",".join(map(lambda c: c.guild.name+"."+c.name, targs[0]))}')
            channels = self._add_targets(*targs)
            for channel in channels:
                create_task(self._mention_channel(channel))
        return

if __name__ == '__main__':
    from dotenv import load_dotenv
    from os import getenv
    from sys import stdout
    from logging import config
    #load token
    load_dotenv()
    token = getenv('TOKEN')
    #setup logging
    form = logging.Formatter('[%(asctime)s]<%(name)s>%(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    file_hand = logging.FileHandler('mention_bot.log', 'w')
    file_hand.setLevel(logging.DEBUG)
    file_hand.setFormatter(form)
    console_hand = logging.StreamHandler(stdout)
    console_hand.setLevel(logging.INFO)
    console_hand.setFormatter(form)
    logger = logging.getLogger('mention_bot')
    logger.propagate = True
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_hand)
    logger.addHandler(console_hand)
    logger.info('Started log')
    #run bot
    bot = MentionBot()
    bot.run(token)
