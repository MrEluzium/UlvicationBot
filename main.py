# Copyright 2020 Артём Воронов
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import discord
from discord.ext import commands
from modules.baselogger import get_logger
from modules.database import DataBase
from modules.Paginator import Paginator
from settings import TOKEN, db_path
log = get_logger("bot")
db = DataBase(db_path)

guild_databases = {}
custom_prefixes = {}
default_prefixes = ['>']


def create_user(gdb, new_user_id, new_user_name, money=0.0):
    gdb.insert("Members", columns="id, tag, money", values=f"{new_user_id}, '{new_user_name}', {money}")


def to_float_or_int(num):
    if float(num) > int(float(num)):
        return float(num)
    else:
        return int(float(num))


def check_admin(ctx):
    if ctx.author.guild_permissions.administrator:
        return True
    guild_data = db.read("Guilds", "id", ctx.guild.id)
    if guild_data[2]:
        roles_list = str(guild_data[2]).split(";")
        for role in roles_list:
            if ctx.guild.get_role(int(role)) in ctx.author.roles:
                return True
    return False


async def get_prefix(bot, message):
    guild = message.guild
    if guild:
        return custom_prefixes.get(guild.id, default_prefixes)
    return default_prefixes

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command("help")


@bot.event
async def on_connect():
    log.info(f"{bot.user} has connected to Discord! Preparing...")

    db.create_table("Guilds", "prefix", "admin_roles")
    db_guilds = db.read_all("Guilds", "id, prefix")
    if db_guilds:  # if we have at lest one guild in database
        guilds = {}

        for g in db_guilds:
            guilds[g[0]] = g[1]  # {guild_id: guild_prefix}

        for bot_guild in bot.guilds:
            guild_databases[bot_guild.id] = DataBase(f"data/databases/{bot_guild.id}.db")
            guild_databases[bot_guild.id].create_table("Members", "tag", "money REAL NOT NULL", "organization")
            guild_databases[bot_guild.id].create_table("Orgs", "name NOT NULL UNIQUE", "points INT NOT NULL",
                                                       "rep INT NOT NULL",
                                                       id_replace="id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL")
            guild_databases[bot_guild.id].create_table("Shop", "price INT NOT NULL")
            if bot_guild.id not in guilds:  # if we don't have this guild in database
                db.insert("Guilds", "id", f"{bot_guild.id}")
            elif guilds[bot_guild.id]:
                custom_prefixes[bot_guild.id] = guilds[bot_guild.id] or default_prefixes

    else:
        for bot_guild in bot.guilds:
            db.insert("Guilds", "id", f"{bot_guild.id}")
            custom_prefixes[bot_guild.id] = default_prefixes

    cur_activity = discord.Game("Stardew Valley")
    await bot.change_presence(status=discord.Status.online, activity=cur_activity)


@bot.event
async def on_ready():
    log.info(f"{bot.user} is done preparing the data. Now we online!")


@bot.event
async def on_disconnect():
    log.warning(f"{bot.user} has disconnected from Discord.")


@bot.event
async def on_resumed():
    log.info(f"{bot.user} has resumed a session!")


@bot.event
async def on_guild_join(guild):
    log.info(f"{bot.user} has joined a new guild! Preparing...")
    guild_databases[guild.id] = DataBase(f"data/databases/{guild.id}.db")
    guild_databases[guild.id].create_table("Members", "tag", "money REAL NOT NULL", "organization")
    guild_databases[guild.id].create_table("Orgs", "name NOT NULL UNIQUE", "points INT NOT NULL", "rep INT NOT NULL",
                                           id_replace="id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL")
    guild_databases[guild.id].create_table("Shop", "price INT NOT NULL")

    db.insert("Guilds", "id", f"{guild.id}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
        log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: {error}")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("Эту команду нельзя использовать в личных сообщениях")
        log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: {error}")
    elif isinstance(error, commands.CheckFailure):
        if check_admin(ctx):
            await ctx.send(f"> Raised an unexpected error: {error}")
            log.error(f"Raised an unexpected error on message ({ctx.message.content}) by {ctx.message.author}: {error}")
        else:
            await ctx.send(f"У вас недостаточно прав для использования этой команды")
            log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: {error}")
    else:
        await ctx.send(f"> Raised an unexpected error: {error}")
        log.error(f"Raised an unexpected error on message ({ctx.message.content}) by {ctx.message.author}: {error}")


@bot.event
async def on_message(message):
    if not message.guild:  # if message sent in private messages with bot
        await bot.process_commands(message)
    else:
        message_prefix = default_prefixes[0]
        if message.guild.id in custom_prefixes:
            message_prefix = custom_prefixes[message.guild.id]

        if message.content.startswith(message_prefix):  # if message is our bot's command we raise it
            await bot.process_commands(message)

        elif not message.author.bot:  # if the author is not a bot
            gdb = guild_databases[message.guild.id]
            user = gdb.read("Members", "id", message.author.id)
            if user:
                gdb.update("Members", "id", message.author.id, "money", user[2]+0.5)  # Updating member money
            else:
                create_user(gdb, message.author.id, message.author.name, 0.5)


@bot.command(name="set_prefix", help="Назначить префикс для команд на этом сервере")
@commands.guild_only()
@commands.check(check_admin)
async def set_prefix(ctx, *, prefix):
    db.update("Guilds", "id", ctx.guild.id, "prefix", f"'{prefix}'")
    custom_prefixes[ctx.guild.id] = prefix
    await ctx.send("Prefix set!")


@bot.command(name="add_manager_role", aliases=["set_manager_role"],
             usage="[role mention]", help="Дает роли доступ к командам администрирования")
@commands.guild_only()
@commands.check(check_admin)
async def add_manager_role(ctx, role: discord.Role):
    guild_data = db.read("Guilds", "id", ctx.guild.id)
    roles_list = list()
    if guild_data[2]:
        roles_list = str(guild_data[2]).split(";")
    roles_list.append(str(role.id))

    db.update("Guilds", "id", ctx.guild.id, "admin_roles", f"'{';'.join(roles_list)}'")
    await ctx.send(f"{role.mention} теперь администрирует бота!")


@bot.command(name="remove_manager_role", aliases=["delete_manager_role", "rem_manager_role"],
             usage="[role mention]", help="Отбирает у роли доступ к командам администрирования")
@commands.guild_only()
@commands.check(check_admin)
async def remove_manager_role(ctx, role: discord.Role):
    guild_data = db.read("Guilds", "id", ctx.guild.id)
    if guild_data[2]:
        roles_list = str(guild_data[2]).split(";")
        try:
            roles_list.remove(str(role.id))
            db.update("Guilds", "id", ctx.guild.id, "admin_roles", f"'{';'.join(roles_list)}'")
            await ctx.send(f"{role.mention} больше не является администрирующей ролью!")
        except ValueError:
            await ctx.send(f"{role.mention} не является администрирующей ролью! Это точно нужная роль?")
    else:
        await ctx.send(f"Для этого сервера не заданы администрирующие роли. Вы можете добавить его командой add_manager_role!")


@bot.command(name="manager_roles", aliases=["show_manager_roles"],
             help="Показывает писок администрирующих ролей")
@commands.guild_only()
@commands.check(check_admin)
async def manager_roles(ctx):
    guild_data = db.read("Guilds", "id", ctx.guild.id)
    if guild_data[2]:
        roles_list = str(guild_data[2]).split(";")
        roles_string = f"*Роли, адмиинтрирующие бота на этом сервере:*"
        for role in roles_list:
            roles_string = roles_string + "\n> " + ctx.guild.get_role(int(role)).mention
        await ctx.send(roles_string)
    else:
        await ctx.send(f"Для этого сервера не заданы администрирующие роли. Вы можете добавить его командой add_manager_role!")


@bot.command(name="set_guild", aliases=["myguild"],
             usage="[guild_name]", help="Задает гильдию, в которой вы состоите")
@commands.guild_only()
async def set_guild(ctx, *, org_name):
    gdb = guild_databases[ctx.guild.id]
    org_data = gdb.read("Orgs", "name", f"'{org_name}'")
    if org_data:
        if not gdb.read("Members", "id", ctx.author.id):
            create_user(gdb, ctx.author.id, ctx.author.name)
        gdb.update("Members", "id", ctx.author.id, "organization", f"'{org_name}'")
        embed = discord.Embed(title=f"Теперь вы в гильдии {org_data[1]}!", color=discord.Colour.from_rgb(254, 254, 254))
        embed.set_image(url="https://media1.tenor.com/images/f8539f656d2ed90be7cd3bbe95d263d2/tenor.gif")
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title=f"Гильдии с именем {org_name} не существует!", color=discord.Colour.from_rgb(254, 254, 254))
        embed.set_image(url="https://media1.tenor.com/images/89d55748e5ae70caa2828b3768112c09/tenor.gif")
        await ctx.send(embed=embed)


@bot.command(name="profile", aliases=["me"],
             help="Показывает ваш профиль")
@commands.guild_only()
async def profile(ctx, *args):
    if ctx.message.mentions:  # if admin try to see member's profile
        if check_admin(ctx):
            member = ctx.message.mentions[0]
        else:
            embed = discord.Embed(title=f"У вас недостаточно прав для просмотра чужого профиля", color=discord.Colour.from_rgb(254, 254, 254))
            embed.set_image(url="https://media1.tenor.com/images/2aedb9ff34aa111c5789004d22d05a78/tenor.gif?itemid=12144903")
            await ctx.send(embed=embed)
            log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: У вас недостаточно прав для просмотра чужого профиля")
            return
    else:
        member = ctx.author

    gdb = guild_databases[ctx.message.guild.id]
    user_data = gdb.read("Members", "id", member.id)
    if not user_data:
        create_user(gdb, member.id, member.name)
        user_data = gdb.read("Members", "id", member.id)

    user_organization = ":crossed_swords: Гильдия: -"

    if user_data[3]:
        org_data = gdb.read("Orgs", "name", f"'{user_data[3]}'")
        if org_data:
            user_organization = f"\n:crossed_swords: Гильдия: {org_data[1]}\n" \
                                f":low_brightness: Очки: {org_data[2]}\n" \
                                f":military_medal: Репутанция: {org_data[3]}"

    rating_list = gdb.read_all_by_order("Members", "money", mod="DESC")
    rating_place = rating_list.index(user_data) + 1

    embed = discord.Embed(color=discord.Colour.from_rgb(254, 254, 254))
    embed.set_thumbnail(url=member.avatar_url)
    embed.add_field(name=f"**Профиль пользователя**", value=member.mention, inline=False)
    embed.add_field(name=f":coin: Монеты: {to_float_or_int(user_data[2])}\n"
                         f":crown: Рейтинг: {rating_place}\n"
                         f"{user_organization}",
                    value=" ‌‌‍‍", inline=False)
    await ctx.send(embed=embed)


# Команды для просмотра информации конкретной гильдии
# @bot.command()
# @commands.guild_only()
# async def guild(ctx, *, org_name):
#     pass


# @bot.command(name="guilds", help="Показывает список всех гильдий сервера")
# @commands.guild_only()
# async def guilds(ctx):
#     gdb = guild_databases[ctx.message.guild.id]
#     guild_org_list = gdb.read_all_by_order("Orgs", "points", mod="DESC")
#     if guild_org_list:
#         embeds = []
#         embed = discord.Embed(title=f"**Гильдии сервера**\n{ctx.guild.name}", color=discord.Colour.from_rgb(254, 254, 254))
#         embed_counter = 1
#         for org in guild_org_list:
#             embed.add_field(name=org[1], value=f":low_brightness:{org[2]}  •:military_medal:{org[3]}", inline=False)
#             if embed_counter % 5 == 0:
#                 embeds.append(embed)
#                 embed = discord.Embed(title=f"**Гильдии сервера**\n{ctx.guild.name}", color=discord.Colour.from_rgb(254, 254, 254))
#             embed_counter += 1
#         if (embed_counter - 1) % 5 != 0:
#             embeds.append(embed)
#         message = await ctx.send(embed=embeds[0])
#         page = Paginator(bot, message, use_more=False, embeds=embeds)
#         await page.start()
#     else:
#         embed = discord.Embed(title=f"Список гильдий для этого сервера пуст :(", color=discord.Colour.from_rgb(254, 254, 254))
#         embed.set_image(url="https://media1.tenor.com/images/a00ad898a26dbb80abb5cd3fc846fa4e/tenor.gif?itemid=16025185")
#         await ctx.send(embed=embed)


@bot.command(name="give_money", aliases=["add_money", "addcoin"],
             usage="[user mention] [amount]", help="Добавляет на счет пользователя указанное кол-во монет")
@commands.guild_only()
@commands.check(check_admin)
async def give_money(ctx, member_tag, amount):
    amount = to_float_or_int(amount)

    gdb = guild_databases[ctx.message.guild.id]
    if ctx.message.mentions:
        member = ctx.message.mentions[0]
    else:
        await ctx.send(f"Вам необходиом отметить пользователя!")
        return
    user_data = gdb.read("Members", "id", member.id)

    if not user_data:
        create_user(gdb, member.id, member.name, amount)
        await ctx.send(f"{member.mention} now has {amount} coins! (+{amount})")
    else:
        now_money = to_float_or_int(user_data[2] + amount)
        gdb.update("Members", "id", member.id, "money", now_money)
        await ctx.send(f"{member.mention} now has {now_money} coins! (+{amount})")


@bot.command(name="take_money", aliases=["takecoin"],
             usage="[user mention] [amount]", help="Отбирает у пользователя указанное кол-во монет")
@commands.guild_only()
@commands.check(check_admin)
async def take_money(ctx, member_tag, amount):
    amount = to_float_or_int(amount)

    gdb = guild_databases[ctx.message.guild.id]
    if ctx.message.mentions:
        member = ctx.message.mentions[0]
    else:
        await ctx.send(f"Вам необходиом отметить пользователя!")
        return
    user_data = gdb.read("Members", "id", member.id)

    if not user_data:
        create_user(gdb, member.id, member.name)
        await ctx.send(f"{member.mention} now has 0 coins! (-0)")
    else:
        if (user_data[2] - amount) < 0:
            await ctx.send(f"{member.mention} has less coins that you try to take!")
            return

        now_money = to_float_or_int(user_data[2] - amount)
        gdb.update("Members", "id", member.id, "money", now_money)
        await ctx.send(f"{member.mention} now has {now_money} coins! (-{amount})")


@bot.command(name="set_money", aliases=["setcoin"],
             usage="[user mention] [amount]", help="Устанавливает счет пользователя на указанное кол-во монет")
@commands.guild_only()
@commands.check(check_admin)
async def set_money(ctx, member_tag, amount):
    amount = to_float_or_int(amount)

    gdb = guild_databases[ctx.message.guild.id]

    if ctx.message.mentions:
        member = ctx.message.mentions[0]
    else:
        await ctx.send(f"Вам необходиом отметить пользователя!")
        return
    user_data = gdb.read("Members", "id", member.id)

    if not user_data:
        create_user(gdb, member.id, member.name, amount)
    else:
        gdb.update("Members", "id", member.id, "money", amount)

    await ctx.send(f"{member.mention}'s money now set on {amount} coins!")


@bot.command(name="add_role_shop", aliases=["addrole", "addshop"],
             usage="[role mention] [price]", help="Добавляет роль в магазин")
@commands.guild_only()
@commands.check(check_admin)
async def add_role_shop(ctx, role: discord.Role, price: to_float_or_int):
    gdb = guild_databases[ctx.message.guild.id]
    if not gdb.read("Shop", "id", role.id):
        gdb.insert("Shop", values=f"{role.id}, {price}")
        await ctx.send(f"Роль {role.mention} успешно добавлена в магазин! Цена: {price} монет")
    else:
        await ctx.send(f"Роль {role.mention} уже добавлена в магазин!")


@bot.command(name="edit_price", aliases=["editprice"],
             usage="[role mention] [price]", help="Изменяет цену роли в магазине")
@commands.guild_only()
@commands.check(check_admin)
async def edit_price(ctx, role: discord.Role, price: to_float_or_int):
    gdb = guild_databases[ctx.message.guild.id]
    if gdb.read("Shop", "id", role.id):
        gdb.update("Shop", "id", role.id, "price", price)
        await ctx.send(f"Теперь {role.mention} стоит {price} монет!")
    else:
        await ctx.send(f"Роль {role.mention} не добавлена в магазин!")


@bot.command(name="remove_role_shop", aliases=["removerole", "remrole"],
             usage="[role mention]", help="Удаляет роль из магазина")
@commands.guild_only()
@commands.check(check_admin)
async def remove_role_shop(ctx, role: discord.Role):
    gdb = guild_databases[ctx.message.guild.id]
    if gdb.read("Shop", "id", role.id):
        gdb.delete("Shop", "id", role.id)
        await ctx.send(f"Роль {role.mention} больше на продается в магазине!")
    else:
        await ctx.send(f"Роль {role.mention} не добавлена в магазин!")


@bot.command(name="shop", help="Магазин ролей")
@commands.guild_only()
async def shop(ctx):
    gdb = guild_databases[ctx.message.guild.id]
    roles_data_list = gdb.read_all_by_order("Shop", "price")
    if roles_data_list:
        embeds = []
        embed = discord.Embed(title=f":sparkles: __Магазин ролей__ :sparkles:", color=discord.Colour.from_rgb(254, 254, 254))
        embed_counter = 1
        for role in roles_data_list:
            role_obj = ctx.guild.get_role(role[0])
            if role_obj:
                embed.add_field(name=f"Цена: {role[1]} :coin:", value=role_obj.mention, inline=False)
                if embed_counter % 6 == 0:
                    embeds.append(embed)
                    embed = discord.Embed(title=f":sparkles: __Магазин ролей__ :sparkles:", color=discord.Colour.from_rgb(254, 254, 254))
                embed_counter += 1
        if (embed_counter - 1) % 6 != 0 and embed.fields:
            embeds.append(embed)
        if embeds:
            message = await ctx.send(embed=embeds[0])
            page = Paginator(bot, message, use_more=False, embeds=embeds)
            await page.start()
            return
    embed = discord.Embed(title=f"Магазин ролей пуст :(", color=discord.Colour.from_rgb(254, 254, 254))
    embed.set_image(url="https://media1.tenor.com/images/a00ad898a26dbb80abb5cd3fc846fa4e/tenor.gif?itemid=16025185")
    await ctx.send(embed=embed)


@bot.command(name="buy", aliases=["buy_role"],
             usage="[role mention]", help="Купить роль из магазина")
@commands.guild_only()
async def buy(ctx, role: discord.Role):
    gdb = guild_databases[ctx.message.guild.id]
    role_data = gdb.read("Shop", "id", role.id)
    if role_data:
        role_obj = ctx.guild.get_role(role_data[0])
        if role_obj:
            if role_obj not in ctx.author.roles:
                user_data = gdb.read("Members", "id", ctx.author.id)
                if not user_data:
                    create_user(gdb, ctx.author.id, ctx.author.name)
                if user_data[2] >= role_data[1]:
                    await ctx.author.add_roles(role_obj)
                    gdb.update("Members", "id", ctx.author.id, "money", user_data[2]-role_data[1])
                    embed = discord.Embed(title=f"Роль теперь ваша! UwU", color=discord.Colour.from_rgb(254, 254, 254))
                    embed.set_image(url="https://media1.tenor.com/images/d5da5398e5a193120690d0f0ca64d2ed/tenor.gif")
                    await ctx.send(embed=embed)
                    return
                else:
                    embed_text = "Эта роль стоит слишком дорого :("
            else:
                embed_text = "У вас уже есть эта роль"
        else:
            embed_text = "С этой ролью что-то не так..."
    else:
        embed_text = "Этой роли нет в магазине :("
    embed = discord.Embed(title=embed_text, color=discord.Colour.from_rgb(254, 254, 254))
    embed.set_image(url="https://media1.tenor.com/images/bf171e739294c6fa63d3a859f414978e/tenor.gif")
    await ctx.send(embed=embed)


@bot.command(name="create_guild", aliases=["newguild"],
             usage="[name]", help="Создает новую гильдию")
@commands.guild_only()
@commands.check(check_admin)
async def create_guild(ctx, *, name):
    gdb = guild_databases[ctx.message.guild.id]
    if not gdb.read("Orgs", "name", f"'{name}'"):
        gdb.insert("Orgs", columns="name, points, rep", values=f"'{name}', 0, 0")
        await ctx.send(f"Гильдия {name} успешно создана!")
    else:
        await ctx.send(f"Гильдия с именем {name} уже есть на сервере!")


@bot.command(name="edit_guild_name", aliases=["guildname"],
             usage='"[name]" "[new name]"', help="Меняет имя гильдии")
@commands.guild_only()
@commands.check(check_admin)
async def edit_guild_name(ctx, org_name, new_name):
    gdb = guild_databases[ctx.message.guild.id]
    if gdb.read("Orgs", "name", f"'{org_name}'"):
        gdb.update("Orgs", "name", f"'{org_name}'", "name", f"'{new_name}'")
        await ctx.send(f"Название гильдии {org_name} изменено на {new_name}!")
    else:
        await ctx.send(f"Гильдии с именем {org_name} не существует!")


@bot.command(name="give_guild_points", aliases=["givepoints", "addpoints"],
             usage="[name] [amount]", help="Добавляет указанное кол-во очков гильдии")
@commands.guild_only()
@commands.check(check_admin)
async def give_guild_points(ctx, *args):
    if len(args) > 1:
        try:
            amount = to_float_or_int(args[-1])
        except ValueError:
            await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
            return
        org_name = " ".join(args[:-1])
        gdb = guild_databases[ctx.message.guild.id]
        org_data = gdb.read("Orgs", "name", f"'{org_name}'")
        if org_data:
            gdb.update("Orgs", "name", f"'{org_name}'", "points", to_float_or_int(org_data[2]+amount))
            await ctx.send(f"Гильдия {org_name} теперь имеет {to_float_or_int(org_data[2]+amount)} очков! (+{amount})")
        else:
            await ctx.send(f"Гильдии с именем {org_name} не существует!")
    else:
        await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
        log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: Введены не все аргументы.")


@bot.command(name="take_guild_points", aliases=["rempoints", "takepoints"],
             usage="[name] [amount]", help="Отбирает указанное кол-во очков гильдии")
@commands.guild_only()
@commands.check(check_admin)
async def take_guild_points(ctx, *args):
    if len(args) > 1:
        try:
            amount = to_float_or_int(args[-1])
        except ValueError:
            await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
            return
        org_name = " ".join(args[:-1])
        gdb = guild_databases[ctx.message.guild.id]
        org_data = gdb.read("Orgs", "name", f"'{org_name}'")
        if org_data:
            if org_data[2]-amount >= 0:
                gdb.update("Orgs", "name", f"'{org_name}'", "points", to_float_or_int(org_data[2]-amount))
                await ctx.send(f"Гильдия {org_name} теперь имеет {to_float_or_int(org_data[2]-amount)} очков! (-{amount})")
            else:
                gdb.update("Orgs", "name", f"'{org_name}'", "points", 0)
                await ctx.send(f"Гильдия {org_name} теперь имеет 0 очков! (-{org_data[2]})")
        else:
            await ctx.send(f"Гильдии с именем {org_name} не существует!")
    else:
        await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
        log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: Введены не все аргументы.")


@bot.command(name="set_guild_points", aliases=["setpoints"],
             usage="[name] [amount]", help="Устанавливает указанное кол-во очков гильдии")
@commands.guild_only()
@commands.check(check_admin)
async def set_guild_points(ctx, *args):
    if len(args) > 1:
        try:
            amount = to_float_or_int(args[-1])
        except ValueError:
            await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
            return
        org_name = " ".join(args[:-1])
        gdb = guild_databases[ctx.message.guild.id]
        org_data = gdb.read("Orgs", "name", f"'{org_name}'")
        if org_data:
            gdb.update("Orgs", "name", f"'{org_name}'", "points", amount)
            await ctx.send(f"Гильдия {org_name} теперь имеет {amount} очков!")
        else:
            await ctx.send(f"Гильдии с именем {org_name} не существует!")
    else:
        await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
        log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: Введены не все аргументы.")


@bot.command(name="give_guild_rep", aliases=["giverep", "addrep"],
             usage="[name] [amount]", help="Добавляет гильдии указанное кол-во репутации")
@commands.guild_only()
@commands.check(check_admin)
async def give_guild_rep(ctx, *args):
    if len(args) > 1:
        try:
            amount = to_float_or_int(args[-1])
        except ValueError:
            await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
            return
        org_name = " ".join(args[:-1])
        gdb = guild_databases[ctx.message.guild.id]
        org_data = gdb.read("Orgs", "name", f"'{org_name}'")
        if org_data:
            gdb.update("Orgs", "name", f"'{org_name}'", "rep", to_float_or_int(org_data[3]+amount))
            await ctx.send(f"Гильдия {org_name} теперь имеет {to_float_or_int(org_data[3]+amount)} очков репутации! (+{amount})")
        else:
            await ctx.send(f"Гильдии с именем {org_name} не существует!")
    else:
        await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
        log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: Введены не все аргументы.")


@bot.command(name="take_guild_rep", aliases=["takerep"],
             usage="[name] [amount]", help="Отнимает у гильдии указанное кол-во репутации")
@commands.guild_only()
@commands.check(check_admin)
async def take_guild_rep(ctx, *args):
    if len(args) > 1:
        try:
            amount = to_float_or_int(args[-1])
        except ValueError:
            await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
            return
        org_name = " ".join(args[:-1])
        gdb = guild_databases[ctx.message.guild.id]
        org_data = gdb.read("Orgs", "name", f"'{org_name}'")
        if org_data:
            if org_data[2]-amount >= 0:
                gdb.update("Orgs", "name", f"'{org_name}'", "rep", to_float_or_int(org_data[3]-amount))
                await ctx.send(f"Гильдия {org_name} теперь имеет {to_float_or_int(org_data[3]-amount)} очков репутации! (-{amount})")
            else:
                gdb.update("Orgs", "name", f"'{org_name}'", "rep", 0)
                await ctx.send(f"Гильдия {org_name} теперь имеет 0 очков репутации! (-{org_data[3]})")
        else:
            await ctx.send(f"Гильдии с именем {org_name} не существует!")
    else:
        await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
        log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: Введены не все аргументы.")


@bot.command(name="set_guild_rep", aliases=["setrep"],
             usage="[name] [amount]", help="Устанавливает гильдии указанное кол-во репутации")
@commands.guild_only()
@commands.check(check_admin)
async def set_guild_rep(ctx, *args):
    if len(args) > 1:
        try:
            amount = to_float_or_int(args[-1])
        except ValueError:
            await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
            return
        org_name = " ".join(args[:-1])
        gdb = guild_databases[ctx.message.guild.id]
        org_data = gdb.read("Orgs", "name", f"'{org_name}'")
        if org_data:
            gdb.update("Orgs", "name", f"'{org_name}'", "rep", amount)
            await ctx.send(f"Гильдия {org_name} теперь имеет {amount} очков репутации!")
        else:
            await ctx.send(f"Гильдии с именем {org_name} не существует!")
    else:
        await ctx.send("Введены не все аргументы. Проверьте правильносьт введенной комманды")
        log.error(f"Raised error on message ({ctx.message.content}) by {ctx.message.author}: Введены не все аргументы.")


@bot.command(name="ping", help="Показывает задержку отправки собщений")
async def ping(ctx):
    t = await ctx.send(':ping_pong: calculation...')
    ms = (t.created_at - ctx.message.created_at).total_seconds() * 1000
    await t.edit(content=':ping_pong: Client Latency: {}ms'.format(int(ms)))


@bot.command(name='help', help="Показать это сообщение")
async def help(ctx):
    prefix = default_prefixes[0]
    if ctx.guild:
        if ctx.guild.id in custom_prefixes:
            prefix = custom_prefixes[ctx.guild.id]

    embeds = []
    embed = discord.Embed(title=f"**Команды Ulvication:**",
                          color=discord.Colour.from_rgb(254, 254, 254))
    embed_counter = 1

    for command in bot.commands:
        if check_admin not in command.checks:
            command_string = f"{prefix}{command.name}"
            command_string += " | " + " | ".join(command.aliases) if command.aliases else ""
            command_string += f" {command.usage}" if command.usage else ""
            command_string += f"  - {command.help}"
            embed.add_field(name=command_string, value=f" ‌‌‍‍", inline=False)
            if embed_counter % 10 == 0:
                embeds.append(embed)
                embed = discord.Embed(title=f"**Команды**",
                                      color=discord.Colour.from_rgb(254, 254, 254))
            embed_counter += 1

    if (embed_counter - 1) % 10 != 0:
        embeds.append(embed)
    await ctx.send(embed=embeds[0])
    # message = await ctx.send(embed=embeds[0])
    # page = Paginator(bot, message, use_more=False, embeds=embeds)
    # await page.start()


@bot.command(name='admin_help', help="Показать это сообщение")
@commands.guild_only()
@commands.check(check_admin)
async def admin_help(ctx):
    prefix = default_prefixes[0]
    if ctx.guild.id in custom_prefixes:
        prefix = custom_prefixes[ctx.guild.id]

    embeds = []
    embed = discord.Embed(title=f"**Команды Ulvication:**",
                          color=discord.Colour.from_rgb(254, 254, 254))
    embed_counter = 1

    for command in bot.commands:
        if check_admin in command.checks:
            command_string = f"{prefix}{command.name}"
            command_string += " | " + " | ".join(command.aliases) if command.aliases else ""
            command_string += f" {command.usage}" if command.usage else ""
            command_string += f"  - {command.help}"
            embed.add_field(name=command_string, value=f" ‌‌‍‍", inline=False)
            if embed_counter % 10 == 0:
                embeds.append(embed)
                embed = discord.Embed(title=f"**Команды**",
                                      color=discord.Colour.from_rgb(254, 254, 254))
            embed_counter += 1

    if (embed_counter - 1) % 10 != 0:
        embeds.append(embed)
    message = await ctx.send(embed=embeds[0])
    page = Paginator(bot, message, use_more=False, embeds=embeds)
    await page.start()


@bot.command(name="author", help="Информация об авторе бота")
async def author(ctx):
    embed = discord.Embed(title="\n:heartpulse: Артём Eluzium :heartpulse: ",
                          url="https://eluzium.aqulas.me/",
                          description=f"Этот бот был создан {bot.get_user(781211906572288001).mention}\n"
                                      f"Специально для серверов милаши Ulvi\n\n"
                                      f"Всем печенек <3",
                          color=discord.Colour.from_rgb(160, 160, 160))
    embed.set_image(url="https://i.gifer.com/2e9L.gif")
    await ctx.send(embed=embed)


if __name__ == '__main__':
    import os
    import platform
    log.info(f"\n\nStart on {platform.platform()}; "
             f"Python {platform.python_version()} {platform.python_compiler()}; "
             f"PID: {os.getpid()}")
    bot.run(TOKEN)
