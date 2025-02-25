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

class DATR(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables specific to the product
        self.prior_close = round(self.variables.get(f'{self.product_name}_PRIOR_CLOSE'), 2)
        self.day_open = round(self.variables.get(f'{self.product_name}_DAY_OPEN'), 2)
        self.prior_high = round(self.variables.get(f'{self.product_name}_PRIOR_HIGH'), 2)
        self.prior_low = round(self.variables.get(f'{self.product_name}_PRIOR_LOW'), 2)
        self.prior_ibh = round(self.variables.get(f'{self.product_name}_PRIOR_IB_HIGH'), 2)
        self.prior_ibl = round(self.variables.get(f'{self.product_name}_PRIOR_IB_LOW'), 2)
        self.total_ovn_delta = round(self.variables.get(f'{self.product_name}_TOTAL_OVN_DELTA'), 2)
        self.total_rth_delta = round(self.variables.get(f'{self.product_name}_TOTAL_RTH_DELTA'), 2)
        self.prior_vpoc = round(self.variables.get(f'{self.product_name}_PRIOR_VPOC'), 2)  
        self.eth_vwap = round(self.variables.get(f'{self.product_name}_ETH_VWAP'), 2)       
        self.cpl = round(self.variables.get(f'{self.product_name}_CPL'), 2)
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.delta = self.total_delta()
        self.exp_rng = self.exp_range()
        self.prior_day_type = self.prior_day()
        self.prior_mid = ((self.prior_high + self.prior_low) / 2)

# ---------------------------------- Specific Calculations ------------------------------------ #   
    def exp_range(self):

        # Calculation (product specific or Not)
        if not self.prior_close:
            logger.error(f" DATR | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" DATR | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        
        if self.product_name == 'ES':
            exp_range = round(((self.prior_close * (self.es_impvol/100)) * math.sqrt(1/252)) , 2)
            exp_hi = (self.prior_close + exp_range)
            exp_lo = (self.prior_close - exp_range)
            
            logger.debug(f" DATR | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
            return exp_range
        
        elif self.product_name == 'NQ':
            exp_range = round(((self.prior_close * (self.nq_impvol/100)) * math.sqrt(1/252)) , 2)
            exp_hi = (self.prior_close + exp_range)
            exp_lo = (self.prior_close - exp_range)
            
            logger.debug(f" DATR | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
            return exp_range
        
        elif self.product_name == 'RTY':
            exp_range = round(((self.prior_close * (self.rty_impvol/100)) * math.sqrt(1/252)) , 2)
            exp_hi = (self.prior_close + exp_range)
            exp_lo = (self.prior_close - exp_range)
        
            logger.debug(f" DATR | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
            return exp_range
        
        elif self.product_name == 'CL':
            exp_range = round(((self.prior_close * (self.cl_impvol/100)) * math.sqrt(1/252)) , 2)
            exp_hi = (self.prior_close + exp_range)
            exp_lo = (self.prior_close - exp_range)
            
            logger.debug(f" DATR | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
            return exp_range       
        else:
            raise ValueError(f" DATR | exp_range | Product: {self.product_name} | Note: Unknown Product")
        
    def total_delta(self):

        # Calculation (Product Specific or Not)        
        total_delta = self.total_ovn_delta + self.total_rth_delta
        
        logger.debug(f" DATR | total_delta | TOTAL_DELTA: {total_delta}")
        return total_delta 
      
    def prior_day(self):
        
        
        if self.prior_high <= self.prior_ibh and self.prior_low >= self.prior_ibl:
            day_type = "Non-Trend"
        elif (self.prior_low < self.prior_ibl and self.prior_high > self.prior_ibh and 
            self.prior_close >= self.prior_ibh + 0.5 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Neutral Extreme ^"
        elif (self.prior_low < self.prior_ibl and self.prior_high > self.prior_ibh and 
            self.prior_close <= self.prior_ibl - 0.5 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Neutral Extreme v"
        elif (self.prior_high > self.prior_ibh and self.prior_low < self.prior_ibl and
            self.prior_close >= (self.prior_ibl - 0.5 * (self.prior_ibh - self.prior_ibl)) and
            self.prior_close <= (self.prior_ibh + 0.5 * (self.prior_ibh - self.prior_ibl))):
            day_type = "Neutral Center"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and 
            self.prior_high <= self.prior_ibh + 0.5 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Normal Day ^"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and 
            self.prior_low >= self.prior_ibl - 0.5 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Normal Day v"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and
            self.prior_high >= self.prior_ibh + (self.prior_ibh - self.prior_ibl) and
            self.prior_close >= self.prior_ibh + (self.prior_ibh - self.prior_ibl)):
            day_type = "Trend ^"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and
            self.prior_close <= self.prior_ibh + (self.prior_ibh - self.prior_ibl) and
            self.prior_high >= self.prior_ibh + 1.25 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Trend ^"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and
            self.prior_low <= self.prior_ibl - (self.prior_ibh - self.prior_ibl) and
            self.prior_close <= self.prior_ibl - (self.prior_ibh - self.prior_ibl)):
            day_type = "Trend v"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and
            self.prior_close >= self.prior_ibl - (self.prior_ibh - self.prior_ibl) and
            self.prior_low <= self.prior_ibl - 1.25 * (self.prior_ibh - self.prior_ibl)):
            day_type = "Trend v"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and
            self.prior_high >= self.prior_ibh + 0.5 * (self.prior_ibh - self.prior_ibl) and
            self.prior_high <= self.prior_ibh + (self.prior_ibh - self.prior_ibl)):
            day_type = "Normal Var ^"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and
            self.prior_high >= self.prior_ibh + (self.prior_ibh - self.prior_ibl) and
            self.prior_close <= self.prior_ibh + (self.prior_ibh - self.prior_ibl)):
            day_type = "Normal Var ^"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and
            self.prior_low <= self.prior_ibl - 0.5 * (self.prior_ibh - self.prior_ibl) and
            self.prior_low >= self.prior_ibl - (self.prior_ibh - self.prior_ibl)):
            day_type = "Normal Var v"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and
            self.prior_low <= self.prior_ibl - (self.prior_ibh - self.prior_ibl) and
            self.prior_close >= self.prior_ibl - (self.prior_ibh - self.prior_ibl)):
            day_type = "Normal Var v"
        else:
            day_type = "Other"
            
        logger.debug(f" DATR | total_delta | Prior Day Type: {day_type}")
        
        return day_type
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        tolerance = (self.exp_rng * 0.15)
        prior_mid = ((self.prior_high + self.prior_low) / 2)
        logic = False
        if (self.prior_high - tolerance) > self.day_open > (self.prior_low + tolerance):
            if self.direction == 'Higher':
                logic = (
                    self.cpl > prior_mid 
                    and
                    self.prior_vpoc > ((self.prior_high + prior_mid) / 2) 
                )
            elif self.direction == 'Lower':
                logic = (
                    self.cpl < prior_mid
                    and 
                    self.prior_vpoc < ((self.prior_low + prior_mid) / 2)
                )
            
        logger.debug(f" DATR | input | Product: {self.product_name} | LOGIC: {logic}")
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
            logger.debug(f" DATR | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_open
            end_time = self.equity_close
            logger.debug(f" DATR | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f" DATR | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        
        # Check if current time is within the window
        if start_time <= self.current_time <= end_time:
            logger.debug(f" DATR | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" DATR | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
        
        # Define Direction
        self.direction = None
        if self.prior_day_type == 'Trend ^':
            self.direction = 'Higher'
        elif self.prior_day_type == 'Trend v':
            self.direction = 'Lower'
            
        self.color = "red" if self.direction == "Lower" else "green"
           
        # Driving Input
        if self.input() and self.time_window():
            
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)   
                logger.debug(f" DATR | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                
                if self.direction != last_alert: 
                    logger.info(f" DATR | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Logic for c_trend
                    self.c_trend = "x"                    
                    # Logic for c_open
                    if self.prior_low < self.day_open < self.prior_high:
                        self.c_open = "x"
                    else:
                        self.c_open = "  "
                    # Logic For c_orderflow
                    self.c_orderflow = "  "
                    if self.direction == "Lower" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "Higher" and self.delta > 0:
                        self.c_orderflow = "x"
                    # Logic for c_vwap
                    self.c_vwap = "  "
                    if self.direction == "Lower" and self.cpl < self.eth_vwap:
                        self.c_vwap = "x"
                    elif self.direction == "Higher" and self.cpl > self.eth_vwap:
                        self.c_vwap = "x"
                    # Logic for c_prior_vpoc
                    self.c_prior_vpoc = "  "
                    if self.direction == "Lower" and self.prior_vpoc < self.prior_mid:
                        self.c_prior_vpoc = "x"
                    elif self.direction == "Higher" and self.prior_vpoc > self.prior_mid:
                        self.c_prior_vpoc = "x"
                    # Logic for c_hwb
                    self.c_hwb = "  "
                    if self.direction == "Lower" and self.cpl < self.prior_mid:
                        self.c_hwb = "x"
                    elif self.direction == "Higher" and self.cpl > self.prior_mid:
                        self.c_hwb = "x"
                    # Logic for Score 
                    self.score = sum(1 for condition in [self.c_trend, self.c_orderflow, self.c_open, self.c_vwap, self.c_prior_vpoc, self.c_hwb] if condition == "x")   
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" DATR | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" DATR | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f" DATR | check | Product: {self.product_name} | Note: Condition Not Met")
# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):
        
        pro_color = self.product_color.get(self.product_name)
        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        
        direction_settings = { 
            "Higher": {
                "pv_indicator": "^",
                "risk": "above",
                "trend": "higher",
                "large": "large_",
                "c_hwb": "Above",
                "c_prior_vpoc": "above",
                "c_vwap": "Above",
            },
            "Lower": {
                "pv_indicator": "v",
                "risk": "below",
                "trend": "lower",
                "large": "",
                "c_hwb": "Below",
                "c_prior_vpoc": "below",
                "c_vwap": "Below",
            }
        }

        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" DATR | discord_message | Note: Invalid direction '{self.direction}'")

        # Title Construction with Emojis
        title = f":large_{pro_color}_square: **{self.product_name} - Playbook Alert** :{settings['large']}{self.color}_circle: **DATR {settings['pv_indicator']}**"

        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: _{self.prior_low} (Prior Session Low)_\n"
                f"**Risk**: _Wrong if price accepts {settings['risk']} HWB of prior session_\n"
                f"**Driving Input**: _Prior Day was a trend {settings['trend']}_\n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()  # Automatically sets the timestamp to current time

        # Criteria Header
        embed.add_embed_field(name="**Criteria**", value="\u200b", inline=False)

        # Criteria Details
        criteria = (
            f"• **[{self.c_trend}]** Prior Day was Trend Day\n"
            f"• **[{self.c_open}]** Open Inside of Prior Range\n"
            f"• **[{self.c_hwb}]** {settings['c_hwb']} HWB of Prior Day Range\n"
            f"• **[{self.c_prior_vpoc}]** Prior Day VPOC {settings['c_prior_vpoc']} HWB of Prior Day Range\n"
            f"• **[{self.c_vwap}]** {settings['c_vwap']} ETH VWAP\n"
            f"• **[{self.c_orderflow}]** Supportive Cumulative Delta (*_{self.delta}_*)\n"
        )
        embed.add_embed_field(name="\u200b", value=criteria, inline=False)

        # Playbook Score
        embed.add_embed_field(name="**Playbook Score**", value=f"_{self.score} / 6_", inline=False)
        
        # Alert Time and Price Context
        embed.add_embed_field(name="**Alert Time / Price**", value=f"_{alert_time_formatted}_ EST | {self.cpl}_", inline=False)

        return embed   
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)  
        logger.info(f" DATR | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
            