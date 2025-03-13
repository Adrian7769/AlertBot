import logging
import math
import threading
from datetime import datetime, time
from alertbot.utils import config
from discord_webhook import DiscordEmbed
from alertbot.alerts.base import Base
from alertbot.source.alert_logger import log_alert_async
logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class IBGP(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables (Round All Variables)
        self.p_vpoc = round(self.variables.get(f'{self.product_name}_PRIOR_VPOC'), 2)
        self.day_open = round(self.variables.get(f'{self.product_name}_DAY_OPEN'), 2)
        self.prior_high = round(self.variables.get(f'{self.product_name}_PRIOR_HIGH'), 2)
        self.prior_low = round(self.variables.get(f'{self.product_name}_PRIOR_LOW'), 2)
        self.ib_atr = round(self.variables.get(f'{self.product_name}_IB_ATR'), 2)
        self.euro_ibh = round(self.variables.get(f'{self.product_name}_EURO_IBH'), 2)
        self.euro_ibl = round(self.variables.get(f'{self.product_name}_EURO_IBL'), 2)
        self.orh = round(self.variables.get(f'{self.product_name}_ORH'), 2)
        self.orl = round(self.variables.get(f'{self.product_name}_ORL'), 2)
        self.eth_vwap = round(self.variables.get(f'{self.product_name}_ETH_VWAP'), 2)
        self.rth_vwap = round(self.variables.get(f'{self.product_name}_RTH_VWAP'), 2)
        self.cpl = round(self.variables.get(f'{self.product_name}_CPL'), 2)
        self.total_ovn_delta = round(self.variables.get(f'{self.product_name}_TOTAL_OVN_DELTA'), 2)
        self.total_rth_delta = round(self.variables.get(f'{self.product_name}_TOTAL_RTH_DELTA'), 2)
        self.prior_close = round(self.variables.get(f'{self.product_name}_PRIOR_CLOSE'), 2)
        self.prior_ibh = round(self.variables.get(f'{self.product_name}_PRIOR_IB_HIGH'), 2)
        self.prior_ibl = round(self.variables.get(f'{self.product_name}_PRIOR_IB_LOW'), 2)       
        self.ib_high = round(self.variables.get(f'{product_name}_IB_HIGH'), 2)
        self.ib_low = round(self.variables.get(f'{product_name}_IB_LOW'), 2)
        self.day_high = round(variables.get(f'{product_name}_DAY_HIGH'), 2)
        self.day_low = round(variables.get(f'{product_name}_DAY_LOW'), 2)   
        self.a_high = round(variables.get(f'{product_name}_A_HIGH'), 2)
        self.a_low = round(variables.get(f'{product_name}_A_LOW'), 2)
        self.b_high = round(variables.get(f'{product_name}_B_HIGH'), 2)
        self.b_low = round(variables.get(f'{product_name}_B_LOW'), 2) 
        self.vwap_slope = variables.get(f'{product_name}_VWAP_SLOPE')    
        self.overnight_high = round(variables.get(f'{product_name}_OVNH'), 2)
        self.overnight_low = round(variables.get(f'{product_name}_OVNL'), 2)          
        self.day_vpoc = round(variables.get(f'{product_name}_DAY_VPOC'), 2)                 
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        self.exp_rng, self.exp_hi, self.exp_lo = self.exp_range() 

# ---------------------------------- Specific Calculations ------------------------------------ #   
    def prior_day(self):
        if self.prior_high <= self.prior_ibh and self.prior_low >= self.prior_ibl:
            day_type = "Rotational"
        elif (self.prior_low < self.prior_ibl and self.prior_high > self.prior_ibh and 
            self.prior_close >= self.prior_ibh + 0.5 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Directional"
        elif (self.prior_low < self.prior_ibl and self.prior_high > self.prior_ibh and 
            self.prior_close <= self.prior_ibl - 0.5 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Directional"
        elif (self.prior_high > self.prior_ibh and self.prior_low < self.prior_ibl and
            self.prior_close >= (self.prior_ibl - 0.5 * (self.prior_ibh - self.prior_ibl)) and
            self.prior_close <= (self.prior_ibh + 0.5 * (self.prior_ibh - self.prior_ibl))):
            day_type = "Rotational"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and 
            self.prior_high <= self.prior_ibh + 0.5 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Rotational"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and 
            self.prior_low >= self.prior_ibl - 0.5 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Rotational"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and
            self.prior_high >= self.prior_ibh + (self.prior_ibh - self.prior_ibl) and
            self.prior_close >= self.prior_ibh + (self.prior_ibh - self.prior_ibl)):
            day_type = "Directional"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and
            self.prior_close <= self.prior_ibh + (self.prior_ibh - self.prior_ibl) and
            self.prior_high >= self.prior_ibh + 1.25 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Directional"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and
            self.prior_low <= self.prior_ibl - (self.prior_ibh - self.prior_ibl) and
            self.prior_close <= self.prior_ibl - (self.prior_ibh - self.prior_ibl)):
            day_type = "Directional"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and
            self.prior_close >= self.prior_ibl - (self.prior_ibh - self.prior_ibl) and
            self.prior_low <= self.prior_ibl - 1.25 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Directional"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and
            self.prior_high >= self.prior_ibh + 0.5 * (self.prior_ibh - self.prior_ibl) and
            self.prior_high <= self.prior_ibh + (self.prior_ibh - self.prior_ibl)):
            day_type = "Rotational"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and
            self.prior_high >= self.prior_ibh + (self.prior_ibh - self.prior_ibl) and
            self.prior_close <= self.prior_ibh + (self.prior_ibh - self.prior_ibl)):
            day_type = "Directional"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and  # IB EXTENSION DOWN
            self.prior_low <= self.prior_ibl - 0.5 * (self.prior_ibh - self.prior_ibl) and # LOW IS BELOW 1.5x IB
            self.prior_low >= self.prior_ibl - (self.prior_ibh - self.prior_ibl)): # LOW IS ABOVE 2x IB
            day_type = "Rotational"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and # IB EXTENSION DOWN
            self.prior_low <= self.prior_ibl - (self.prior_ibh - self.prior_ibl) and # LOW IS BELOW 2x IB
            self.prior_close >= self.prior_ibl - (self.prior_ibh - self.prior_ibl)): # CLOSE IS WITHIN 2x IB
            day_type = "Directional"
        else:
            day_type = "Other"
        logger.debug(f" IBGW | prior_day | Prior Day Type: {day_type}")
        return day_type
    def open_type(self):
        a_period_mid = round(((self.a_high + self.a_low) / 2), 2)
        overlap = max(0, min(self.day_high, self.prior_high) - max(self.day_low, self.prior_low))
        total_range = self.day_high - self.day_low
        if self.day_open == self.a_high and (self.b_high < a_period_mid):
            open_type = "OD v"
        elif self.day_open == self.a_low and (self.b_low > a_period_mid):
            open_type = "OD ^"
        elif (self.day_open > a_period_mid) and (self.b_high < a_period_mid):
            open_type = "OTD v"
        elif (self.day_open < a_period_mid) and (self.b_low > a_period_mid):
            open_type = "OTD ^"
        elif (self.day_open > a_period_mid) and (self.b_low > a_period_mid) and (self.b_high > self.orh):
            open_type = "ORR ^"
        elif (self.day_open < a_period_mid) and (self.b_high < a_period_mid) and (self.b_low < self.orl):
            open_type = "ORR v"
        elif overlap >= 0.5 * total_range:
            open_type = "OAIR"
        elif (overlap < 0.5 * total_range) and (self.day_open >= self.prior_high):
            open_type = "OAOR ^"
        elif (overlap < 0.5 * total_range) and (self.day_open <= self.prior_low):
            open_type = "OAOR v"
        else:
            open_type = "Other"
        return open_type 
    def exp_range(self):

        # Calculation (product specific or Not)
        if not self.prior_close:
            logger.error(f" IBGP | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" IBGP | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)

        if impvol is None:
            raise ValueError(f"IBGP | exp_range | Product: {self.product_name} | Note: Unknown Product")

        exp_range = round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)), 2)
        exp_hi = round(self.prior_close + exp_range, 2)
        exp_lo = round(self.prior_close - exp_range, 2)
        
        logger.debug(f" IBGP | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
        return exp_range, exp_hi, exp_lo
    def one_time_framing(self):
        if self.product_name == "CL":
            period_times = {
                'A': time(9, 0), 'B': time(9, 30), 'C': time(10, 0),
                'D': time(10, 30), 'E': time(11, 0), 'F': time(11, 30),
                'G': time(12, 0), 'H': time(12, 30), 'I': time(13, 0),
                'J': time(13, 30), 'K': time(14, 0),
            }
        else:
            period_times = {
                'A': time(9, 30), 'B': time(10, 0), 'C': time(10, 30),
                'D': time(11, 0), 'E': time(11, 30), 'F': time(12, 0),
                'G': time(12, 30), 'H': time(13, 0), 'I': time(13, 30),
                'J': time(14, 0), 'K': time(14, 30), 'L': time(15, 0),
                'M': time(15, 30),
            }
        
        now = datetime.now(self.est).time()
        sorted_periods = sorted(period_times.items(), key=lambda x: x[1])
        finished_periods = [p for p, t in sorted_periods if t <= now]
        if len(finished_periods) < 2:
            return False
        last_two = finished_periods[-2:]
        period1 = last_two[0]
        period2 = last_two[1]
        p1_high = self.variables.get(f"{self.product_name}_{period1}_HIGH")
        p1_low = self.variables.get(f"{self.product_name}_{period1}_LOW")
        p2_high = self.variables.get(f"{self.product_name}_{period2}_HIGH")
        p2_low = self.variables.get(f"{self.product_name}_{period2}_LOW")
        if None in (p1_high, p1_low, p2_high, p2_low):
            return False
        p1_high = round(p1_high, 2)
        p1_low = round(p1_low, 2)
        p2_high = round(p2_high, 2)
        p2_low = round(p2_low, 2)
        current_high = self.day_high
        current_low = self.day_low
        if self.direction == "long":
            if p2_high > p1_high and p2_low > p1_low:
                if current_high > p2_high and current_low > p2_low:
                    return True
                else:
                    return False
            else:
                return False
        elif self.direction == "short":
            if p2_high < p1_high and p2_low < p1_low:
                if current_high < p2_high and current_low < p2_low:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False    
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        if self.direction == "short":
            self.ib_ext_half = self.day_low >= self.ib_low - 0.5 * (self.ib_high-self.ib_low)
            if self.cpl > self.day_vpoc and (self.cpl > self.eth_vwap or self.cpl > self.rth_vwap):
                self.favorable_price = True
            else:
                self.favorable_price = False
        elif self.direction == "long":
            self.ib_ext_half = self.day_high <= self.ib_high + 0.5 * (self.ib_high-self.ib_low)
            if self.cpl < self.day_vpoc and (self.cpl < self.eth_vwap or self.cpl < self.rth_vwap):
                self.favorable_price = True
            else:
                self.favorable_price = False
        logic = (
            self.ib_high - self.ib_low / self.ib_atr >= 1.00
            and self.ib_ext_half
            and not self.one_time_framing()
            and self.favorable_price
            )    
        logger.debug(f" IBGP | input | Product: {self.product_name} | LOGIC: {logic}")
        return logic
    
# ---------------------------------- Opportunity Window ------------------------------------ #   
    def time_window(self):
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
        if self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_ib
            lunch_start = self.equity_lunch_start
            lunch_end = self.equity_lunch_end
            close_time = self.equity_close
            if (start_time <= self.current_time <= lunch_start) or \
            (lunch_end <= self.current_time <= close_time):
                logger.debug(f"Within equity alert window: {self.current_time}")
                return True
            else:
                logger.debug(f"Outside equity alert window: {self.current_time}")
                return False
        elif self.product_name == 'CL':
            if self.crude_ib <= self.current_time <= self.crude_close:
                logger.debug(f"Within crude alert window: {self.current_time}")
                return True
            else:
                logger.debug(f"Outside crude alert window: {self.current_time}")
                return False
        else:
            logger.warning(f"No time window defined for product: {self.product_name}")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
        if self.day_low < self.ib_low:
            self.direction = "short"
        elif self.day_high > self.ib_high:
            self.direction = "long"
        elif self.day_low < self.ib_low and self.day_high > self.ib_high:
            logger.debug(f" IBGP | check | Product: {self.product_name} | Note: Neutral Behavior Detected, Returning")
            return
        else:
            logger.debug(f" IBGP | check | Product: {self.product_name} | Note: No IB Extension Detected, Returning.")
            return
        # Driving Input
        if self.time_window() and self.input():
            
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)   
                logger.debug(f" IBGP | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                if self.direction != last_alert: 
                    logger.info(f" IBGP | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Critical Criteria
                    self.c_favorable_price = "x"
                    self.c_rotational_current_session = "x"
                    self.c_wide_ib = "x"
                    self.c_ib_ext_half = "x"
                    # Logic for Non-Directional Open
                    if self.open_type() == "OAIR":
                        self.c_non_dir_open = "x"
                    else:
                        self.c_non_dir_open = "  "
                    # Logic for using 75% of Expected Range
                    self.used_range = max(self.overnight_high, self.day_high) - min(self.overnight_low, self.day_low)
                    self.remaining_range = self.exp_rng - self.used_range
                    if self.remaining_range >= 0.75 * self.exp_rng:
                        self.c_exp_rng = "x"
                    else:
                        self.c_exp_rng = "  "
                    # Logic for c_euro IB
                    if self.direction == "short": 
                        if self.cpl < self.euro_ibl:
                            self.c_euro_ib = "x" 
                        else:
                            self.c_euro_ib = "  "
                    elif self.direction == "long":
                        if self.cpl > self.euro_ibh:
                            self.c_euro_ib = "x" 
                        else:
                            self.c_euro_ib = "  "                     
                    # Logic DVPOC is in middle of IB Range
                    if self.ib_low + round(0.25(self.ib_high - self.ib_low), 2) <= self.day_vpoc <= self.ib_high - round(0.25(self.ib_high - self.ib_low), 2):
                        self.c_vpoc_in_middle = "x" 
                    else:
                        self.c_vpoc_in_middle = "  "
                    # Logic for is prior session directional
                    if self.prior_day() == "Directional":
                        self.c_directional = "x"
                    else:
                        self.c_directional = "  "  
                    # Logic for Noticeable Slope to VWAP
                    if self.direction == "short": 
                        if self.vwap_slope < -0.03:
                            self.c_vwap_slope = "x" 
                        else:
                            self.c_vwap_slope = "  "
                    elif self.direction == "long":
                        if self.vwap_slope > 0.03:
                            self.c_vwap_slope = "x" 
                        else:
                            self.c_vwap_slope = "  "                                        
                    # Logic for Score 
                    self.score = sum(1 for condition in [self.c_favorable_price, self.c_rotational_current_session, self.c_euro_ib, self.c_vpoc_in_middle, self.c_ib_ext_half, self.c_wide_ib, self.c_exp_rng, self.c_non_dir_open, self.c_directional] if condition == "x")   
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" IBGP | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" IBGP | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f" IBGP | check | Product: {self.product_name} | Note: Condition Not Met")
# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):

        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        direction_settings = {
            "long": {
                "dir_indicator": "^",
                "destination": "IBH",
                "mid": "Above",
                "mid-o": "Below",
            },
            "short": {
                "dir_indicator": "v",
                "destination": "IBL",
                "mid": "Below",
            }
        }
 
        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" TRCT | discord_message | Note: Invalid direction '{self.direction}'")
        
        if self.open_type() == "OAIR":
            ot = self.open_type()
            colon = ":"
        else:
            ot = ""   
            colon = ""      
        if self.direction == "long":
            if self.vwap_slope > 0.03:
                inline_text = f"Noticeable Slope to dVWAP: ({self.vwap_slope*100})\n"
            else:
                inline_text = f"Noticeable Slope to dVWAP \n"
        elif self.direction == "short":
            if self.vwap_slope < -0.03:
                inline_text = f"Noticeable Slope to dVWAP: ({self.vwap_slope*100})\n"
            else:
                inline_text = f"Noticeable Slope to dVWAP \n"

        # Title Construction with Emojis
        title = f"**{self.product_name} - Playbook Alert** - **IBGP {settings['dir_indicator']}**"
    
        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: Depending on Entry, Developing VWAP/VPOC or {settings['destination']}\n"
                f"**Risk**: Wrong if Auction goes neutral\n"
                f"**Driving Input**: This trade seeks entry with the participants who extended the Initial Balance, either at the developing value or favorable to it.\n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()

        # Criteria Header
        embed.add_embed_field(name="**Criteria**", value="\u200b", inline=False)

        # Criteria Details
        criteria = (
            f"• [{self.c_favorable_price}] Price is favorable to Value: At or {settings['mid-o']}\n"
            f"• [{self.c_non_dir_open}] Non-Directional Open{colon} {ot}\n"
            f"• [{self.c_rotational_current_session}] Rotational Day (Not One-Time Framing) \n"
            f"• [{self.c_exp_rng}] Achieved 75% of Expected Range \n"
            f"• [{self.c_wide_ib}] IB is Average to Wide: ({(self.ib_high - self.ib_low / self.ib_atr)*100}%) \n"
            f"• [{self.c_vpoc_in_middle}] dVPOC is in middle of IB Range \n"
            f"• [{self.c_directional}] Prior Session was Directional \n"
            f"• [{self.c_vwap_slope}] {inline_text}"
            f"• [{self.c_ib_ext_half}] Have Not Hit 1.5x {settings['destination']}\n"
            f"• [{self.c_euro_ib}] {settings['mid']} Euro {settings['destination']}\n"
        )
        embed.add_embed_field(name="\u200b", value=criteria, inline=False)

        # Playbook Score
        embed.add_embed_field(name="**Playbook Score**", value=f"_{self.score} / 10_", inline=False)
        
        # Alert Time and Price Context
        alert_time_text = f"**Alert Time / Price**: _{alert_time_formatted} EST | {self.cpl}_"
        embed.add_embed_field(name="\u200b", value=alert_time_text, inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"IBGP | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
        alert_details = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'product': self.product_name,
            'playbook': '#IBGP',
            'direction': self.direction,
            'alert_price': self.cpl,
            'score': self.score,
            'target': None,
        }
        log_alert_async(alert_details)