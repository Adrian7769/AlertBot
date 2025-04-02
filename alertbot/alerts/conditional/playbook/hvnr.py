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
class HVNR(Base):
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
            logger.error("HVNR: Missing value for rounding; defaulting to 0.")
            return 0
        try:
            return round(value, digits)
        except Exception as e:
            logger.error(f"HVNR: Error rounding value {value}: {e}")
            return 0
# ---------------------------------- Specific Calculations ------------------------------------ #   
    def exp_range(self):

        # Calculation (product specific or Not)
        if not self.prior_close:
            logger.error(f" HVNR | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" HVNR | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)

        if impvol is None:
            raise ValueError(f"HVNR | exp_range | Product: {self.product_name} | Note: Unknown Product")

        exp_range = round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)), 2)
        exp_hi = round(self.prior_close + exp_range, 2)
        exp_lo = round(self.prior_close - exp_range, 2)
        
        logger.debug(f" HVNR | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
        return exp_range, exp_hi, exp_lo
        
        
    def total_delta(self):

        # Calculation (Product Specific or Not)        
        total_delta = self.total_ovn_delta + self.total_rth_delta
        
        logger.debug(f" HVNR | total_delta | TOTAL_DELTA: {total_delta}")
        return total_delta   
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        def log_condition(condition, description):
            logger.debug(f"HVNR | input | Product: {self.product_name} | {description} --> {condition}")
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

        logger.debug(f"HVNR | input | Product: {self.product_name} | FINAL_LOGIC: {logic} | "
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
            logger.debug(f" HVNR | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_pvat_start
            end_time = self.equity_ib
            logger.debug(f" HVNR | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f" HVNR | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        
        # Check if current time is within the window
        if start_time <= self.current_time <= end_time:
            logger.debug(f" HVNR | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" HVNR | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):

        # Determine Direction Based on Open vs. Prior High/Low with Logging
        if self.day_open > self.p_high:
            self.direction = "short"
            logger.debug(f" HVNR | check | Product: {self.product_name} | DIR_LOGIC: self.day_open({self.day_open}) > self.prior_high({self.prior_high}) -> short")
        elif self.day_open < self.p_low:
            self.direction = "long"
            logger.debug(f" HVNR | check | Product: {self.product_name} | DIR_LOGIC: self.day_open({self.day_open}) < self.prior_low({self.prior_low}) -> long")
        else:
            logger.debug(f" HVNR | check | Product: {self.product_name} | Note: Open In Range; Not In Play, Returning.")
            return  # Open In Range, So Not In Play

        # Driving Input Check with Logging
        if self.time_window() and self.input():
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)
                logger.debug(f" HVNR | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                if self.direction != last_alert:
                    logger.info(f" HVNR | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Critical Criteria Logging
                    self.c_several_dir_days = "x"
                    logger.debug(f" HVNR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: Set c_several_dir_days -> [{self.c_several_dir_days}]")
                    
                    self.c_ab_vwap = "x"
                    logger.debug(f" HVNR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: Set c_ab_vwap -> [{self.c_ab_vwap}]")
                    
                    self.c_posture = "x"
                    logger.debug(f" HVNR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: Set c_posture -> [{self.c_posture}]")
                    
                    # Logic For c_orderflow with Logging
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                        logger.debug(f" HVNR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: self.delta({self.delta}) < 0 for short -> [{self.c_orderflow}]")
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"
                        logger.debug(f" HVNR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: self.delta({self.delta}) > 0 for long -> [{self.c_orderflow}]")
                    else:
                        logger.debug(f" HVNR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: Orderflow criteria not met -> [{self.c_orderflow}]")
                    
                    # Logic for c_within_ibatr with Logging
                    if abs(self.cpl - self.p_vpoc) <= self.ib_atr:
                        self.c_within_ibatr = "x"
                        logger.debug(f" HVNR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: |abs(self.cpl({self.cpl}) - self.prior_vpoc({self.prior_vpoc})| <= self.ib_atr({self.ib_atr}) -> [{self.c_within_ibatr}]")
                    else:
                        self.c_within_ibatr = "  "
                        logger.debug(f" HVNR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: |abs(self.cpl({self.cpl}) - self.prior_vpoc({self.prior_vpoc})| > self.ib_atr({self.ib_atr}) -> [{self.c_within_ibatr}]")
                    
                    # Score Calculation Logging
                    self.score = sum(1 for condition in [self.c_several_dir_days, self.c_ab_vwap, self.c_posture, self.c_orderflow, self.c_within_ibatr] if condition == "x")
                    logger.debug(f" HVNR | check | Product: {self.product_name} | Direction: {self.direction} | SCORE: {self.score}/5")
                    
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" HVNR | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" HVNR | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f" HVNR | check | Product: {self.product_name} | Note: Condition(s) Not Met")

# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):
        
        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        
        direction_settings = {
            "long": {
                "c_euro_ib_text": "Above Euro IBH",
                "c_or_text": "Above 30 Sec Opening Range High",
                "emoji_indicator": "🔼",
            },
            "short": {
                "c_euro_ib_text": "Below Euro IBL",
                "c_or_text": "Below 30 Sec Opening Range Low",
                "emoji_indicator": "🔽",
            }
        }

        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" HVNR | discord_message | Note: Invalid direction '{self.direction}'")
        
        # Title Construction with Emojis
        title = f"**{self.product_name} - Playbook Alert** - **HVNR** {settings['emoji_indicator']}"

        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: {self.p_vpoc} (Prior Session Vpoc) \n"
                f"**Risk**: Wrong if auction fails to complete PVPOC test before IB, or accepts away from value \n"
                f"**Driving Input**: Auction opening in range or slightly outside range, divergent from prior session Vpoc \n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()  

        # Criteria Header
        embed.add_embed_field(name="**Criteria**", value="", inline=False)

        # Criteria Details
        criteria = (
            f"- **[{self.c_within_atr}]** Target Within ATR Of IB\n"
            f"- **[{self.c_orderflow}]** Orderflow In Direction Of Target ({self.delta}) \n"
            f"- **[{self.c_euro_ib}]** {settings['c_euro_ib_text']}\n"
            f"- **[{self.c_or}]** {settings['c_or_text']}\n"
            f"\n- **[{self.c_between}]** Between DVWAP and PVPOC\n"
            f"Or\n"
            f"- **[{self.c_align}]** DVWAP and PVPOC aligned\n"
        )
        embed.add_embed_field(name="", value=criteria, inline=False)

        # Playbook Score
        embed.add_embed_field(name="**Playbook Score**", value=f"{self.score} / 5", inline=False)
        
        alert_time_text = f"**Alert Time / Price**: {alert_time_formatted} EST | {self.cpl}"
        embed.add_embed_field(name="", value=alert_time_text, inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"HVNR | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")