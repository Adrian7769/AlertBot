import logging
import math
from alertbot.utils import config
from alertbot.alerts.base import Base
from discord_webhook import DiscordWebhook, DiscordEmbed
import threading
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class Gap_Check_Equity(Base):
    def __init__(self, files):
        super().__init__(files=files)
        
    # ---------------------- Specific Calculations ------------------------- #
    def exp_range(self, prior_close, impvol):
        
        exp_range = round(((prior_close * (impvol / 100)) * math.sqrt(1 / 252)), 2)
        
        return exp_range

    def gap_info(self, day_open, prior_high, prior_low, exp_range):
        
        gap = ""
        gap_tier = ""
        
        if day_open > prior_high:
            gap_size = round((day_open - prior_high), 2)
            gap = "Gap Up"
            
            if exp_range == 0:
                gap_tier = "Undefined"  
            else:
                gap_ratio = round((gap_size / exp_range) , 2)
                if gap_ratio <= 0.5:
                    gap_tier = "Tier 1"
                elif gap_ratio <= 0.75:
                    gap_tier = "Tier 2"
                else:
                    gap_tier = "Tier 3"
        
        elif day_open < prior_low:
            gap_size = round((prior_low - day_open), 2)
            gap = "Gap Down"
            
            if exp_range == 0:
                gap_tier = "Undefined" 
            else:
                gap_ratio = round((gap_size / exp_range) , 2)
                if gap_ratio <= 0.5:
                    gap_tier = "Tier 1"
                elif gap_ratio <= 0.75:
                    gap_tier = "Tier 2"
                else:
                    gap_tier = "Tier 3"
        
        else:
            gap = "No Gap"
            gap_tier = "Tier 0"
            gap_size = 0
        
        return gap, gap_tier, gap_size
       
    # ---------------------- Alert Preparation ------------------------- #
    def send_alert(self):
        threads = []
        for product_name in ['ES', 'NQ', 'RTY']:
            thread = threading.Thread(target=self.process_product, args=(product_name,))
            thread.start()
            threads.append(thread)
            time.sleep(1)

        # Optionally wait for all threads to complete
        for thread in threads:
            thread.join()

    def process_product(self, product_name):
        try:
            variables = self.fetch_latest_variables(product_name)
            if not variables:
                logger.error(f" GAP_EQUITY | process_product | Product: {product_name} |  Note: No data available ")
                return
            
            # Variables (Round All Variables) 
            prior_close = round(variables.get(f'{product_name}_PRIOR_CLOSE'), 2)
            day_open = round(variables.get(f'{product_name}_DAY_OPEN'), 2)
            prior_high = round(variables.get(f'{product_name}_PRIOR_HIGH'), 2)
            prior_low = round(variables.get(f'{product_name}_PRIOR_LOW'), 2)
            
            # Implied volatility specific to the product
            if product_name == 'ES':
                impvol = config.es_impvol
            elif product_name == 'NQ':
                impvol = config.nq_impvol
            elif product_name == 'RTY':
                impvol = config.rty_impvol
            else:
                raise ValueError(f" GAP_EQUITY | process_product | Note: {product_name}")
            
            color = self.product_color.get(product_name)
            current_time = datetime.now(self.est).strftime('%H:%M:%S')
            
            # Calculations
            exp_range = self.exp_range(
                prior_close, impvol
                )
            gap, gap_tier, gap_size = self.gap_info(
                day_open, prior_high, prior_low, exp_range
                )
            
            if gap in ["Gap Up", "Gap Down"]:
                direction_emojis = {
                    'Gap Up': ':arrow_up:',
                    'Gap Down': ':arrow_down:',
                }
                
                # Build the Discord Embed
                try:
                    # Title Construction with Emojis
                    embed_title = f":large_{color}_square: **{product_name} - Context Alert - Gap** :large_{color}_square:"
                    embed = DiscordEmbed(
                        title=embed_title,
                        description=(
                            f"**Gap Type**: _{gap}_\n"
                            f"**Tier**: _{gap_tier}_\n"
                            f"**Gap Size**: _{gap_size}p_"
                        ),
                        color=self.get_color()
                    )
                    embed.set_timestamp()  # Automatically sets the timestamp to current time

                    # Add Alert Time
                    embed.add_embed_field(name=":alarm_clock: Alert Time", value=f"_{current_time}_ EST", inline=False)

                    # Send the embed with the webhook
                    self.send_alert_embed(embed, username=None, avatar_url=None)
                except Exception as e:
                    logger.error(f" GAP_EQUITY | process_product | Product: {product_name} | Error sending Discord message: {e}")
            else:
                logger.info(f" GAP_EQUITY | process_product | Product: {product_name} | Note: No Gap detected, message not sent.")
        except Exception as e:
            logger.error(f" GAP_EQUITY | process_product | Product: {product_name} | Error processing: {e}")