import logging
import math
from alertbot.utils import config
from alertbot.alerts.base import Base
import threading
from datetime import datetime
import time
from discord_webhook import DiscordWebhook, DiscordEmbed
import investpy
import pandas as pd
import os

# Perhaps we could just pass to #BSND?
# Configure logging if not already configured elsewhere
logger = logging.getLogger(__name__)

class Economic(Base):
    def __init__(self, files):
        super().__init__(files=files)

    def send_alert(self):
        today = datetime.now()
        today_str = today.strftime('%m/%d/%Y')
        logger.debug(f" ECON | send_alert | Note: Fetching economic data for {today_str}...")

        try:
            calendar = investpy.news.economic_calendar(
                time_zone=None,
                time_filter='time_only',
                countries=['united states'],
                importances=['high', 'medium'],
                categories=None,
                from_date=None,  
                to_date=None
            )
            logger.debug(f" ECON | send_alert | Note: Economic calendar fetched successfully.")
            logger.debug(f" ECON | send_alert | Calendar Data: {calendar}")
        except Exception as e:
            logger.error(f" ECON | send_alert | Note: Error fetching economic calendar: {e}")
            return

        logger.debug(" ECON | send_alert | Note: Manipulating Dataframe")

        try:
            calendar_df = pd.DataFrame(calendar)
            logger.debug(" ECON | send_alert | Note: DataFrame created from calendar data.")
            logger.debug(f" ECON | send_alert | DataFrame Columns: {calendar_df.columns.tolist()}")
            logger.debug(f" ECON | send_alert | DataFrame Head:\n{calendar_df.head()}")
        except Exception as e:
            logger.error(f" ECON | send_alert | Note: Error creating DataFrame: {e}")
            return

        columns_to_keep = ['time', 'event', 'importance']
        logger.debug(f" ECON | send_alert | Columns to keep: {columns_to_keep}")

        # Check if required columns are present
        missing_columns = [col for col in columns_to_keep if col not in calendar_df.columns]
        if missing_columns:
            logger.error(f" ECON | send_alert | Missing columns in DataFrame: {missing_columns}")
            logger.debug(f" ECON | send_alert | Available columns: {calendar_df.columns.tolist()}")
            return
        else:
            logger.debug(" ECON | send_alert | All required columns are present.")

        # Proceed to select the columns
        try:
            calendar_df = calendar_df[columns_to_keep]
            logger.debug(" ECON | send_alert | Selected required columns from DataFrame.")
            logger.debug(f" ECON | send_alert | Filtered DataFrame Columns: {calendar_df.columns.tolist()}")
            logger.debug(f" ECON | send_alert | Filtered DataFrame Head:\n{calendar_df.head()}")
        except KeyError as e:
            logger.error(f" ECON | send_alert | KeyError while selecting columns: {e}")
            return
        except Exception as e:
            logger.error(f" ECON | send_alert | Unexpected error while selecting columns: {e}")
            return

        formatted_events = [self.format_event(row) for _, row in calendar_df.iterrows()]
        logger.debug(f" ECON | send_alert | Number of formatted events: {len(formatted_events)}")
        if not formatted_events:
            formatted_events = ["No significant events today."]
            logger.debug(" ECON | send_alert | No events found. Using default message.")

        discord_webhook_url = os.getenv('DISCORD_ECON_WEBHOOK')  # Adjust as per your Base class

        events_text = "\n".join(formatted_events)
        logger.debug(f" ECON | send_alert | Events text prepared for Discord.")

        # Build the Discord Embed
        try:
            embed_title = f":black_large_square: **Economic Events for {today_str}** :black_large_square:"
            embed = DiscordEmbed(
                title=embed_title,
                description=events_text,
                color=self.get_color()  
            )
            embed.set_timestamp()  

            embed.add_embed_field(name=":information_source: Note", value="`Control Risk and Trade Well!`", inline=False)

            # Send the embed with the webhook
            if discord_webhook_url:
                webhook = DiscordWebhook(url=discord_webhook_url, username=None)
                webhook.add_embed(embed)
                response = webhook.execute()
                if response.status_code == 200 or response.status_code == 204:
                    logger.info(f" ECON | send_alert | Note: Message sent to Discord webhook for economic events.")
                else:
                    logger.error(f" ECON | send_alert | Note: Failed to send message to Discord webhook | Status Code: {response.status_code}")
            else:
                logger.error(f" ECON | send_alert | Note: No Discord webhook URL configured.")
        except Exception as e:
            logger.error(f" ECON | send_alert | Error sending Discord message: {e}")
                
    def format_event(self, row):
        
        event_time = row.get('time', 'N/A')
        event_name = row.get('event', 'N/A')
        importance = row.get('importance', 'N/A').capitalize()

        logger.debug(f" ECON | format_event | Event Time: {event_time}, Event Name: {event_name}, Importance: {importance}")

        importance_emojis = {
            'High': ':red_circle:',
            'Medium': ':large_orange_diamond:',
            'Low': ':white_circle:'
        }
        
        importance_emoji = importance_emojis.get(importance, ':grey_question:')

        if importance == 'High':
            formatted_event = f"{importance_emoji}  **{event_time}** - {event_name}"
        else:
            formatted_event = f"{importance_emoji}  **{event_time}** - {event_name}"
        
        logger.debug(f" ECON | format_event | Formatted Event: {formatted_event}")
        return formatted_event
