import discord
import requests
import json
import os
import asyncio  # Import asyncio for creating delays
from config import API_KEY, GAME_NAME, TAG_LINE, REGION_PUUID, REGION_LEAGUE, DISCORD_TOKEN

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

# Load the last match ID
def load_last_match():
    if os.path.exists(LAST_MATCH_FILE):
        with open(LAST_MATCH_FILE, 'r') as f:
            return f.read().strip()
    return None

# Save the new match ID
def save_last_match(match_id):
    with open(LAST_MATCH_FILE, 'w') as f:
        f.write(match_id)

async def check_match(channel):
    # Step 1: Fetch PUUID
    puuid = get_puuid(GAME_NAME, TAG_LINE)

    if puuid:
        # Step 2: Fetch recent match ID
        last_match_id = load_last_match()
        recent_matches = get_recent_match_ids(puuid)

        if recent_matches:
            recent_match_id = recent_matches[0]

            if recent_match_id != last_match_id:
                # Step 3: Fetch match details
                match_details = get_match_details(recent_match_id)
                if match_details:
                    participant = next(p for p in match_details['info']['participants'] if p['puuid'] == puuid)
                    win = participant['win']
                    champion = participant['championName']
                    kills = participant['kills']
                    deaths = participant['deaths']
                    assists = participant['assists']

                    # Get the queue ID and map it to a game mode
                    queue_id = match_details['info']['queueId']
                    game_mode = QUEUE_ID_MAP.get(queue_id, "Unknown Mode")

                    # Create output message
                    message = "=== New Match Found ===\n"
                    message += f"Game Mode: {game_mode}\n"  # Add game mode to the message
                    message += f"Result: {'Win' if win else 'Loss'}\n"
                    message += f"Champion: {champion}\n"
                    message += f"KDA: {kills}/{deaths}/{assists}\n"
                    message += "========================"

                    # Send message to Discord channel
                    await channel.send(message)

                    # Step 4: Save the new match ID
                    save_last_match(recent_match_id)

                # Step 5: Fetch encrypted summoner ID
                encrypted_summoner_id = get_encrypted_summoner_id(puuid)

                if encrypted_summoner_id:
                    # Step 6: Fetch league entries
                    league_entries = get_league_entries(encrypted_summoner_id)

                    if league_entries:
                        # Prepare league message
                        league_message = ""
                        # Separate entries into solo and flex
                        solo_entry = None
                        flex_entry = None

                        for entry in league_entries:
                            # Check for Solo and Flex ranks
                            if entry['queueType'] == 'RANKED_SOLO_5x5':
                                solo_entry = entry
                            elif entry['queueType'] == 'RANKED_FLEX_SR':
                                flex_entry = entry

                        # Print Solo entry first
                        if solo_entry:
                            wins = solo_entry['wins']
                            losses = solo_entry['losses']
                            lp = solo_entry.get('leaguePoints', 0)  # Get LP if available

                            total_matches = wins + losses
                            win_rate = (wins / total_matches * 100) if total_matches > 0 else 0

                            league_message += f"soloq: {solo_entry['tier']} {solo_entry['rank']} {lp}LP, {wins}W/{losses}L, {win_rate:.2f}% Win Rate\n"

                        # Print Flex entry second
                        if flex_entry:
                            wins = flex_entry['wins']
                            losses = flex_entry['losses']
                            lp = flex_entry.get('leaguePoints', 0)  # Get LP if available

                            total_matches = wins + losses
                            win_rate = (wins / total_matches * 100) if total_matches > 0 else 0

                            league_message += f"flex: {flex_entry['tier']} {flex_entry['rank']} {lp}LP, {wins}W/{losses}L, {win_rate:.2f}% Win Rate\n"

                        await channel.send(league_message)

        # If no recent matches found, do nothing
    else:
        await channel.send("Unable to get PUUID.")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    channel = client.get_channel(1292776026178588806)
    
    while True:  # Create an infinite loop
        await check_match(channel)  # Check for new matches
        await asyncio.sleep(20)  # Wait for 60 seconds before checking again

# Replace 'your_token_here' with your Discord bot token
client.run(DISCORD_TOKEN)
