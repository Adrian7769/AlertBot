import logging
import math
import threading
from datetime import datetime
from alertbot.utils import config
from discord_webhook import DiscordEmbed
from alertbot.alerts.base import Base
logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

# NEED TO IMPLEMENT
class STRC(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables (Round All Variables)
        self.p_vpoc = round(self.variables.get(f'{self.product_name}_PRIOR_VPOC'), 2)
        self.day_open = round(self.variables.get(f'{self.product_name}_DAY_OPEN'), 2)
        self.p_high = round(self.variables.get(f'{self.product_name}_PRIOR_HIGH'), 2)
        self.p_low = round(self.variables.get(f'{self.product_name}_PRIOR_LOW'), 2)
        self.ib_atr = round(self.variables.get(f'{self.product_name}_IB_ATR'), 2)
        self.euro_ibh = round(self.variables.get(f'{self.product_name}_EURO_IBH'), 2)
        self.euro_ibl = round(self.variables.get(f'{self.product_name}_EURO_IBL'), 2)
        self.orh = round(self.variables.get(f'{self.product_name}_ORH'), 2)
        self.orl = round(self.variables.get(f'{self.product_name}_ORL'), 2)
        self.eth_vwap = round(self.variables.get(f'{self.product_name}_ETH_VWAP'), 2)
        self.cpl = round(self.variables.get(f'{self.product_name}_CPL'), 2)
        self.total_ovn_delta = round(self.variables.get(f'{self.product_name}_TOTAL_OVN_DELTA'), 2)
        self.total_rth_delta = round(self.variables.get(f'{self.product_name}_TOTAL_RTH_DELTA'), 2)
        self.prior_close = round(self.variables.get(f'{self.product_name}_PRIOR_CLOSE'), 2)
        self.ib_high = round(self.variables.get(f'{product_name}_IB_HIGH'), 2)
        self.ib_low = round(self.variables.get(f'{product_name}_IB_LOW'), 2)
        
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.delta = self.total_delta()
        self.exp_rng, self.exp_hi, self.exp_lo = self.exp_range() 
        
    def safe_round(self, value, digits=2):
        if value is None:
            logger.error("STRC: Missing value for rounding; defaulting to 0.")
            return 0
        try:
            return round(value, digits)
        except Exception as e:
            logger.error(f"STRC: Error rounding value {value}: {e}")
            return 0
        
# ---------------------------------- Specific Calculations ------------------------------------ #   
    def exp_range(self):

        # Calculation (product specific or Not)
        if not self.prior_close:
            logger.error(f" STRC | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" STRC | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)

        if impvol is None:
            raise ValueError(f" STRC | exp_range | Product: {self.product_name} | Note: Unknown Product")

        exp_range = round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)), 2)
        exp_hi = round(self.prior_close + exp_range, 2)
        exp_lo = round(self.prior_close - exp_range, 2)
        
        logger.debug(f" STRC | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
        return exp_range, exp_hi, exp_lo
        
        
    def total_delta(self):

        # Calculation (Product Specific or Not)        
        total_delta = self.total_ovn_delta + self.total_rth_delta
        
        logger.debug(f" STRC | total_delta | TOTAL_DELTA: {total_delta}")
        return total_delta   
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        def log_condition(condition, description):
            logger.debug(f" STRC | input | Product: {self.product_name} | {description} --> {condition}")
            return condition

        self.used_atr = self.ib_high - self.ib_low
        self.remaining_atr = max((self.ib_atr - self.used_atr), 0)

        # Direction Based Logic
        if self.direction == "short":
            self.atr_condition = log_condition(abs(self.ib_low - self.p_vpoc) <= self.remaining_atr,
                                                "ATR Condition for short: abs(ib_low - p_vpoc) <= remaining_atr")
            self.or_condition = log_condition(self.cpl < self.orl,
                                            "OR Condition for short: cpl < orl")
        elif self.direction == "long":
            self.atr_condition = log_condition(abs(self.ib_high - self.p_vpoc) <= self.remaining_atr,
                                                "ATR Condition for long: abs(ib_high - p_vpoc) <= remaining_atr")
            self.or_condition = log_condition(self.cpl > self.orh,
                                            "OR Condition for long: cpl > orh")

        # Driving Input Logic
        cond1 = log_condition(self.p_low - (self.exp_rng * 0.15) <= self.day_open <= self.p_high + (self.exp_rng * 0.15),
                            "Driving Condition 1: p_low - (exp_rng*0.15) <= day_open <= p_high + (exp_rng*0.15)")
        cond2 = log_condition(self.p_low + (self.exp_rng * 0.10) <= self.cpl <= self.p_high - (self.exp_rng * 0.10),
                            "Driving Condition 2: p_low + (exp_rng*0.10) <= cpl <= p_high - (exp_rng*0.10)")
        cond3 = log_condition(self.atr_condition, "Driving Condition 3: ATR Condition")
        cond4 = log_condition(abs(self.cpl - self.p_vpoc) > self.exp_rng * 0.1,
                            "Driving Condition 4: abs(cpl - p_vpoc) > (exp_rng*0.1)")
        cond5 = log_condition(self.or_condition, "Driving Condition 5: OR Condition")

        logic = cond1 and cond2 and cond3 and cond4 and cond5

        logger.debug(f" STRC | input | Product: {self.product_name} | FINAL_LOGIC: {logic} | "
                    f"COND1: {cond1} | COND2: {cond2} | COND3: {cond3} | COND4: {cond4} | COND5: {cond5}")
        return logic
    
# ---------------------------------- Opportunity Window ------------------------------------ #   
    def time_window(self):
        
        # Update current time
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
        
        # Define time windows based on product type
        if self.product_name == 'CL':
            start_time = self.crude_pvat_start
            end_time = self.crude_ib
            logger.debug(f" STRC | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_pvat_start
            end_time = self.equity_ib
            logger.debug(f" STRC | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f" STRC | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        
        # Check if current time is within the window
        if start_time <= self.current_time <= end_time:
            logger.debug(f" STRC | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" STRC | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
        
        # Define Direction
        self.direction = "short" if self.cpl > self.p_vpoc else "long"
        self.color = "red" if self.direction == "short" else "green"
    
        # Driving Input
        if self.input() and self.time_window():
            
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)   
                logger.debug(f" STRC | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                
                if self.direction != last_alert: 
                    logger.info(f" STRC | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Logic For c_within_atr 
                    if self.atr_condition: 
                        self.c_within_atr = "x" 
                    else:
                        self.c_within_atr = "  "
                    # Logic For c_orderflow
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"
                    # Logic for c_euro IB
                    self.c_euro_ib = "  "
                    if self.direction == "short" and self.cpl < self.euro_ibl:
                        self.c_euro_ib = "x"
                    elif self.direction == "long" and self.cpl > self.euro_ibh:
                        self.c_euro_ib = "x"
                    # Logic for c_or
                    self.c_or = "  "
                    if self.direction == "short" and self.cpl < self.orl:
                        self.c_or = "x"
                    elif self.direction == "long" and self.cpl > self.orh:
                        self.c_or = "x"
                    # Logic for c_between
                    self.c_between = "  "
                    if self.direction == "short" and self.p_vpoc < self.cpl < self.eth_vwap:
                        self.c_between = "x"
                    elif self.direction == "long" and self.eth_vwap < self.cpl < self.p_vpoc:
                        self.c_between = "x"
                    # Logic for c_align
                    if abs(self.eth_vwap - self.p_vpoc) <= (self.exp_rng * 0.05):
                        self.c_align = "x"
                    else: 
                        self.c_align = "  "
                    # Logic for Score 
                    self.score = sum(1 for condition in [self.c_within_atr, self.c_orderflow, self.c_euro_ib, self.c_or, self.c_between, self.c_align] if condition == "x")   
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" STRC | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" STRC | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.info(f" STRC | check | Product: {self.product_name} | Note: Condition Not Met")
# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):
        
        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        
        direction_settings = {
            "long": {
                "pv_indicator": "^",
                "c_euro_ib_text": "Above Euro IBH",
                "c_or_text": "Above 30 Sec Opening Range High",
                "emoji_indicator": "🔼",
                "color_circle": "🔵"
            },
            "short": {
                "pv_indicator": "v",
                "c_euro_ib_text": "Below Euro IBL",
                "c_or_text": "Below 30 Sec Opening Range Low",
                "emoji_indicator": "🔽",
                "color_circle": "🔴"
            }
        }

        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" STRC | discord_message | Note: Invalid direction '{self.direction}'")
        
        # Title Construction with Emojis
        title = f"{settings['color_circle']} **{self.product_name} - Playbook Alert** {settings['emoji_indicator']} **PVAT {settings['pv_indicator']}**"

        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: _{self.p_vpoc} (Prior Session Vpoc)_\n"
                f"**Risk**: _Wrong if auction fails to complete PVPOC test before IB, or accepts away from value_\n"
                f"**Driving Input**: _Auction opening in range or slightly outside range, divergent from prior session Vpoc_\n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()  # Automatically sets the timestamp to current time

        # Criteria Header
        embed.add_embed_field(name="**Criteria**", value="\u200b", inline=False)

        # Criteria Details
        criteria = (
            f"• **[{self.c_within_atr}]** Target Within ATR Of IB\n"
            f"• **[{self.c_orderflow}]** Orderflow In Direction Of Target (_{self.delta}_) \n"
            f"• **[{self.c_euro_ib}]** {settings['c_euro_ib_text']}\n"
            f"• **[{self.c_or}]** {settings['c_or_text']}\n"
            f"\n• **[{self.c_between}]** Between DVWAP and PVPOC\n"
            f"Or\n"
            f"• **[{self.c_align}]** DVWAP and PVPOC aligned\n"
        )
        embed.add_embed_field(name="\u200b", value=criteria, inline=False)

        # Playbook Score
        embed.add_embed_field(name="**Playbook Score**", value=f"_{self.score} / 5_", inline=False)
        
        # Alert Time and Price Context
        alert_time_text = f"**Alert Time / Price**: _{alert_time_formatted} EST | {self.cpl}_"
        embed.add_embed_field(name="\u200b", value=alert_time_text, inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"STRC | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")