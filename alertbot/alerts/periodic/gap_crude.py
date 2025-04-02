import logging
import math
from alertbot.utils import config
from alertbot.alerts.base import Base
from discord_webhook import DiscordWebhook, DiscordEmbed
import threading
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class Gap_Check_Crude(Base):
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
                gap_ratio = round((gap_size / exp_range), 2)
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
                gap_ratio = round((gap_size / exp_range), 2)
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

    # ---------------------- Driving Input Logic ------------------------- #
    def send_alert(self):
        threads = []
        for product_name in ['CL']:
            thread = threading.Thread(target=self.process_product, args=(product_name,))
            thread.start()
            threads.append(thread)
            time.sleep(1)

        for thread in threads:
            thread.join()

    # ---------------------- Alert Preparation ------------------------- #
    def process_product(self, product_name):
        try:
            local_product = product_name
            variables = self.fetch_latest_variables(local_product)
            if not variables:
                logger.error(f" GAP_CRUDE | process_product | Product: {local_product} |  Note: No data available ")
                return
            prior_close = round(variables.get(f'{local_product}_PRIOR_CLOSE'), 2)
            day_open = round(variables.get(f'{local_product}_DAY_OPEN'), 2)
            prior_high = round(variables.get(f'{local_product}_PRIOR_HIGH'), 2)
            prior_low = round(variables.get(f'{local_product}_PRIOR_LOW'), 2)
            impvol = config.cl_impvol
            color_name = self.product_color.get(local_product, ":black_large_square:") 
            color_value = self.get_color(local_product)
            exp_range = self.exp_range(prior_close, impvol)
            gap, gap_tier, gap_size = self.gap_info(day_open, prior_high, prior_low, exp_range)
            
            if gap in ["Gap Up", "Gap Down"]:
                direction_emojis = {
                    'Gap Up': '🔼',
                    'Gap Down': '🔽',
                }
                
                try:
                    embed_title = f"{color_name} **{local_product} - Context Alert - Gap** {direction_emojis[gap]}"
                    embed = DiscordEmbed(
                        title=embed_title,
                        description=(
                            f"**Gap Type**: {gap} \n"
                            f"**Tier**: {gap_tier} \n"
                            f"**Gap Size**: {gap_size}p "
                        ),
                        color=color_value
                    )
                    embed.set_timestamp()  

                    self.send_alert_embed(embed, product_name=local_product, username=None, avatar_url=None)

                except Exception as e:
                    logger.error(f" GAP_CRUDE | process_product | Product: {local_product} | Error sending Discord message: {e}")
            else:
                logger.info(f" GAP_CRUDE | process_product | Product: {local_product} | Note: No Gap detected, message not sent.")
        except Exception as e:
            logger.error(f" GAP_CRUDE | process_product | Product: {local_product} | Error processing: {e}")
