import discord
from discord.ext import commands, tasks
import pandas as pd
import asyncio
import os
import json
import datetime
from typing import List, Dict
import hashlib
from pathlib import Path
import yaml

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

with open('bot_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

#change these values in bot_config.yaml
TOKEN = os.getenv('DISCORD_TOKEN')
STATUS_CHANNEL_ID = config['bot']['status']  # Channel for status/logs
DATA_CHANNEL_ID = config['bot']['data']  # Channel for CSV data embeds
timespan = config['bot']['period']

minimum_quantity = config['filter']['quantity']
maximum_date = config['filter']['date']

special_quantity = config['special']['quantity']
special_date = config['special']['date']


if os.getenv('DATA'):
    DATA_CHANNEL_ID = os.getenv('DATA')
    if not os.getenv('STATUS'):
        STATUS_CHANNEL_ID = DATA_CHANNEL_ID

if os.getenv('STATUS'):
    STATUS_CHANNEL_ID = os.getenv('STATUS')
    if not os.getenv('DATA'):
        DATA_CHANNEL_ID = STATUS_CHANNEL_ID

if STATUS_CHANNEL_ID is None:
    STATUS_CHANNEL_ID = DATA_CHANNEL_ID
if DATA_CHANNEL_ID is None:
    DATA_CHANNEL_ID = STATUS_CHANNEL_ID



# File Paths
CSV_PATH = Path("data/insider_trades.csv")
PERSISTENCE_FILE = Path("data/processed_trades.json")

if not os.path.exists("data"):
    os.makedirs("data")

# -------------------------------------------------------------------------
# Data Processing Helpers
# -------------------------------------------------------------------------

def clean_currency(value) -> float:
    """Removes symbols (+, $, %, ,) and converts to float."""
    if isinstance(value, str):
        cleaned = value.replace('$', '').replace(',', '').replace('+', '').replace('%', '')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return float(value) if value else 0.0


def generate_trade_id(row) -> str:
    """Generates a unique string ID for a trade based on its content."""
    raw_str = f"{row['transaction_date']}{row['ticker']}{row['owner_name']}{row['Qty']}{row['Value']}"
    return hashlib.sha256(raw_str.encode()).hexdigest()


def load_persistence() -> List[str]:
    """Loads list of processed trade IDs."""
    if not os.path.exists(PERSISTENCE_FILE):
        return []
    try:
        with open(PERSISTENCE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_persistence(processed_ids: List[str]):
    """Saves processed trade IDs to file."""
    with open(PERSISTENCE_FILE, 'w') as f:
        json.dump(processed_ids, f)


def get_data() -> pd.DataFrame:
    """Reads CSV, cleans data types, and returns DataFrame."""
    if not os.path.exists(CSV_PATH):
        channel = asyncio.run(bot.get_channel(STATUS_CHANNEL_ID))
        asyncio.run(channel.send("Can't find csv file"))
        return pd.DataFrame()

    try:
        df = pd.read_csv(CSV_PATH)

        # Ensure required columns exist
        required_cols = ['trade_date', 'Qty', 'Value', 'last_price', 'transaction_date']
        if not all(col in df.columns for col in required_cols):
            return pd.DataFrame()

        # Clean numerical columns
        df['clean_qty'] = df['Qty'].apply(clean_currency)
        df['clean_value'] = df['Value'].apply(clean_currency)
        df['clean_price'] = df['last_price'].apply(clean_currency)

        # Convert dates
        df['trade_date_dt'] = pd.to_datetime(df['trade_date'], errors='coerce')

        return df
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return pd.DataFrame()


# -------------------------------------------------------------------------
# Bot Setup
# -------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# State management
bot.scanner_running = False

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print("enter !start to start scraping")


# -------------------------------------------------------------------------
# Embed Builder
# -------------------------------------------------------------------------

def create_trade_embed(row, is_special: bool) -> discord.Embed:
    """Formats the DataFrame row into the specific Discord Embed requested."""

    # Calculate days ago
    days_ago = "N/A"
    if pd.notnull(row['trade_date_dt']):
        delta = datetime.datetime.now() - row['trade_date_dt']
        days_ago = str(delta.days)

    color = discord.Color.gold() if is_special else discord.Color.blue()

    ticker_display = f"**{row['ticker']}**" if is_special else row['ticker']

    embed = discord.Embed(
        title=ticker_display,
        description=row['company_name'],
        color=color
    )

    # Row 1
    embed.add_field(name="Trade Date", value=str(row['trade_date']), inline=True)
    embed.add_field(name="Days Ago", value=days_ago, inline=True)
    embed.add_field(name="Type", value=str(row['transaction_type']), inline=True)

    # Row 2
    insider_info = f"{row['owner_name']}\n({row['Title']})"
    embed.add_field(name="Insider", value=insider_info, inline=True)

    qty_val = row['Qty']
    if is_special:
        qty_val = f"**{qty_val}**"
    embed.add_field(name="Quantity", value=qty_val, inline=True)

    embed.add_field(name="Price", value=str(row['last_price']), inline=True)

    # Row 3
    embed.add_field(name="Value", value=str(row['Value']), inline=True)
    embed.add_field(name="Shares Held", value=str(row['shares_held']), inline=True)

    # Calculate ownership change if possible, else default to 0% or usage of Owned column if exists
    # Using 'Owned' from CSV header provided in prompt
    owned_change = row['Owned'] if 'Owned' in row else "N/A"
    embed.add_field(name="Ownership Change", value=str(owned_change), inline=True)

    return embed


# -------------------------------------------------------------------------
# Core Logic
# -------------------------------------------------------------------------


@tasks.loop(minutes=timespan)
async def scanner_loop(force=False) -> None:
    """Background task logic. Force for ignoring history file"""

    await bot.wait_until_ready()
    status_channel = bot.get_channel(STATUS_CHANNEL_ID)
    data_channel = bot.get_channel(DATA_CHANNEL_ID)

    try:
        # 1. Run Scraper
        await asyncio.create_subprocess_shell('python3 openinsider_scraper.py')

        # 2. Load Data
        df = get_data()
        processed_ids = load_persistence()
        new_processed_ids = list(processed_ids)

        if df.empty:
            await status_channel.send("CSV is empty or not found. Retrying in 30 mins.")
        else:
            # 3. Filter Logic
            now = datetime.datetime.now()

            # Base Filter: Last 5 days AND Qty > 20,000
            mask_date = (now - df['trade_date_dt']).dt.days <= maximum_date
            mask_qty = df['clean_qty'] > minimum_quantity
            filtered_df = df[mask_date & mask_qty]

            for index, row in filtered_df.iterrows():
                trade_id = generate_trade_id(row)

                # Check persistence
                if trade_id in new_processed_ids and not force:
                    continue

                # Special Logic
                # Special if: <= 2 days ago OR Qty > 300,000
                days_diff = (now - row['trade_date_dt']).days
                is_special = (days_diff <= special_date) or (row['clean_qty'] > special_quantity)

                # Send Embed
                embed = create_trade_embed(row, is_special)
                await data_channel.send(embed=embed)

                new_processed_ids.append(trade_id)

            # Update persistence
            save_persistence(new_processed_ids)

            print('Scanner loop completed')

    except Exception as e:
        status_channel.send(f"Error: {e}")


# -------------------------------------------------------------------------
# Commands
# -------------------------------------------------------------------------

@bot.command(name='start')
async def start_scanner(ctx):
    """Starts the background scanning task."""
    if bot.scanner_running:
        await ctx.send("Scanner is already running.")
        return
    bot.scanner_running = True
    await scanner_loop.start()

    # Respond in the Status Channel (or ctx if matches)
    status_channel = bot.get_channel(STATUS_CHANNEL_ID)
    if status_channel:
        await status_channel.send("Scanner started via command.")

@bot.command(name="stop")
async def stop(ctx):
    try:
        bot.scanner_running = False
        await scanner_loop.stop()

        ctx.send('Scanner stopped')
    except Exception as e:
        await ctx.send(f"Scanner was already off, probably {e}")

@bot.command(name='status')
async def status_scanner(ctx):
    """Checks if the scanner loop is running."""

    state = "Running" if bot.scanner_running else "Stopped"
    await ctx.send(f"Scanner Status: {state}")


@bot.command(name='force')
async def force_scanner(ctx):
    """Forces the scanner to output something."""
    try:
        if bot.scanner_running:
            await scanner_loop.stop()

        await scanner_loop(force=True)
        await ctx.send('Forced scan complete')
    except:
        pass

@bot.command(name='today')
async def today_trades(ctx):
    """Returns trades where trade_date is today. Ignores persistence."""
    df = get_data()
    if df.empty:
        await ctx.send("No data available.")
        return

    now_str = datetime.datetime.now().strftime('%Y-%m-%d')
    # Filter for exact string match on date or datetime match
    today_df = df[df['trade_date'] == now_str]

    if today_df.empty:
        await ctx.send("No trades found for today.")
        return

    await ctx.send(f"Found {len(today_df)} trades for {now_str}:")

    # Send to Data Channel to keep format
    data_channel = bot.get_channel(DATA_CHANNEL_ID)
    for index, row in today_df.iterrows():
        # Calculate special just for formatting purposes
        days_diff = 0
        is_special = (days_diff <= 2) or (row['clean_qty'] > 300000)
        embed = create_trade_embed(row, is_special)
        await data_channel.send(embed=embed)
    else:
        await ctx.send("Data channel not configured correctly.")


@bot.command(name='analysis')
async def analysis_top_three(ctx):
    """Scores and returns top 3 stocks from data."""
    df = get_data()

    if df.empty:
        await ctx.send("No data available for analysis.")
        return

    # Scoring Algorithm
    # Recency: Higher weight (inverse of days ago)
    # Quantity: Medium weight
    # Value: Low weight

    now = datetime.datetime.now()

    def calculate_score(row):
        # Days ago (add 1 to avoid division by zero)
        days = (now - row['trade_date_dt']).days
        days = max(0, days)  # Ensure no negative
        recency_score = (1 / ((days - 1) + 1)) * 10000

        qty_score = row['clean_qty'] * 0.01
        value_score = row['clean_value'] * 0.001

        return recency_score + qty_score + value_score

    # Create a copy to avoid SettingWithCopy warnings
    analysis_df = df.copy()
    analysis_df['score'] = analysis_df.apply(calculate_score, axis=1)

    # Sort and take top 3
    top_3 = analysis_df.sort_values(by='score', ascending=False).head(3)

    if top_3.empty:
        await ctx.send("Not enough data to perform analysis.")
        return

    response = "**Top 3 Analyzed Trades**\n"
    response += "Criteria: Recency (High), Qty (Med), Value (Low)\n\n"

    for i, (index, row) in enumerate(top_3.iterrows(), 1):
        response += (
            f"{i}. **{row['ticker']}** | Date: {row['trade_date']} | "
            f"Qty: {row['Qty']} | Val: {row['Value']}\n"
        )

    await ctx.send(response)


# -------------------------------------------------------------------------
# Run Bot
# -------------------------------------------------------------------------

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables.")
    else:
        bot.run(TOKEN)
