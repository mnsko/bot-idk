import discord
from discord import Embed
import requests
import json
import os
import asyncio  # Import asyncio for creating delays
from config import API_KEY, ACCOUNTS, REGION_PUUID, REGION_LEAGUE, DISCORD_TOKEN

LAST_MATCH_FILE = 'last_match.txt'

# Set up Discord client
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Queue ID mapping to game mode
QUEUE_ID_MAP = {
    420: "Ranked Solo",
    440: "Ranked Flex",
    450: "ARAM",
    400: "Normal Draft",
    430: "Normal Blind",
    # Add more queueId mappings as needed
}

# Step 1: Get PUUID using Riot ID
def get_puuid(game_name, tag_line):
    url = f"https://{REGION_PUUID}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}?api_key={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['puuid']
    else:
        print(f"Error getting PUUID: {response.json()}")
        return None

# Step 2: Get recent match IDs using PUUID
def get_recent_match_ids(puuid):
    match_url = f"https://{REGION_PUUID}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1&api_key={API_KEY}"
    response = requests.get(match_url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting recent match IDs: {response.json()}")
        return []

# Step 3: Get encrypted summoner ID using PUUID
def get_encrypted_summoner_id(puuid):
    summoner_url = f"https://{REGION_LEAGUE}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={API_KEY}"
    response = requests.get(summoner_url)
    if response.status_code == 200:
        return response.json()['id']
    else:
        print(f"Error getting encrypted summoner ID: {response.json()}")
        return None

# Step 4: Get league entries using encrypted summoner ID
def get_league_entries(summoner_id):
    league_url = f"https://{REGION_LEAGUE}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={API_KEY}"
    response = requests.get(league_url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting league entries: {response.json()}")
        return []

# Step 5: Get match details
def get_match_details(match_id):
    match_url = f"https://{REGION_PUUID}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"
    response = requests.get(match_url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting match details: {response.json()}")
        return None

# Load the last match ID for a specific account
def load_last_match(game_name, tag_line):
    filename = f"{game_name}_{tag_line}.txt"
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return f.read().strip()
    return None

# Save the new match ID for a specific account
def save_last_match(game_name, tag_line, match_id):
    filename = f"{game_name}_{tag_line}.txt"
    with open(filename, 'w') as f:
        f.write(match_id)

async def check_match(channel, game_name, tag_line):
    puuid = get_puuid(game_name, tag_line)

    if puuid:
        last_match_id = load_last_match(game_name, tag_line)
        recent_matches = get_recent_match_ids(puuid)

        if recent_matches:
            recent_match_id = recent_matches[0]

            if recent_match_id != last_match_id:
                match_details = get_match_details(recent_match_id)
                if match_details:
                    participant = next(p for p in match_details['info']['participants'] if p['puuid'] == puuid)
                    win = participant['win']
                    champion = participant['championName']
                    kills = participant['kills']
                    deaths = participant['deaths']
                    assists = participant['assists']
                    match_duration = match_details['info']['gameDuration']
                    farm = participant['totalMinionsKilled']
                    queue_id = match_details['info']['queueId']
                    game_mode = QUEUE_ID_MAP.get(queue_id, "Unknown Mode")

                    # Create an embed for the match details
                    embed = Embed(title=f"New Match for {game_name}#{tag_line}", color=discord.Color.green() if win else discord.Color.red())
                    embed.add_field(name="Game Mode", value=game_mode, inline=False)
                    embed.add_field(name="Result", value="Victory" if win else "Defeat", inline=True)
                    embed.add_field(name="Champion", value=champion, inline=True)
                    embed.add_field(name="KDA", value=f"{kills}/{deaths}/{assists}", inline=True)
                    embed.add_field(name="Duration", value=f"{match_duration // 60}m {match_duration % 60}s", inline=True)
                    embed.add_field(name="Farm (CS)", value=str(farm), inline=True)

                    # Send the embed to Discord channel
                    await channel.send(embed=embed)

                    # Save the new match ID
                    save_last_match(game_name, tag_line, recent_match_id)

                # Fetch and send league entries
                encrypted_summoner_id = get_encrypted_summoner_id(puuid)
                if encrypted_summoner_id:
                    league_entries = get_league_entries(encrypted_summoner_id)
                    if league_entries:
                        league_embed = Embed(title=f"Ranked Stats for {game_name}#{tag_line}", color=discord.Color.blue())
                        
                        for entry in league_entries:
                            queue_type = "Solo/Duo" if entry['queueType'] == 'RANKED_SOLO_5x5' else "Flex"
                            wins = entry['wins']
                            losses = entry['losses']
                            total_matches = wins + losses
                            win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
                            
                            league_embed.add_field(
                                name=f"{queue_type} Queue",
                                value=f"{entry['tier']} {entry['rank']} {entry['leaguePoints']}LP\n"
                                      f"W/L: {wins}/{losses}\n"
                                      f"Win Rate: {win_rate:.2f}%",
                                inline=False
                            )
                        
                        await channel.send(embed=league_embed)

    else:
        await channel.send(f"Unable to get PUUID for {game_name}#{tag_line}.")


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    channel = client.get_channel(1292776026178588806)

    while True:  # Create an infinite loop
        for game_name, tag_line in ACCOUNTS:
            await check_match(channel, game_name, tag_line)  # Check for new matches for each account
        await asyncio.sleep(20)  # Wait before checking again

client.run(DISCORD_TOKEN)