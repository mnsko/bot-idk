import discord
from discord import Embed
import requests
import json
import os
import asyncio
import time
from config import API_KEY, ACCOUNTS, REGION_PUUID, REGION_LEAGUE, DISCORD_TOKEN

# Set up Discord client
intents = discord.Intents.default()
intents.message_content = True
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

# Global variables for ranked stats update
last_update_time = 0
last_ranked_stats = None
UPDATE_INTERVAL = 60  # 60 seconds

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

# Load the last LP data for a specific account
def load_last_lp(game_name, tag_line):
    filename = f"{game_name}_{tag_line}_lp.txt"
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

# Save the LP data for a specific account
def save_last_lp(game_name, tag_line, lp_data):
    filename = f"{game_name}_{tag_line}_lp.txt"
    with open(filename, 'w') as f:
        json.dump(lp_data, f)

# Rank players by tier, division, and LP
def rank_players(league_entries):
    rank_order = {
        'CHALLENGER': 0, 'GRANDMASTER': 1, 'MASTER': 2, 'DIAMOND': 3,
        'EMERALD': 4, 'PLATINUM': 5, 'GOLD': 6, 'SILVER': 7, 'BRONZE': 8, 'IRON': 9
    }
    division_order = {'I': 0, 'II': 1, 'III': 2, 'IV': 3, 'V': 4}
    
    def rank_key(entry):
        if not entry:
            return (float('inf'), 0, 0)
        return (rank_order.get(entry['tier'], float('inf')),
                division_order.get(entry['rank'], 0),
                -entry['leaguePoints'])
    
    return sorted(league_entries, key=rank_key)

# Format ranked stats for display
def format_ranked_stats(ranked_players, queue_type):
    formatted = f"**{queue_type}**\n"
    for player in ranked_players:
        if player:
            formatted += f"{player['summonerName']}: **{player['tier']} {player['rank']} {player['leaguePoints']}LP**\n"
        else:
            # Find the corresponding account for this unranked player
            unranked_player = next((f"{name}#{tag}" for name, tag in ACCOUNTS if f"{name}#{tag}" not in [p['summonerName'] for p in ranked_players if p]), "Unknown Player")
            formatted += f"{unranked_player}: **Unranked**\n"
    return formatted.strip()

async def update_ranked_stats(channel):
    global last_update_time, last_ranked_stats
    current_time = time.time()
    
    if current_time - last_update_time < UPDATE_INTERVAL:
        return  # Skip update if not enough time has passed
    
    all_solo_entries = []
    all_flex_entries = []
    
    for game_name, tag_line in ACCOUNTS:
        puuid = get_puuid(game_name, tag_line)
        if puuid:
            encrypted_summoner_id = get_encrypted_summoner_id(puuid)
            if encrypted_summoner_id:
                league_entries = get_league_entries(encrypted_summoner_id)
                solo_entry = next((entry for entry in league_entries if entry['queueType'] == 'RANKED_SOLO_5x5'), None)
                flex_entry = next((entry for entry in league_entries if entry['queueType'] == 'RANKED_FLEX_SR'), None)

                last_lp_data = load_last_lp(game_name, tag_line)
                
                if solo_entry:
                    solo_entry['summonerName'] = f"{game_name}#{tag_line}"
                    all_solo_entries.append(solo_entry)
                    
                    # Compare LP for Solo Queue
                    last_solo_lp = last_lp_data.get('solo', {}).get('lp', None)
                    if last_solo_lp is not None and last_solo_lp != solo_entry['leaguePoints']:
                            # LP has changed, but no message is sent
                            pass
                    
                    last_lp_data['solo'] = {
                        'lp': solo_entry['leaguePoints']
                    }
                else:
                    all_solo_entries.append(None)

                if flex_entry:
                    flex_entry['summonerName'] = f"{game_name}#{tag_line}"
                    all_flex_entries.append(flex_entry)
                    
                    # Compare LP for Flex Queue
                    last_flex_lp = last_lp_data.get('flex', {}).get('lp', None)
                    if last_flex_lp is not None and last_flex_lp != flex_entry['leaguePoints']:
                        # LP has changed, but no message is sent
                        pass
                    
                    last_lp_data['flex'] = {
                        'lp': flex_entry['leaguePoints']
                    }
                else:
                    all_flex_entries.append(None)
                
                # Save the updated LP data
                save_last_lp(game_name, tag_line, last_lp_data)
    
    ranked_solo = rank_players(all_solo_entries)
    ranked_flex = rank_players(all_flex_entries)
    
    new_ranked_stats = (format_ranked_stats(ranked_solo, "Solo/Duo Queue"), 
                        format_ranked_stats(ranked_flex, "Flex Queue"))
    
    if new_ranked_stats != last_ranked_stats:
        embed = Embed(title="Ranked Stats", color=discord.Color.blue())
        embed.add_field(name="Solo/Duo Queue", value=new_ranked_stats[0], inline=False)
        embed.add_field(name="Flex Queue", value=new_ranked_stats[1], inline=False)
        
        # Find and edit the existing message, or send a new one if not found
        async for message in channel.history(limit=10):
            if message.author == client.user and message.embeds and message.embeds[0].title == "Ranked Stats":
                await message.edit(embed=embed)
                break
        else:
            await channel.send(embed=embed)
        
        last_ranked_stats = new_ranked_stats
    
    last_update_time = current_time

async def check_match(channel, game_name, tag_line):
    puuid = get_puuid(game_name, tag_line)

    if puuid:
        last_match_id = load_last_match(game_name, tag_line)
        recent_match_ids = get_recent_match_ids(puuid)
        
        if recent_match_ids:
            recent_match_id = recent_match_ids[0]

            if last_match_id != recent_match_id:
                match_details = get_match_details(recent_match_id)

                if match_details:
                    participant = next(p for p in match_details['info']['participants'] if p['puuid'] == puuid)
                    game_mode = QUEUE_ID_MAP.get(match_details['info']['queueId'], "Unknown")

                    if game_mode in ["Ranked Solo", "Ranked Flex"]:
                        win_or_loss = "won" if participant['win'] else "lost"
                        champ_name = participant['championName']
                        score = f"{participant['kills']}/{participant['deaths']}/{participant['assists']}"
                        
                        # Create an embed for the message
                        embed = discord.Embed(title=f"New Match for {game_name}#{tag_line}", color=discord.Color.green() if participant['win'] else discord.Color.red())
                        embed.add_field(name="Game Mode", value=game_mode, inline=False)
                        embed.add_field(name="Result", value="Victory" if participant['win'] else "Defeat", inline=True)
                        embed.add_field(name="Champion", value=champ_name, inline=True)
                        embed.add_field(name="KDA", value=score, inline=True)
                        embed.add_field(name="Duration", value=f"{match_details['info']['gameDuration'] // 60}m {match_details['info']['gameDuration'] % 60}s", inline=True)
                        embed.add_field(name="Farm (CS)", value=str(participant['totalMinionsKilled'] + participant['neutralMinionsKilled']), inline=True)
                        
                        await channel.send(embed=embed)

                    # Save the new match ID
                    save_last_match(game_name, tag_line, recent_match_id)
            else:
                print(f"No new match for {game_name}#{tag_line}")
        else:
            print(f"No matches found for {game_name}#{tag_line}")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    match_channel = client.get_channel(1292916252712636506)  # Channel ID where will be new matches
    ranked_channel = client.get_channel(1292916197754404884) # Channel ID where is the ranks of players

    while True:
        for game_name, tag_line in ACCOUNTS:
            await check_match(match_channel, game_name, tag_line)
        await update_ranked_stats(ranked_channel)
        await asyncio.sleep(60)  # Check every 60 seconds

client.run(DISCORD_TOKEN)
