import logging
import math
from datetime import datetime
from alertbot.utils import config
from alertbot.alerts.base import Base
from discord_webhook import DiscordEmbed, DiscordWebhook
import threading
import re
logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class SWING_BIAS(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables
        self.es_bias = config.es_swing_bias
        self.nq_bias = config.nq_swing_bias
        self.rty_bias = config.rty_swing_bias
        self.cl_bias = config.cl_swing_bias
        self.cpl = round(self.variables.get(f'{self.product_name}_CPL'), 2)
        
# ---------------------------------- Driving Input Logic ------------------------------------ #         
    def input(self):
        
        self.bias_string = ''
        if self.product_name == 'ES':
            self.bias_string = self.es_bias
        elif self.product_name == 'NQ':
            self.bias_string = self.nq_bias
        elif self.product_name == 'RTY':
            self.bias_string = self.rty_bias
        elif self.product_name == 'CL':
            self.bias_string = self.cl_bias
        
        self.price = None
        self.bias_char = ''
        if self.bias_string:
            self.bias_string = self.bias_string.strip()
            match = re.match(r'^([0-9]*\.?[0-9]+)([^\d\.]*)$', self.bias_string)
            if match:
                self.price_str = match.group(1)
                self.bias_char = match.group(2).strip()
                try:
                    self.price = float(self.price_str)
                except ValueError:
                    self.price = None
            else:
                try:
                    self.price = float(self.bias_string)
                    self.bias_char = ''
                except ValueError:
                    self.price = None
                    self.bias_char = ''
        else:
            self.price = None
            self.bias_char = ''
            
        self.bias_condition = False 
        if self.price is not None and self.bias_char:
            if self.bias_char.lower() == 'v':
                self.bias_condition = self.cpl > self.price
                self.direction = "above"
            elif self.bias_char == '^':
                self.bias_condition = self.cpl < self.price
                self.direction = "below"
            else:
                self.bias_condition = False
                self.direction = None
        else:
            pass

        logic = (
            self.bias_condition
        )    

        logger.debug(
            f" SWING | input | Product: {self.product_name} | Bias_Symbol: {self.bias_char} | Bias_Price: {self.price} | Last_Price: {self.cpl} | LOGIC: {logic}"
        )
        
        return logic
# ---------------------------------- Opportunity Window ------------------------------------ #   
    def time_window(self):
        
        # Update current time
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
        
        # Define time windows based on product type
        if self.product_name == 'CL':
            start_time = self.crude_open
            end_time = self.crude_close
            logger.debug(f" SWING | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_open
            end_time = self.equity_close
            logger.debug(f" SWING | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f" SWING | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        
        # Check if current time is within the window
        if start_time <= self.current_time <= end_time:
            logger.debug(f" SWING | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" SWING | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False   
# ---------------------------------- Main Function ------------------------------------ #                  
    def check(self):
        
        # Driving Input
        if self.input() and self.time_window():
            
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)   
                current_date = datetime.now().date()
                logger.debug(f" SWING | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                
                if last_alert != current_date: 
                    logger.info(f" SWING | check | Product: {self.product_name} | Note: Condition Met")
                    try:
                        last_alerts[self.product_name] = current_date
                        self.execute()
                    except Exception as e:
                        logger.error(f" SWING | check | Product: {self.product_name} | Note: Failed to send Discord alert: {e}")
                else:
                    logger.debug(f" SWING | check | Product: {self.product_name} | Note: Alert Already Sent Today")
        else:
            logger.debug(f" SWING | check | Product: {self.product_name} | Note: Condition Not Met Or No Bias")
# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):
        
        color_name = self.product_color.get(self.product_name, ":black_large_square:") 
        
        direction_settings = {
            "above": {
                "text": "Above",
            },
            "below": {
                "text": "Below",
            }
        }

        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" SWING | discord_message | Note: Invalid direction '{self.direction}'")

        # Title Construction with Emojis
        title = f"{color_name} **{self.product_name} - Context Alert - Bias Violation**"

        embed = DiscordEmbed(
            title=title,
            description=(
                f"> :warning:   **SWING BIAS CHALLENGED**    :warning:\n"
                f"- Price Trading {settings['text']} **{self.price}**!"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()  # Automatically sets the timestamp to current time

        return embed 
    
    def execute(self):
        
        embed = self.discord_message()
        
        try:
            # Send the embed using the alert webhook
            self.send_alert_embed(embed, username=None, avatar_url=None)
            logger.info(f" SWING | execute | Product: {self.product_name} | Note: Alert Sent To Discord Webhook")
        except Exception as e:
            logger.error(f" SWING | execute | Product: {self.product_name} | Note: Error sending Discord message: {e}")