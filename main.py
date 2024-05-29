import discord
from discord import app_commands
from discord.ext import commands
import helpers
from typing import List
from discord.ext import tasks
import helpers
import re 
import asyncio
import logging
import dotenv
import os

dotenv.load_dotenv()

TOKEN = os.getenv("TOKEN")
bot = commands.Bot(command_prefix ='!',intents = discord.Intents.all())

DB_PATH = "database.db"

MAX_CATOGERY = 2    

@bot.event
async def on_ready():
    print(f'{bot.user} is online')
    if not categoryUpdate.is_running():
        categoryUpdate.start()
    try:
        synced = await bot.tree.sync()
        print(f'synced {len(synced)} command(s)')
    except Exception as e:
        print(e)

@tasks.loop(minutes=20)
async def categoryUpdate():
    print("Updating the category")
    categories = [category.id for category in bot.guilds[0].categories]
    categoryData = await helpers.fetchdata(DB_PATH, "CategoryData")
    cat_id_db = [recode[1] for recode in categoryData]
    for index , cat_id in enumerate(cat_id_db):
        if cat_id not in categories:
            await helpers.deleteCategoryData(DB_PATH , "CategoryData", {"category_id": cat_id})
            continue
        # update the channel form the database if the name is not same as the channel name
        toupdate = bot.get_channel(cat_id)
        if isinstance(toupdate , discord.CategoryChannel):
            channels = toupdate.voice_channels
            for i , channel in enumerate(channels):
                i = i + 2
                if channel.name != categoryData[index][i]:
                    await channel.edit(name = categoryData[index][i])
                    print("channel updated")

@categoryUpdate.error
async def categoryUpdate_error(error):
    logging.error(f"Error in Tasks loop : {error}")
    categoryUpdate.stop()
    
@bot.tree.command(name = "hello")
async def hello(interaction : discord.Interaction):
    await interaction.response.send_message("hi")
        
@bot.tree.command(name = "pool" , description="choose a pool!")
@app_commands.describe(pools = "choose a pool string")
@app_commands.checks.has_permissions(administrator=True)
async def p (interaction : discord.Interaction , pools : str ):
    await interaction.response.defer(ephemeral=True)
    # fetching categories that are in CURR1/CURR2.Address formate and ignoring other categories
    categories = [category.name for category in interaction.guild.categories if re.match(r'^[a-zA-Z0-9]+/[a-zA-Z0-9]+\.[a-zA-Z0-9]+$', category.name)]
    if len(categories) >= MAX_CATOGERY:
        await interaction.followup.send("Only *Two* catogaries can be made in one server!")
        return
    # fetching address of the pool
    address = await helpers.getAddress(pools)

    # fetching the AMM info of the address
    loop = asyncio.get_event_loop()
    amm_info = await loop.run_in_executor(None, helpers.getAMMInfo ,address[0][0])
    
    # Process the data in amm_info
    channels : list = helpers.ProcessedData(amm_info)

    # Create the category and channels
    category = await interaction.guild.create_category(pools)
    await interaction.guild.create_voice_channel(channels[0] , category=category)
    await interaction.guild.create_voice_channel(channels[1] , category=category)
    await interaction.guild.create_voice_channel(channels[2] , category=category)
    await interaction.guild.create_voice_channel(channels[3] , category=category)

    # insert the Category data into database
    await helpers.insertCategoryData(interaction.guild.id , category.id , channels[0],channels[1],channels[2],channels[3],channels[4])
    
    await interaction.followup.send(f"Check you discord Channels, A category named *{pools}* have created")
    
@p.autocomplete('pools')
async def pool_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    pools = await helpers.fetchdata(DB_PATH, "pools")
    p = [pool[0] for pool in pools]
    filtered_pools = [
        app_commands.Choice(name=pool, value=pool) 
        for pool in p if current.lower() in pool.lower()
    ][:25]
    return filtered_pools

@p.error
async def pool_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandInvokeError):
        await interaction.followup.send(f"Some error occured! pls contact admin.")
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.followup.send(f"You don't have permission to use this command!")

@bot.tree.command(name = "delete", description="delete a pool!")
@app_commands.checks.has_permissions(administrator=True)
async def d(interaction : discord.Interaction, category : str):
    await interaction.response.defer(ephemeral=True)
    category_to_delete = discord.utils.get(interaction.guild.categories, name=category)
    if category_to_delete:
        for channel in category_to_delete.channels:
            await channel.delete()
        await category_to_delete.delete()
        await helpers.deleteCategoryData(DB_PATH, "CategoryData", {"category_id": category_to_delete.id})
        await interaction.followup.send(f"Category '{category}' and all its channels have been deleted.")
    else:
        await interaction.followup.send(f"Category '{category}' not found.", ephemeral=True)
    
@d.autocomplete('category')
async def category_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    pattern = re.compile(r'^[a-zA-Z0-9]+/[a-zA-Z0-9]+\.[a-zA-Z0-9]+$')
    categories = [category.name for category in interaction.guild.categories if pattern.match(category.name)]
    filtered_categories = [category for category in categories if current.lower() in category.lower()]
    return [app_commands.Choice(name=category, value=category) for category in filtered_categories]

@d.error
async def category_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandInvokeError):
        await interaction.followup.send(f"Some error occured in deleting the category and its data!")

bot.run(TOKEN)
