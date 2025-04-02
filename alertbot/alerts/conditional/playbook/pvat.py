import logging
import math
import threading
from datetime import datetime
from alertbot.utils import config
from discord_webhook import DiscordEmbed, DiscordWebhook
from alertbot.alerts.base import Base
logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class PVAT(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables (Round All Variables)
        self.p_vpoc = self.safe_round(self.variables.get(f'{self.product_name}_PRIOR_VPOC'))
        self.day_open = self.safe_round(self.variables.get(f'{self.product_name}_DAY_OPEN'))
        self.p_high = self.safe_round(self.variables.get(f'{self.product_name}_PRIOR_HIGH'))
        self.p_low = self.safe_round(self.variables.get(f'{self.product_name}_PRIOR_LOW'))
        self.ib_atr = self.safe_round(self.variables.get(f'{self.product_name}_IB_ATR'))
        self.euro_ibh = self.safe_round(self.variables.get(f'{self.product_name}_EURO_IBH'))
        self.euro_ibl = self.safe_round(self.variables.get(f'{self.product_name}_EURO_IBL'))
        self.orh = self.safe_round(self.variables.get(f'{self.product_name}_ORH'))
        self.orl = self.safe_round(self.variables.get(f'{self.product_name}_ORL'))
        self.eth_vwap = self.variables.get(f'{self.product_name}_ETH_VWAP')
        self.cpl = self.safe_round(self.variables.get(f'{self.product_name}_CPL'), 2)
        self.total_ovn_delta = self.safe_round(self.variables.get(f'{self.product_name}_TOTAL_OVN_DELTA'))
        self.total_rth_delta = self.safe_round(self.variables.get(f'{self.product_name}_TOTAL_RTH_DELTA'))
        self.prior_close = self.safe_round(self.variables.get(f'{self.product_name}_PRIOR_CLOSE'))
        self.ib_high = self.safe_round(self.variables.get(f'{product_name}_IB_HIGH'))
        self.ib_low = self.safe_round(self.variables.get(f'{product_name}_IB_LOW'))
        
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.delta = self.total_delta()
        self.exp_rng, self.exp_hi, self.exp_lo = self.exp_range() 
        
    def safe_round(self, value, digits=2):
        if value is None:
            logger.error(f"PVAT | safe_round | Product: {self.product_name} | Missing value for rounding; defaulting to 0.")
            return 0
        try:
            return round(value, digits)
        except Exception as e:
            logger.error(f"PVAT | safe_round | Product: {self.product_name} | Error rounding value {value}: {e}")
            return 0  
# ---------------------------------- Specific Calculations ------------------------------------ #   
    def exp_range(self):
        if not self.prior_close:
            logger.error(f" PVAT | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" PVAT | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)
        if impvol is None:
            raise ValueError(f" PVAT | exp_range | Product: {self.product_name} | Note: Unknown Product")
        exp_range = self.safe_round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)))
        exp_hi = self.safe_round(self.prior_close + exp_range)
        exp_lo = self.safe_round(self.prior_close - exp_range)
        
        logger.debug(f" PVAT | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
        return exp_range, exp_hi, exp_lo
        
    def total_delta(self):       
        total_delta = self.total_ovn_delta + self.total_rth_delta
        
        logger.debug(f" PVAT | total_delta | Product: {self.product_name} | TOTAL_DELTA: {total_delta}")
        return total_delta   
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        def log_condition(condition, description):
            logger.debug(f" PVAT | input | Product: {self.product_name} | Direction: {self.direction} | {description} --> {condition}")
            return condition

        self.used_atr = self.ib_high - self.ib_low
        self.remaining_atr = max((self.ib_atr - self.used_atr), 0)

        # Direction Based Logic
        if self.direction == "short":
            crit1 = log_condition(abs(self.ib_low - self.p_vpoc) <= self.remaining_atr,
                                                f"CRITICAL1: abs(ib_low({self.ib_low}) - p_vpoc({self.p_vpoc})) <= self.remaining_atr({self.remaining_atr})")
            crit2 = log_condition(self.cpl < self.orl,
                                            f"CRITICAL2: cpl({self.cpl}) < orl({self.orl})")
        elif self.direction == "long":
            crit1 = log_condition(abs(self.ib_high - self.p_vpoc) <= self.remaining_atr,
                                                f"CRITICAL1: abs(ib_high({self.ib_high}) - p_vpoc({self.p_vpoc})) <= self.remaining_atr({self.remaining_atr})")
            crit2 = log_condition(self.cpl > self.orh,
                                            f"CRITICAL2: cpl({self.cpl}) > orh({self.orh})")

        # Driving Input Logic
        crit3 = log_condition(self.p_low - (self.exp_rng * 0.15) <= self.day_open <= self.p_high + (self.exp_rng * 0.15),
                            f"CRITICAL3: p_low({self.p_low}) - (exp_rng({self.exp_rng})*0.15) <= day_open({self.day_open}) <= p_high({self.p_high}) + (exp_rng({self.exp_rng})*0.15)")
        crit4 = log_condition(self.p_low + (self.exp_rng * 0.10) <= self.cpl <= self.p_high - (self.exp_rng * 0.10),
                            f"CRITICAL4: p_low({self.p_low}) + (exp_rng({self.exp_rng})*0.10) <= cpl({self.cpl}) <= p_high({self.p_high}) - (exp_rng({self.exp_rng})*0.10)")
        crit5 = log_condition(abs(self.cpl - self.p_vpoc) > self.exp_rng * 0.1,
                            f"CRITICAL5: abs(cpl({self.cpl}) - p_vpoc({self.p_vpoc})) > (exp_rng){self.exp_rng})*0.1)")
        logic = crit1 and crit2 and crit3 and crit4 and crit5

        logger.debug(f" PVAT | input | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {logic} | "
                    f"CRITICAL1: {crit1} | CRITICAL2: {crit2} | CRITICAL3: {crit3} | CRITICAL4: {crit4} | CRITICAL5: {crit5}")
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
            logger.debug(f" PVAT | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_pvat_start
            end_time = self.equity_ib
            logger.debug(f" PVAT | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f" PVAT | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        
        # Check if current time is within the window
        if start_time <= self.current_time <= end_time:
            logger.debug(f" PVAT | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" PVAT | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
        
        # Define Direction with Detailed Logging
        if self.cpl > self.p_vpoc:
            self.direction = "short"
            logger.debug(f" PVAT | check | Product: {self.product_name} | DIR_LOGIC: self.cpl({self.cpl}) > self.p_vpoc({self.p_vpoc}) -> short")
        else:
            self.direction = "long"
            logger.debug(f" PVAT | check | Product: {self.product_name} | DIR_LOGIC: self.cpl({self.cpl}) <= self.p_vpoc({self.p_vpoc}) -> long")
        
        self.color = "red" if self.direction == "short" else "green"
        
        # Driving Input Check with Detailed Logging
        if self.time_window() and self.input():
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)
                logger.debug(f" PVAT | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                
                if self.direction != last_alert:
                    logger.info(f" PVAT | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Critical Criteria Logging
                    
                    # CRITERIA 1: c_within_atr
                    self.c_within_atr = "x"
                    logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: Set c_within_atr -> [{self.c_within_atr}]")
                    
                    # CRITERIA 2: c_orderflow
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: self.delta({self.delta}) < 0 for short -> [{self.c_orderflow}]")
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: self.delta({self.delta}) > 0 for long -> [{self.c_orderflow}]")
                    else:
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: Orderflow criteria not met -> [{self.c_orderflow}]")
                    
                    # CRITERIA 3: c_euro_ib
                    self.c_euro_ib = "  "
                    if self.direction == "short" and self.cpl < self.euro_ibl:
                        self.c_euro_ib = "x"
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: self.cpl({self.cpl}) < self.euro_ibl({self.euro_ibl}) for short -> [{self.c_euro_ib}]")
                    elif self.direction == "long" and self.cpl > self.euro_ibh:
                        self.c_euro_ib = "x"
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: self.cpl({self.cpl}) > self.euro_ibh({self.euro_ibh}) for long -> [{self.c_euro_ib}]")
                    else:
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: Euro IB criteria not met -> [{self.c_euro_ib}]")
                    
                    # CRITERIA 4: c_or
                    self.c_or = "  "
                    if self.direction == "short" and self.cpl < self.orl:
                        self.c_or = "x"
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: self.cpl({self.cpl}) < self.orl({self.orl}) for short -> [{self.c_or}]")
                    elif self.direction == "long" and self.cpl > self.orh:
                        self.c_or = "x"
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: self.cpl({self.cpl}) > self.orh({self.orh}) for long -> [{self.c_or}]")
                    else:
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: OR criteria not met -> [{self.c_or}]")
                    
                    # CRITERIA 5: c_between
                    self.c_between = "  "
                    if self.direction == "short" and self.p_vpoc < self.cpl < self.eth_vwap:
                        self.c_between = "x"
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: self.p_vpoc({self.p_vpoc}) < self.cpl({self.cpl}) < self.eth_vwap({self.eth_vwap}) for short -> [{self.c_between}]")
                    elif self.direction == "long" and self.eth_vwap < self.cpl < self.p_vpoc:
                        self.c_between = "x"
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: self.eth_vwap({self.eth_vwap}) < self.cpl({self.cpl}) < self.p_vpoc({self.p_vpoc}) for long -> [{self.c_between}]")
                    else:
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: Between criteria not met -> [{self.c_between}]")
                    
                    # CRITERIA 6: c_align
                    if abs(self.eth_vwap - self.p_vpoc) <= (self.exp_rng * 0.05):
                        self.c_align = "x"
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: abs(self.eth_vwap({self.eth_vwap}) - self.p_vpoc({self.p_vpoc})) <= {self.exp_rng * 0.05} -> [{self.c_align}]")
                    else:
                        self.c_align = "  "
                        logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: abs(self.eth_vwap({self.eth_vwap}) - self.p_vpoc({self.p_vpoc})) > {self.exp_rng * 0.05} -> [{self.c_align}]")
                    
                    # Score Calculation Logging
                    self.score = sum(1 for condition in [self.c_within_atr, self.c_orderflow, self.c_euro_ib, self.c_or, self.c_between, self.c_align] if condition == "x")
                    logger.debug(f" PVAT | check | Product: {self.product_name} | Direction: {self.direction} | SCORE: {self.score}/6")
                    
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" PVAT | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" PVAT | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f" PVAT | check | Product: {self.product_name} | Note: Condition(s) Not Met")

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
            raise ValueError(f" PVAT | discord_message | Note: Invalid direction '{self.direction}'")
        
        # Title Construction with Emojis
        title = f"**{self.product_name} - Playbook Alert** - **PVAT** {settings['emoji_indicator']}"

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
        logger.info(f"PVAT | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")