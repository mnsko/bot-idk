# League of Legends Discord Bot

This Discord bot tracks League of Legends matches and ranked stats for specified accounts, providing updates in designated Discord channels.

## Features

- Tracks recent matches for specified League of Legends accounts
- Posts match results for ranked games in a designated Discord channel
- Updates and displays ranked stats for tracked accounts
- Supports multiple regions and queue types

## Requirements

- Python 3.7+
- discord.py library
- requests library

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/MNSKcze/bot-idk
   cd bot-idk
   ```

2. Install the required packages:
   ```
   pip install discord.py requests
   ```

3. Edit a config.py file
   ```python
   API_KEY = "YOUR_RIOT_API_KEY"
   ACCOUNTS = [
       ("Nickname1", "GameTag1"),
       ("Nickname2", "GameTag2"),
       # Add more accounts as needed
   ]
   REGION_PUUID = "europe"  # Region for getting PUUID
   REGION_LEAGUE = "eun1"   # Region for getting encrypted IDs
   DISCORD_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
   ```

   Replace `YOUR_RIOT_API_KEY` with your Riot Games API key and `YOUR_DISCORD_BOT_TOKEN` with your Discord bot token.
   Replace `europe` and `eun1` with your regions.

## Configuration

- In the main script, set the channel IDs for match updates and ranked stats:
  ```python
  match_channel = client.get_channel(MATCH_CHANNEL_ID)
  ranked_channel = client.get_channel(RANKED_CHANNEL_ID)
  ```
  Replace `MATCH_CHANNEL_ID` and `RANKED_CHANNEL_ID` with the appropriate Discord channel IDs.

## Usage

Run the bot using:

```
python main.py
```

The bot will start tracking matches and updating ranked stats for the specified accounts.

## Features

- **Match Tracking**: Posts embed messages for new ranked matches played by tracked accounts.
- **Ranked Stats**: Periodically updates and displays ranked stats for all tracked accounts.
- **Multi-Account Support**: Can track multiple League of Legends accounts simultaneously.
- **Flexible Configuration**: Easily configurable for different regions and accounts.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Disclaimer

This bot isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing League of Legends. League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc. League of Legends © Riot Games, Inc.