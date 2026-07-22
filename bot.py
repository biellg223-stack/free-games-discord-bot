import os
import json
import asyncio
import aiohttp
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

# =========================
# CONFIGURAÇÕES
# =========================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Verifica ofertas a cada 30 minutos
CHECK_INTERVAL = 30

# Arquivo que guarda as ofertas já publicadas
DATABASE_FILE = "published_games.json"


# =========================
# BANCO DE DADOS SIMPLES
# =========================

def load_published_games():
    if not os.path.exists(DATABASE_FILE):
        return set()

    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as file:
            return set(json.load(file))
    except:
        return set()


def save_published_games(games):
    with open(DATABASE_FILE, "w", encoding="utf-8") as file:
        json.dump(list(games), file, ensure_ascii=False, indent=2)


published_games = load_published_games()


# =========================
# DISCORD
# =========================

intents = discord.Intents.default()

bot = discord.Client(intents=intents)


# =========================
# BUSCAR JOGOS GRÁTIS
# =========================

async def get_free_games():

    url = "https://www.gamerpower.com/api/giveaways"

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(url, timeout=30) as response:

                if response.status != 200:
                    print("Erro ao consultar a API.")
                    return []

                data = await response.json()

                games = []

                for giveaway in data:

                    platform = giveaway.get("platforms", "")

                    # Apenas Steam e Epic Games
                    if "Steam" not in platform and "Epic Games" not in platform:
                        continue

                    game_id = str(giveaway.get("id"))

                    if game_id in published_games:
                        continue

                    games.append(giveaway)

                return games

    except Exception as error:

        print(f"Erro: {error}")

        return []


# =========================
# ENVIAR EMBED
# =========================

async def send_game(giveaway):

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:

        print("Canal não encontrado.")

        return


    title = giveaway.get("title", "Jogo grátis")

    description = giveaway.get(
        "description",
        "Um jogo está disponível gratuitamente!"
    )

    image = giveaway.get("image")

    link = giveaway.get("open_giveaway_url")

    platforms = giveaway.get(
        "platforms",
        "Não informado"
    )

    end_date = giveaway.get(
        "end_date",
        "Não informado"
    )


    embed = discord.Embed(

        title=f"🎮 {title}",

        description=description,

        url=link,

        color=discord.Color.green()

    )


    if image:

        embed.set_image(url=image)


    embed.add_field(

        name="🏪 Plataforma",

        value=platforms,

        inline=True

    )


    embed.add_field(

        name="⏰ Termina em",

        value=end_date,

        inline=True

    )


    embed.add_field(

        name="🔗 Resgatar",

        value=f"[Clique aqui para resgatar]({link})",

        inline=False

    )


    embed.set_footer(

        text="Free Games Bot • Oferta detectada automaticamente"

    )


    await channel.send(embed=embed)


# =========================
# VERIFICAR OFERTAS
# =========================

@tasks.loop(minutes=CHECK_INTERVAL)
async def check_games():

    print("Verificando novos jogos grátis...")

    games = await get_free_games()


    for game in games:

        game_id = str(game.get("id"))

        try:

            await send_game(game)

            published_games.add(game_id)

            save_published_games(published_games)

            print(
                f"Oferta publicada: {game.get('title')}"
            )

            await asyncio.sleep(2)

        except Exception as error:

            print(
                f"Erro ao publicar oferta: {error}"
            )


# =========================
# BOT ONLINE
# =========================

@bot.event
async def on_ready():

    print(
        f"Bot conectado como {bot.user}"
    )

    print(
        f"Canal configurado: {CHANNEL_ID}"
    )

    if not check_games.is_running():

        check_games.start()


# =========================
# INICIAR
# =========================

if not DISCORD_TOKEN:

    raise ValueError(
        "DISCORD_TOKEN não foi configurado."
    )


bot.run(DISCORD_TOKEN)
