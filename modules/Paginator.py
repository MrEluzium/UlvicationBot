# MIT License
#
# Copyright (c) 2020 RuCybernetic
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Module of Cybernator library by RuCybernetic.
# Original library: https://github.com/RuCybernetic/Cybernator
import discord
import asyncio


class Cybered(Exception):
    pass


class Cyberad(Exception):
    pass


class Paginator:
    def __init__(
            self,
            ctx,
            message: discord.Message,
            embeds: list = None,
            use_images: bool = False,
            images: list = None,
            timeout: int = 35,
            use_more: bool = False,
            use_exit: bool = False,
            only: discord.abc.User = None,
            delete_message: bool = False,
            time_stamp: bool = False,
            footer: bool = True,
            footer_icon: str = None,
            reactions: list = ["⬅", "➡"],
            more_reactions: list = ["⬅", "➡", "⏪", "⏩"],
            exit_reaction: list = ["⏹"],
            color: int = None,
            use_remove_reaction: bool = True
    ):
        self.ctx = ctx
        self.message = message
        self.timeout = timeout
        self.reactions = reactions
        self.more_reactions = more_reactions
        self.exit_reaction = exit_reaction
        self.index = 0
        self.index_page = 0
        self.is_time_up = False
        self.embeds = embeds
        self.use_images = use_images
        self.images = images
        self.use_more = use_more
        self.use_exit = use_exit
        self.only = only
        self.delete_message = delete_message
        self.time_stamp = time_stamp
        self.footer = footer
        self.color = color
        self.footer_icon = footer_icon
        self.use_remove_reaction = use_remove_reaction

        if embeds is None:
            raise Cybered('Cybernetic съел ваш embeds.')
        if not isinstance(self.timeout, int):
            raise Cyberad('Что-то пошло не так...')
        if self.only is not None:
            if not isinstance(self.only, discord.abc.User):
                raise TypeError

    def emoji_checker(self, payload):
        if payload.user_id == self.ctx.user.id:
            return False
        if payload.message_id != self.message.id:
            return False
        if self.only is not None:
            if payload.user_id != self.only.id:
                return False
        if self.use_more:
            if str(payload.emoji) in self.more_reactions:
                return True
        else:
            if str(payload.emoji) in self.reactions:
                return True
        if self.use_exit:
            if str(payload.emoji) in self.exit_reaction:
                return True
        return False

    async def add_reactions(self):
        if self.use_more:
            for i in self.more_reactions:
                await self.message.add_reaction(i)
            if self.use_exit:
                await self.message.add_reaction(self.exit_reaction[0])
        else:
            for i in self.reactions:
                await self.message.add_reaction(i)
            if self.use_exit:
                await self.message.add_reaction(self.exit_reaction[0])
        return True

    async def start(self):
        try:
            await self.section()
        except:
            await self.page()
        await self.add_reactions()

        while True:
            try:
                add_reaction = asyncio.ensure_future(
                    self.ctx.wait_for(
                        "raw_reaction_add", check=self.emoji_checker
                    )
                )
                done, pending = await asyncio.wait(
                    (add_reaction, add_reaction),
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=self.timeout,
                )

                for i in pending:
                    i.cancel()

                if len(done) == 0:
                    raise asyncio.TimeoutError()

                payload = done.pop().result()
                await self.pagination(payload.emoji)
                try:
                    if self.use_remove_reaction:
                        await self.message.remove_reaction(payload.emoji, payload.member)
                    else:
                        pass
                except AttributeError:
                    pass

            except asyncio.TimeoutError:
                try:
                    self.is_time_up = True
                    if self.delete_message:
                        await self.message.delete()
                    else:
                        if self.use_more:
                            await self.page()
                        else:
                            await self.section()
                        if self.message.guild:
                            await self.message.clear_reactions()
                        else:
                            pass
                    break
                except:
                    await self.section()
                    if self.message.guild:
                        await self.message.clear_reactions()
                    else:
                        pass
                break

    async def pagination(self, emoji):
        if self.use_more:
            if str(emoji) == str(self.more_reactions[0]):
                await self.go_section_previous()
            elif str(emoji) == str(self.more_reactions[1]):
                await self.go_section_next()
            elif str(emoji) == str(self.more_reactions[2]):
                await self.go_page_previous()
            elif str(emoji) == str(self.more_reactions[3]):
                await self.go_page_next()
            elif str(emoji) == str(self.exit_reaction[0]):
                raise asyncio.TimeoutError
        else:
            if str(emoji) == str(self.reactions[0]):
                await self.go_section_previous()
            elif str(emoji) == str(self.reactions[1]):
                await self.go_section_next()
            elif str(emoji) == str(self.exit_reaction[0]):
                raise asyncio.TimeoutError

    async def go_section_previous(self):
        if self.index != 0:
            self.index -= 1
            try:
                await self.section()
            except Exception as e:
                print(repr(e))
                self.index_page = 0
                await self.page()

    async def go_page_next(self):
        try:
            if self.embeds[self.index][self.index_page]:
                if self.index_page != len(self.embeds[self.index][self.index_page]) - 1:
                    self.index_page += 1
                    await self.page()
        except Exception as e:
            print(repr(e))
            pass

    async def go_section_next(self):
        try:
            if self.index != len(self.embeds) - 1:
                self.index += 1
                await self.section()
        except Exception as e:
            print(repr(e))
            self.index_page = 0
            await self.page()

    async def go_page_previous(self):
        if self.index_page != 0:
            self.index_page -= 1
            try:
                await self.page()
            except Exception as e:
                print(repr(e))
                pass

    async def section(self):
        if self.is_time_up:
            self.embeds[self.index].set_footer(text=f'Раздел: [{1 + self.index}/{len(self.embeds)}] [Время вышло]',
                                               icon_url=self.footer_icon if self.footer_icon is not None else '')
        else:
            self.embeds[self.index].set_footer(text=f'Раздел: [{1 + self.index}/{len(self.embeds)}]',
                                               icon_url=self.footer_icon if self.footer_icon is not None else '')
        if self.time_stamp is True:
            self.embeds[self.index].timestamp = self.message.created_at
        if self.color is not None:
            self.embeds[self.index].colour = self.color
        if self.use_images:
            return await self.message.edit(file=self.images[self.index], embed=self.embeds[self.index])
        else:
            return await self.message.edit(embed=self.embeds[self.index])

    async def page(self):
        if self.is_time_up:
            self.embeds[self.index][self.index_page].set_footer(
                text=f'Раздел: [{1 + self.index}/{len(self.embeds)}] Страница: [{1 + self.index_page}/{len(self.embeds[self.index])}] [Время вышло]',
                icon_url=self.footer_icon if self.footer_icon is not None else '')
        else:
            self.embeds[self.index][self.index_page].set_footer(
                text=f'Раздел: [{1 + self.index}/{len(self.embeds)}] Страница: [{1 + self.index_page}/{len(self.embeds[self.index])}]',
                icon_url=self.footer_icon if self.footer_icon is not None else '')
        if self.time_stamp is True:
            self.embeds[self.index][self.index_page].timestamp = self.message.created_at
        if self.color is not None:
            self.embeds[self.index][self.index_page].colour = self.color

        if self.use_images:
            return await self.message.edit(file=self.images[self.index][self.index_page], embed=self.embeds[self.index][self.index_page])
        else:
            return await self.message.edit(embed=self.embeds[self.index][self.index_page])
