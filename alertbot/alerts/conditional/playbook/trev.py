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

class TREV(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables (Round All Variables)
        self.prior_vpoc = self.safe_round(variables.get(f'{self.product_name}_PRIOR_VPOC'))
        self.day_open = self.safe_round(variables.get(f'{self.product_name}_DAY_OPEN'))
        self.p_high = self.safe_round(variables.get(f'{self.product_name}_PRIOR_HIGH'))
        self.p_low = self.safe_round(variables.get(f'{self.product_name}_PRIOR_LOW'))
        self.prior_high = self.safe_round(variables.get(f'{self.product_name}_PRIOR_HIGH'))
        self.prior_low = self.safe_round(variables.get(f'{self.product_name}_PRIOR_LOW'))
        self.prior_prior_high = self.safe_round(variables.get(f'{self.product_name}_PRIOR_PRIOR_HIGH'))
        self.prior_prior_low = self.safe_round(variables.get(f'{self.product_name}_PRIOR_PRIOR_LOW'))                
        self.ib_atr = self.safe_round(variables.get(f'{self.product_name}_IB_ATR'))
        self.eth_vwap = variables.get(f'{self.product_name}_ETH_VWAP')
        self.cpl = self.safe_round(variables.get(f'{self.product_name}_CPL'))
        self.total_ovn_delta = self.safe_round(variables.get(f'{self.product_name}_TOTAL_OVN_DELTA'))
        self.total_rth_delta = self.safe_round(variables.get(f'{self.product_name}_TOTAL_RTH_DELTA'))
        self.prior_close = self.safe_round(variables.get(f'{self.product_name}_PRIOR_CLOSE'))
        self.ib_high = self.safe_round(variables.get(f'{product_name}_IB_HIGH'))
        self.ib_low = self.safe_round(variables.get(f'{product_name}_IB_LOW'))
        self.fd_vpoc = self.safe_round(variables.get(f'{product_name}_5D_VPOC'))
        self.td_vpoc = self.safe_round(variables.get(f'{product_name}_20D_VPOC'))        
        
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.delta = self.total_delta()
        self.exp_rng = self.exp_range() 
        self.gap, self.gap_tier, self.gap_size = self.gap_info()
        
    def safe_round(self, value, digits=2):
        if value is None:
            logger.error(f"TREV | safe_round | Product: {self.product_name} | Missing value for rounding; defaulting to 0.")
            return 0
        try:
            return round(value, digits)
        except Exception as e:
            logger.error(f"TREV | safe_round | Product: {self.product_name} | Error rounding value {value}: {e}")
            return 0        

# ---------------------------------- Specific Calculations ------------------------------------ #   
    def exp_range(self):
        if not self.prior_close:
            logger.error(f" TREV | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" TREV | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)
        if impvol is None:
            raise ValueError(f" TREV | exp_range | Product: {self.product_name} | Note: Unknown Product")
        exp_range = self.safe_round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)))
        logger.debug(f" TREV | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range}")
        return exp_range
    
    def gap_info(self):
        gap = ""
        gap_tier = ""
        gap_size = 0
        if self.day_open > self.prior_high:
            gap_size = self.safe_round((self.day_open - self.prior_high))
            gap = "Gap Up"
            if self.exp_rng == 0:
                gap_tier = "Undefined"  
            else:
                gap_ratio = round((gap_size / self.exp_rng))
                if gap_ratio <= 0.5:
                    gap_tier = "Tier_1"
                elif gap_ratio <= 0.75:
                    gap_tier = "Tier_2"
                else:
                    gap_tier = "Tier_3"
        elif self.day_open < self.prior_low:
            gap_size = self.safe_round((self.prior_low - self.day_open))
            gap = "Gap Down"
            if self.exp_rng == 0:
                gap_tier = "Undefined" 
            else:
                gap_ratio = self.safe_round((gap_size / self.exp_rng))
                if gap_ratio <= 0.5:
                    gap_tier = "Tier_1"
                elif gap_ratio <= 0.75:
                    gap_tier = "Tier_2"
                else:
                    gap_tier = "Tier_3"
        else:
            gap = "No Gap"
            gap_tier = "Tier_0"
            gap_size = 0
        logger.debug(f" TREV | gap_info | Product: {self.product_name} | GAP: {gap} | GAP_TIER: {gap_tier} | GAP_SIZE: {gap_size}")
        return gap_tier, gap, gap_size
        
    def total_delta(self):
        total_delta = self.total_ovn_delta + self.total_rth_delta
        logger.debug(f" TREV | total_delta | Product: {self.product_name} | TOTAL_DELTA: {total_delta}")
        return total_delta  
     
    def posture(self):
        threshold = self.safe_round((self.exp_rng * 0.68))
        if (abs(self.cpl - self.fd_vpoc) <= threshold) and (abs(self.fd_vpoc - self.td_vpoc) <= threshold):
            posture = "PRICE=5D=20D"
        elif (self.cpl > self.fd_vpoc + threshold) and (self.fd_vpoc > self.td_vpoc + threshold):
            posture = "PRICE^5D^20D"
        elif (self.cpl < self.fd_vpoc - threshold) and (self.fd_vpoc < self.td_vpoc - threshold):
            posture = "PRICEv5Dv20D"
        elif (abs(self.cpl - self.fd_vpoc) <= threshold) and (self.fd_vpoc > self.td_vpoc + threshold):
            posture = "PRICE=5D^20D"
        elif (self.cpl > self.fd_vpoc + threshold) and (abs(self.fd_vpoc - self.td_vpoc) <= threshold):
            posture = "PRICE^5D=20D"
        elif (self.cpl < self.fd_vpoc - threshold) and (abs(self.fd_vpoc - self.td_vpoc) <= threshold):
            posture = "PRICEv5D=20D"
        elif (abs(self.cpl - self.fd_vpoc) <= threshold) and (self.fd_vpoc < self.td_vpoc - threshold):
            posture = "PRICE=5Dv20D"
        elif (self.cpl > self.fd_vpoc + threshold) and (self.fd_vpoc < self.td_vpoc - threshold):
            posture = "PRICE^5Dv20D"
        elif (self.cpl < self.fd_vpoc - threshold) and (self.fd_vpoc > self.td_vpoc + threshold):
            posture = "PRICEv5D^20D"
        else:
            posture = "Other"
        logger.debug(f" TREV | posture | Product: {self.product_name} | POSTURE: {posture}")
        return posture    
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        def log_condition(condition, description):
            logger.debug(f"TREV | input | Product: {self.product_name} | Direction: {self.direction} | {description} --> {condition}")
            return condition
        if self.direction == "short":
            crit1 = log_condition(
                self.prior_low > self.prior_prior_high,
                f"CRITICAL1: prior_low({self.prior_low}) > prior_prior_high({self.prior_prior_high})"
            )
            crit2 = log_condition(
                self.prior_vpoc > self.prior_low + 0.33 * (self.prior_high - self.prior_low),
                f"CRITICAL2: prior_vpoc({self.prior_vpoc}) > (prior_low({self.prior_low}) + 0.33*(prior_high({self.prior_high}) - prior_low({self.prior_low})))"
            )
            crit3 = log_condition(
                self.cpl < self.eth_vwap,
                f"CRITICAL3: cpl({self.cpl}) < eth_vwap({self.eth_vwap})"
            )
        elif self.direction == "long":
            crit1 = log_condition(
                self.prior_high < self.prior_prior_low,
                f"CRITICAL1: prior_high({self.prior_high}) < prior_prior_low({self.prior_prior_low})"
            )
            crit2 = log_condition(
                self.prior_vpoc < self.prior_high - 0.33 * (self.prior_high - self.prior_low),
                f"CRITICAL2: prior_vpoc({self.prior_vpoc}) < (prior_high({self.prior_high}) - 0.33*(prior_high({self.prior_high}) - prior_low({self.prior_low})))"
            )
            crit3 = log_condition(
                self.cpl > self.eth_vwap,
                f"CRITICAL3: cpl({self.cpl}) > eth_vwap({self.eth_vwap})"
            )
        crit4 = log_condition(
            self.gap_tier == "Tier_1",
            f"CRITICAL4: gap_tier({self.gap_tier}) == 'Tier_1'")
        crit5 = log_condition(
            self.posture() in ["PRICE^5D^20D", "PRICEv5Dv20D", "PRICEv5D^20D", "PRICE^5Dv20D"],
            f"CRITICAL5: posture({self.posture()}) in ['PRICE^5D^20D', 'PRICEv5Dv20D', 'PRICEv5D^20D', 'PRICE^5Dv20D']"
        )
        logic = crit1 and crit2 and crit3 and crit4 and crit5
        logger.debug(f"TREV | input | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {logic} | "
                    f"CRITICAL1: {crit1} | CRITICAL2: {crit2} | CRITICAL3: {crit3} | CRITICAL4: {crit4} | CRITICAL5: {crit5}")
        return logic

    
# ---------------------------------- Opportunity Window ------------------------------------ #   
    def time_window(self):
        
        # Update current time
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
        
        # Define time windows based on product type
        if self.product_name == 'CL':
            start_time = self.crude_open
            end_time = self.crude_ib
            logger.debug(f" TREV | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_open
            end_time = self.equity_ib
            logger.debug(f" TREV | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f" TREV | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        
        # Check if current time is within the window
        if start_time <= self.current_time <= end_time:
            logger.debug(f" TREV | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" TREV | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
    
        if self.day_open > self.prior_high:
            self.direction = "short"
        elif self.day_open < self.prior_low:
            self.direction = "long"
        else:
            logger.debug(f" TREV | check | Product: {self.product_name} | Note: Open In Range; Not In Play, Returning.")
            return # Open In Range, So Not In Play
    
        # Driving Input
        if self.time_window() and self.input():
            
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)   
                logger.debug(f" TREV | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                
                if self.direction != last_alert: 
                    logger.info(f" TREV | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Critical Criteria
                    self.c_several_dir_days = "x"
                    self.c_ab_vwap = "x"
                    self.c_posture = "x" 
                    # Logic For c_orderflow
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"
                    # Logic for c_within_atr
                    if abs(self.cpl - self.prior_vpoc) <= self.ib_atr:
                        self.c_within_ibatr= "x"
                    else:
                        self.c_within_ibatr = "  "
                    # Logic for Score 
                    self.score = sum(1 for condition in [self.c_several_dir_days, self.c_ab_vwap, self.c_posture, self.c_orderflow, self.c_within_ibatr] if condition == "x")   
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" TREV | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" TREV | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.info(f" TREV | check | Product: {self.product_name} | Note: Condition(s) Not Met")
# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):

        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        direction_settings = {
            "long": {
                "dir_indicator": "^",
                "vwap": "Above"
            },
            "short": {
                "dir_indicator": "v",
                "vwap": "Below"
            }
        }
 
        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" TREV | discord_message | Product: {self.product_name} | Note: Invalid direction '{self.direction}'")     

        # Title Construction with Emojis
        title = f"**{self.product_name} - Playbook Alert** - **3REV {settings['dir_indicator']}**"
    
        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: {self.prior_vpoc} (PVPOC) \n"
                f"**Risk**: Wrong if Auction Finds Acceptance Away from Prior Session Vpoc\n"
                f"**Driving Input**: Several Day's of Sustained Direction and Participation is Waning. \n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()

        # Criteria Header
        embed.add_embed_field(name="**Criteria**", value="\u200b", inline=False)

        # Criteria Details
        criteria = (
            f"• [{self.c_several_dir_days}] Several Days of Sustained Direction \n"
            f"• [{self.c_posture}] Auction in Postural Extreme: ({self.posture()}) \n"
            f"• [{self.c_orderflow}] Supportive Cumulative Delta ({self.delta}) \n"
            f"• [{self.c_ab_vwap}] {settings['vwap']} ETH VWAP \n"
            f"• [{self.c_within_ibatr}] Prior Vpoc Within ATR of IB \n"
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
        logger.info(f"TREV | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
