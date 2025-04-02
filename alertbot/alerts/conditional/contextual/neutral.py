import logging
import threading
from datetime import datetime
from alertbot.alerts.base import Base
from discord_webhook import DiscordEmbed
logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class NEUTRAL(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables (Round All Variables)
        self.cpl = round(self.variables.get(f'{self.product_name}_CPL'), 2)
        self.ib_high = round(self.variables.get(f'{product_name}_IB_HIGH'), 2)
        self.ib_low = round(self.variables.get(f'{product_name}_IB_LOW'), 2)
        self.day_high = round(self.variables.get(f'{product_name}_DAY_HIGH'), 2)
        self.day_low = round(self.variables.get(f'{product_name}_DAY_LOW'), 2)
        
# ---------------------------------- Driving Input Logic ------------------------------------ #      
    def input(self, last_state):

        # Initialize variables to keep track of alerts
        has_alerted_neutral_lower = last_state.get('has_alerted_neutral_lower', False)
        has_alerted_neutral_higher = last_state.get('has_alerted_neutral_higher', False)

        self.neutral_type = None

        # Check if both IBH and IBL have been extended
        if self.day_high > self.ib_high and self.day_low < self.ib_low:
            # Both sides have been extended, do not send an alert
            logger.debug(f" NEUTRAL | input | Product: {self.product_name} | Note: Both IBH and IBL have been extended, no alert will be sent")
            return False

        logic = False

        # Check for Neutral Lower scenario
        if self.day_high > self.ib_high and not has_alerted_neutral_lower:
            if self.cpl < self.ib_low:
                logic = True
                self.neutral_type = 'Lower'
                last_state['has_alerted_neutral_lower'] = True
                logger.debug(f" NEUTRAL | input | Product: {self.product_name} | Note: Neutral Lower detected")

        # Check for Neutral Higher scenario
        elif self.day_low < self.ib_low and not has_alerted_neutral_higher:
            if self.cpl > self.ib_high:
                logic = True
                self.neutral_type = 'Higher'
                last_state['has_alerted_neutral_higher'] = True
                logger.debug(f" NEUTRAL | input | Product: {self.product_name} | Note: Neutral Higher detected")

        return logic
# ---------------------------------- Opportunity Window ------------------------------------ #   
    def time_window(self):
        
        # Update current time
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
        
        # Define time windows based on product type
        if self.product_name == 'CL':
            start_time = self.crude_ib
            end_time = self.crude_close
            logger.debug(f" NEUTRAL | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_ib
            end_time = self.equity_close
            logger.debug(f" NEUTRAL | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f" NEUTRAL | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        
        # Check if current time is within the window
        if start_time <= self.current_time <= end_time:
            logger.debug(f" NEUTRAL | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" NEUTRAL | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False
# ---------------------------------- Main Function ------------------------------------ #      
    def check(self):
        logic = False

        with last_alerts_lock:
            # Retrieve or initialize the last state
            last_state = last_alerts.get(self.product_name)
            if last_state is None:
                last_state = {
                    'has_alerted_neutral_lower': False,
                    'has_alerted_neutral_higher': False
                }
                last_alerts[self.product_name] = last_state
                logger.debug(f" NEUTRAL | check | Product: {self.product_name} | Note: Initialized last_state")

            # Evaluate the input
            logic = self.input(last_state)

            # Update the last state
            last_alerts[self.product_name] = last_state

        if logic and self.time_window():
            try:
                self.execute()
            except Exception as e:
                logger.error(f" NEUTRAL | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
        else:
            logger.debug(f" NEUTRAL | check | Product: {self.product_name} | Note: No alert sent")
# ---------------------------------- Alert Preparation------------------------------------ # 
    def discord_message(self):
        color_name = self.product_color.get(self.product_name, ":black_large_square:")   # Default to grey if not found

        direction_emojis = {
            'Higher': '🔼',
            'Lower': '🔽',
        }

        arrow = direction_emojis.get(self.neutral_type, '')

        embed = DiscordEmbed(
            title=f"{color_name} **{self.product_name} - Context Alert - Neutral Activity**",
            description=(
                f"> {arrow}   **NEUTRAL**    {arrow}\n"
                f"- Neutral Activity Detected!"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()  # Automatically sets the timestamp to current time

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        
        try:
            # Send the embed using the alert webhook
            self.send_alert_embed(embed, username="NEUTRAL Alert Bot")
            logger.info(f" NEUTRAL | execute | Product: {self.product_name} | Note: Alert Sent To Discord Webhook")
        except Exception as e:
            logger.error(f" NEUTRAL | execute | Product: {self.product_name} | Note: Error sending Discord message: {e}")