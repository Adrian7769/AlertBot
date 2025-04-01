import os
import logging
from discord_webhook import DiscordWebhook
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from typing import Optional

load_dotenv()
logger = logging.getLogger(__name__)

class Base:
    def __init__(self, product_name: Optional[str] = None, variables: Optional[str] = None, files: Optional[str] = None):
        self.discord_webhooks_playbook = {
            'ES': os.getenv("DISCORD_PLAYBOOK_ES_WEBHOOK"),
            'NQ': os.getenv("DISCORD_PLAYBOOK_NQ_WEBHOOK"),
            'RTY': os.getenv("DISCORD_PLAYBOOK_RTY_WEBHOOK"),
            'CL': os.getenv("DISCORD_PLAYBOOK_CL_WEBHOOK")
        }
        self.discord_webhooks_alert = {
            'ES': os.getenv("DISCORD_CONTEXT_ES_WEBHOOK"),
            'NQ': os.getenv("DISCORD_CONTEXT_NQ_WEBHOOK"),
            'RTY': os.getenv("DISCORD_CONTEXT_RTY_WEBHOOK"),
            'CL': os.getenv("DISCORD_CONTEXT_CL_WEBHOOK")
        }
        self.discord_webhooks_preps = {
            'ES': os.getenv("DISCORD_PREP_ES_WEBHOOK"),
            'NQ': os.getenv("DISCORD_PREP_NQ_WEBHOOK"),
            'RTY': os.getenv("DISCORD_PREP_RTY_WEBHOOK"),
            'CL': os.getenv("DISCORD_PREP_CL_WEBHOOK"),
            'QuickSheet': os.getenv("DISCORD_QUICKSHEET_WEBHOOK")
        }
        self.product_color = {
            'ES': "blue",   
            'NQ': "green",  
            'RTY': "orange",  
            'CL': "purple",   
            'QuickSheet': "black",
        }
        self.product_name = product_name
        self.variables = variables
        self.files = files
        
        # TimeZone Setup
        self.est = ZoneInfo('America/New_York')
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
        
        # Time Regulations for Equity Products
        self.equity_open = time(9, 30) 
        self.equity_ib = time(10, 30)
        self.equity_lunch_start = time(12, 00)
        self.equity_lunch_end = time(14, 00)
        self.equity_close = time(16, 00)

        # Time Regulations for Crude 
        self.crude_open = time(9, 00)
        self.crude_ib = time(10, 00)       
        self.crude_close = time(14, 30) 
        
        # Custom Time Regulations for Playbook
        self.crude_pvat_start = time(9, 2)
        self.equity_pvat_start = time(9, 32)
        self.crude_dogw_start = time(9, 10)
        self.equity_dogw_start = time(9, 40)

    def fetch_latest_variables(self, product_name):
        from alertbot.source.startup import Initialization
        all_variables = Initialization.prep_data(self.files)
        return all_variables.get(product_name)

    def send_discord_embed(self, webhook_url, embed, username=None, avatar_url=None):
        if webhook_url:
            try:
                webhook = DiscordWebhook(url=webhook_url, username=username, avatar_url=avatar_url)
                webhook.add_embed(embed)
                response = webhook.execute()
                logger.info(f"Message sent to Discord webhook: {webhook_url} | Response Code: {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to send message to Discord webhook: {e}")
        else:
            logger.warning(f"No Discord webhook URL configured for the product '{self.product_name}'.")

    def send_discord_embed_with_file(self, webhook_url, embed, file_path, username=None, avatar_url=None):
        if webhook_url:
            try:
                webhook = DiscordWebhook(url=webhook_url, username=username, avatar_url=avatar_url)
                webhook.add_embed(embed)
                with open(file_path, "rb") as f:
                    webhook.add_file(file=f.read(), filename=os.path.basename(file_path))
                response = webhook.execute()
                logger.info(f"Embed with file sent to Discord webhook: {webhook_url} | Response Code: {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to send embed with file to Discord webhook: {e}")
        else:
            logger.warning(f"No Discord webhook URL configured for the product '{self.product_name}'.")

    # Updated send_playbook_embed accepts an optional product_name parameter.
    def send_playbook_embed(self, embed, product_name: Optional[str] = None, username=None, avatar_url=None):
        prod = product_name if product_name is not None else self.product_name
        logger.debug(f"Product name for playbook embed: {prod}")
        webhook_url = self.discord_webhooks_playbook.get(prod)
        if webhook_url:    
            logger.debug(f"Webhook for playbook embed: {webhook_url}")
            self.send_discord_embed(webhook_url, embed, username=username, avatar_url=avatar_url)
        else:
            logger.error(f"No Discord Webhook Configured for {prod}")

    # Updated send_alert_embed accepts an optional product_name parameter.
    def send_alert_embed(self, embed, product_name: Optional[str] = None, username=None, avatar_url=None):
        prod = product_name if product_name is not None else self.product_name
        logger.debug(f"Product name for alert embed: {prod}")
        webhook_url = self.discord_webhooks_alert.get(prod)
        if webhook_url:
            logger.debug(f"Webhook for alert embed: {webhook_url}")
            self.send_discord_embed(webhook_url, embed, username=username, avatar_url=avatar_url)
        else:
            logger.error(f"No Discord Webhook Configured for {prod}")

    def get_color(self, product_name: Optional[str] = None):
        prod = product_name if product_name is not None else self.product_name        
        color_mapping = {
            "blue": 0x3498db,
            "green": 0x2ecc71,
            "orange": 0xE67E22,
            "purple": 0x9B59B6,
            "black": 0x000000
        }
        color_name = self.product_color.get(prod, "black").lower()
        return color_mapping.get(color_name, 0x000000)
