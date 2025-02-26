import logging
import math
import threading
from datetime import datetime
from alertbot.utils import config
from discord_webhook import DiscordEmbed
from alertbot.alerts.base import Base
from alertbot.source.alert_logger import log_alert_async
logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class IBGW(Base):
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
        self.a_high = round(variables.get(f'{product_name}_A_HIGH'), 2)
        self.a_low = round(variables.get(f'{product_name}_A_LOW'), 2)
        self.b_high = round(variables.get(f'{product_name}_B_HIGH'), 2)
        self.b_low = round(variables.get(f'{product_name}_B_LOW'), 2)        
        self.day_high = round(variables.get(f'{product_name}_DAY_HIGH'), 2)
        self.day_low = round(variables.get(f'{product_name}_DAY_LOW'), 2)        
        self.eth_vwap = variables.get(f'{product_name}_ETH_VWAP')
        self.eth_vwap_pt = variables.get(f'{product_name}_ETH_VWAP_P2')         
        
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.delta = self.total_delta()
        self.exp_rng, self.exp_hi, self.exp_lo = self.exp_range() 

# ---------------------------------- Specific Calculations ------------------------------------ #   
    def open_type(self):
        a_period_mid = round(((self.a_high + self.a_low) / 2), 2)
        overlap = max(0, min(self.day_high, self.p_high) - max(self.day_low, self.p_low))
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
        elif (overlap < 0.5 * total_range) and (self.day_open >= self.p_high):
            open_type = "OAOR ^"
        elif (overlap < 0.5 * total_range) and (self.day_open <= self.p_low):
            open_type = "OAOR v"
        else:
            open_type = "Other"
        return open_type 
    
    def prior_session_type(self):
        return
    
    def slope_to_vwap(self):
        # Need to come up with a better solution to estimate VWAP SLOPE
        scale_time = 1.0
        scale_price = 1.0
        delta_price = abs(self.eth_vwap - self.eth_vwap_pt)
        delta_time = 0.1
        
        delta_y = delta_price * scale_price
        delta_x = delta_time * scale_time
        slope = delta_y / delta_x
        
        theta_radians = math.atan(slope)
        theta_degrees = round((math.degrees(theta_radians)), 2)
        if theta_degrees >= 10:
            vwap_type = 'Strong' 
        else:
            vwap_type = 'Flat'
        logger.debug(f" IB_EQUITY | slope_to_vwap | delta_x: {delta_price} | delta_y: {delta_y} | slope: {slope} | theta_degrees: {theta_degrees} | Note: Complete")
        return theta_degrees, vwap_type    
    
    def exp_range(self):

        # Calculation (product specific or Not)
        if not self.prior_close:
            logger.error(f" IBGW | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" IBGW | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)

        if impvol is None:
            raise ValueError(f" IBGW | exp_range | Product: {self.product_name} | Note: Unknown Product")

        exp_range = round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)), 2)
        exp_hi = round(self.prior_close + exp_range, 2)
        exp_lo = round(self.prior_close - exp_range, 2)
        
        logger.debug(f" IBGW | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
        return exp_range, exp_hi, exp_lo
        
        
    def total_delta(self):

        # Calculation (Product Specific or Not)        
        total_delta = self.total_ovn_delta + self.total_rth_delta
        
        logger.debug(f" IBGW | total_delta | TOTAL_DELTA: {total_delta}")
        return total_delta   
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        # Some of the IBGW Critical Criteria Include the Following:
        # 1. IB is narrow to average (below 90% of the IB ATR) 
        # 2. Have not traded 1.5x IB
        # 3. Handle Neutral Scenarios 
        self.used_atr = self.ib_high - self.ib_low
        self.remaining_atr = max((self.ib_atr - self.used_atr), 0)
        
        # Direction Based Logic
        if self.direction == "short":
            self.atr_condition = abs(self.ib_low - self.p_vpoc) <= self.remaining_atr
            self.or_condition = self.cpl < self.orl
        elif self.direction == "long":
            self.atr_condition = abs(self.ib_high - self.p_vpoc) <= self.remaining_atr
            self.or_condition = self.cpl > self.orh
            
        # Driving Input
        logic = (
            self.p_low - (self.exp_rng * 0.15) <= self.day_open <= self.p_high + (self.exp_rng * 0.15) 
            and
            self.p_low + (self.exp_rng * 0.10) <= self.cpl <= self.p_high - (self.exp_rng * 0.10) 
            and
            self.atr_condition 
            and
            abs(self.cpl - self.p_vpoc) > self.exp_rng * 0.1 
            and
            self.or_condition 
            )    
        
        logger.debug(f" IBGW | input | Product: {self.product_name} | LOGIC: {logic}")
        
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
            logger.debug(f" IBGW | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_ib
            end_time = self.equity_close
            logger.debug(f" IBGW | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f" IBGW | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        
        # Check if current time is within the window
        if start_time <= self.current_time <= end_time:
            logger.debug(f" IBGW | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" IBGW | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
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
                logger.debug(f" IBGW | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                
                if self.direction != last_alert: 
                    logger.info(f" IBGW | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Logic For c_50%_expected range left (Use static not directional)
                    if self.atr_condition: 
                        self.c_within_atr = "x" 
                    else:
                        self.c_within_atr = "  "
                    # Logic For one time framing (past 3-4 30 min periods)
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"
                    # logic for clear_magnet (pull from value references and check if they are within 2x IB)
                    self.c_euro_ib = "  "
                    if self.direction == "short" and self.cpl < self.euro_ibl:
                        self.c_euro_ib = "x"
                    elif self.direction == "long" and self.cpl > self.euro_ibh:
                        self.c_euro_ib = "x"
                    # logic for not hit 1.5x IB
                    self.c_euro_ib = "  "
                    if self.direction == "short" and self.cpl < self.euro_ibl:
                        self.c_euro_ib = "x"
                    elif self.direction == "long" and self.cpl > self.euro_ibh:
                        self.c_euro_ib = "x"                        
                    # Logic for SUPPORTIVE directional open
                    self.c_or = "  "
                    if self.direction == "short" and self.cpl < self.orl:
                        self.c_or = "x"
                    elif self.direction == "long" and self.cpl > self.orh:
                        self.c_or = "x"
                    # Logic for IB is narrow to average
                    self.c_between = "  "
                    if self.direction == "short" and self.p_vpoc < self.cpl < self.eth_vwap:
                        self.c_between = "x"
                    elif self.direction == "long" and self.eth_vwap < self.cpl < self.p_vpoc:
                        self.c_between = "x"
                    # Logic for c_euro IB
                    self.c_euro_ib = "  "
                    if self.direction == "short" and self.cpl < self.euro_ibl:
                        self.c_euro_ib = "x"
                    elif self.direction == "long" and self.cpl > self.euro_ibh:
                        self.c_euro_ib = "x"                        
                    # Logic for skew in profile towards IB extreme
                    if abs(self.eth_vwap - self.p_vpoc) <= (self.exp_rng * 0.05):
                        self.c_align = "x"
                    else: 
                        self.c_align = "  "
                    # Logic for IB broke from composite reference, must be 5d, 20d, or 90d (for now)
                    self.c_between = "  "
                    if self.direction == "short" and self.p_vpoc < self.cpl < self.eth_vwap:
                        self.c_between = "x"
                    elif self.direction == "long" and self.eth_vwap < self.cpl < self.p_vpoc:
                        self.c_between = "x"   
                    # Logic for is prior session balanced
                    self.c_between = "  "
                    if self.direction == "short" and self.p_vpoc < self.cpl < self.eth_vwap:
                        self.c_between = "x"
                    elif self.direction == "long" and self.eth_vwap < self.cpl < self.p_vpoc:
                        self.c_between = "x"                          
                                             
                    # Logic for Score 
                    self.score = sum(1 for condition in [self.c_within_atr, self.c_orderflow, self.c_euro_ib, self.c_or, self.c_between, self.c_align] if condition == "x")   
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" IBGW | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" IBGW | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f" IBGW | check | Product: {self.product_name} | Note: Condition Not Met")
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
            raise ValueError(f" IBGW | discord_message | Note: Invalid direction '{self.direction}'")
        
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
        logger.info(f"IBGW | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
        alert_details = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'product': self.product_name,
            'playbook': '#IBGW',
            'direction': self.direction,
            'alert_price': self.cpl,
            'score': self.score,
            'target': self.prior_mid,
        }
        log_alert_async(alert_details)