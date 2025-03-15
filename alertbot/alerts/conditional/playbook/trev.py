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
        self.prior_vpoc = round(self.variables.get(f'{self.product_name}_PRIOR_VPOC'), 2)
        self.day_open = round(self.variables.get(f'{self.product_name}_DAY_OPEN'), 2)
        self.p_high = round(self.variables.get(f'{self.product_name}_PRIOR_HIGH'), 2)
        self.p_low = round(self.variables.get(f'{self.product_name}_PRIOR_LOW'), 2)
        self.prior_high = round(self.variables.get(f'{self.product_name}_PRIOR_HIGH'), 2)
        self.prior_low = round(self.variables.get(f'{self.product_name}_PRIOR_LOW'), 2)
        self.prior_prior_high = round(self.variables.get(f'{self.product_name}_PRIOR_PRIOR_HIGH'), 2)
        self.prior_prior_low = round(self.variables.get(f'{self.product_name}_PRIOR_PRIOR_LOW'), 2)                
        self.ib_atr = round(self.variables.get(f'{self.product_name}_IB_ATR'), 2)
        self.eth_vwap = round(self.variables.get(f'{self.product_name}_ETH_VWAP'), 2)
        self.cpl = round(self.variables.get(f'{self.product_name}_CPL'), 2)
        self.total_ovn_delta = round(self.variables.get(f'{self.product_name}_TOTAL_OVN_DELTA'), 2)
        self.total_rth_delta = round(self.variables.get(f'{self.product_name}_TOTAL_RTH_DELTA'), 2)
        self.prior_close = round(self.variables.get(f'{self.product_name}_PRIOR_CLOSE'), 2)
        self.ib_high = round(self.variables.get(f'{product_name}_IB_HIGH'), 2)
        self.ib_low = round(self.variables.get(f'{product_name}_IB_LOW'), 2)
        self.fd_vpoc = round(variables.get(f'{product_name}_5D_VPOC'), 2)
        self.td_vpoc = round(variables.get(f'{product_name}_20D_VPOC'), 2)        
        
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.delta = self.total_delta()
        self.exp_rng = self.exp_range() 
        self.gap, self.gap_tier, self.gap_size = self.gap_info()

# ---------------------------------- Specific Calculations ------------------------------------ #   
    def exp_range(self):

        # Calculation (product specific or Not)
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

        exp_range = round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)), 2)
        
        logger.debug(f" TREV | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range}")
        return exp_range
    
    def gap_info(self):
        gap = ""
        gap_tier = ""
        gap_size = 0
        if self.day_open > self.prior_high:
            gap_size = round((self.day_open - self.prior_high), 2)
            gap = "Gap Up"
            if self.exp_rng == 0:
                gap_tier = "Undefined"  
            else:
                gap_ratio = round((gap_size / self.exp_rng) , 2)
                if gap_ratio <= 0.5:
                    gap_tier = "Tier_1"
                elif gap_ratio <= 0.75:
                    gap_tier = "Tier_2"
                else:
                    gap_tier = "Tier_3"
        elif self.day_open < self.prior_low:
            gap_size = round((self.prior_low - self.day_open), 2)
            gap = "Gap Down"
            if self.exp_rng == 0:
                gap_tier = "Undefined" 
            else:
                gap_ratio = round((gap_size / self.exp_rng) , 2)
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
        return gap_tier, gap, gap_size
        
    def total_delta(self):
        total_delta = self.total_ovn_delta + self.total_rth_delta
        logger.debug(f" TREV | total_delta | TOTAL_DELTA: {total_delta}")
        return total_delta  
     
    def posture(self):
        threshold = round((self.exp_rng * 0.68), 2)
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
        return posture    
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        
        self.used_atr = self.ib_high - self.ib_low
        self.remaining_atr = max((self.ib_atr - self.used_atr), 0)
        
        # Direction Based Logic
        if self.direction == "short":
            self.several_dir_days = self.prior_low > self.prior_prior_high # Gap Between Sessions
            self.vpoc_location = self.prior_vpoc > self.prior_low + 0.33 * (self.prior_high - self.prior_low)
            self.ab_vwap = self.cpl < self.eth_vwap
        elif self.direction == "long":
            self.several_dir_days = self.prior_high < self.prior_prior_low
            self.vpoc_location = self.prior_vpoc < self.prior_high - 0.33 * (self.prior_high - self.prior_low)
            self.ab_vwap = self.cpl > self.eth_vwap
        # Driving Input
        logic = (
            self.several_dir_days # Prior Two Sessions with 0 Overlap
            and self.vpoc_location # Prior Session VPOC Location
            and self.gap_tier == "Tier_1" # Open in Tier 1 Gap
            and self.ab_vwap # Above / Below ETH VWAP
            and self.posture() in ["PRICE^5D^20D","PRICEv5Dv20D","PRICEv5D^20D", "PRICE^5Dv20D"] # In Postural Extreme
            )    
        
        logger.debug(f" TREV | input | Product: {self.product_name} | LOGIC: {logic}")
        
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
            logger.info(f" TREV | check | Product: {self.product_name} | Note: Condition Not Met")
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
            raise ValueError(f" TREV | discord_message | Note: Invalid direction '{self.direction}'")     

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
