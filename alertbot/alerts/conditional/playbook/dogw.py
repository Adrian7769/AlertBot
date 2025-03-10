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

class DOGW(Base):
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
        self.a_high = round(variables.get(f'{product_name}_A_HIGH'), 2)
        self.a_low = round(variables.get(f'{product_name}_A_LOW'), 2)
        self.b_high = round(variables.get(f'{product_name}_B_HIGH'), 2)
        self.b_low = round(variables.get(f'{product_name}_B_LOW'), 2)
        self.eth_vwap = round(self.variables.get(f'{self.product_name}_ETH_VWAP'), 2)
        self.cpl = round(self.variables.get(f'{self.product_name}_CPL'), 2)
        self.total_ovn_delta = round(self.variables.get(f'{self.product_name}_TOTAL_OVN_DELTA'), 2)
        self.total_rth_delta = round(self.variables.get(f'{self.product_name}_TOTAL_RTH_DELTA'), 2)
        self.prior_close = round(self.variables.get(f'{self.product_name}_PRIOR_CLOSE'), 2)
        self.ib_high = round(self.variables.get(f'{product_name}_IB_HIGH'), 2)
        self.ib_low = round(self.variables.get(f'{product_name}_IB_LOW'), 2)
        self.rvol = round(self.variables.get(f'{product_name}_RVOL'), 2)
        self.day_high = round(variables.get(f'{product_name}_DAY_HIGH'), 2)
        self.day_low = round(variables.get(f'{product_name}_DAY_LOW'), 2)        
        self.vwap_slope = variables.get(f'{product_name}_VWAP_SLOPE')
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.delta = self.total_delta()
        self.exp_rng, self.exp_hi, self.exp_lo = self.exp_range() 
        self.opentype = self.open_type_algorithm()

    # ---------------------------------- Specific Calculations ------------------------------------ #   
    def open_type_algorithm(self): # This probably needs to be refined!
        a_period_mid = round(((self.a_high + self.a_low) / 2), 2)
        a_period_range = self.a_high - self.a_low
        five_pct = 0.05 * a_period_range
        fifteen_pct = 0.15 * a_period_range
        twentyfive_pct = 0.25 * a_period_range
        top_0 = self.a_high
        top_5 = self.a_high - five_pct
        top_15 = self.a_high - fifteen_pct
        top_25 = self.a_high - twentyfive_pct
        bottom_0 = self.a_low
        bottom_5 = self.a_low + five_pct
        bottom_15 = self.a_low + fifteen_pct
        bottom_25 = self.a_low + twentyfive_pct
        open_type = "Wait" 
        
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
        
        if self.product_name == 'CL':
            b_period_start_time = time(9, 30)  
        else:
            b_period_start_time = time(10, 0)  
            
        b_period_active = self.current_time >= b_period_start_time
        overlap_pct = 0
        
        if b_period_active and self.b_high > 0 and self.b_low > 0:
            overlap = max(0, min(self.day_high, self.prior_high) - max(self.day_low, self.prior_low))
            total_range = self.day_high - self.day_low
            overlap_pct = overlap / total_range if total_range > 0 else 0
            logger.debug(f"DOGW | open_type_algorithm | Overlap: {overlap} | Total Range: {total_range} | Overlap %: {overlap_pct}")
        else:
            if b_period_active:
                logger.debug("DOGW | open_type_algorithm | B period data not yet available (b_high or b_low is 0).")
        if not b_period_active:
            if self.day_open == self.a_high:
                open_type = "OD v"
                logger.debug("DOGW | open_type_algorithm | Condition met: OD v")
            elif self.day_open == self.a_low:
                open_type = "OD ^"
                logger.debug("DOGW | open_type_algorithm | Condition met: OD ^")
            elif top_5 < self.day_open < top_0:
                open_type = "OTD v"
                logger.debug("DOGW | open_type_algorithm | Condition met: OTD v")
            elif bottom_0 < self.day_open < bottom_5:
                open_type = "OTD ^"
                logger.debug("DOGW | open_type_algorithm | Condition met: OTD ^")
            else:
                # Only trigger OAOR if there is a tier 2 gap present?
                logger.debug("DOGW | open_type_algorithm | Condition met: Wait (A period no specific open type)")
        else:
            if self.b_high == 0 and self.b_low == 0:
                open_type = "Wait"
                logger.debug("DOGW | open_type_algorithm | B period data not available yet. Open type set to Wait.")
            else:
                if self.day_open == self.a_high:
                    open_type = "OD v"
                    logger.debug("DOGW | open_type_algorithm | Condition met: OD v")
                elif self.day_open == self.a_low:
                    open_type = "OD ^"
                    logger.debug("DOGW | open_type_algorithm | Condition met: OD ^")
                elif top_5 < self.day_open < top_0:
                    open_type = "OTD v"
                    logger.debug("DOGW | open_type_algorithm | Condition met: OTD v")
                elif bottom_0 < self.day_open < bottom_5:
                    open_type = "OTD ^"
                    logger.debug("DOGW | open_type_algorithm | Condition met: OTD ^")
                elif top_15 < self.day_open <= top_5 and self.b_high < a_period_mid:
                    open_type = "OTD v"
                    logger.debug("DOGW | open_type_algorithm | Condition met: OTD v (top_15 < day_open <= top_5 and b_high < a_period_mid)")
                elif bottom_5 < self.day_open <= bottom_15 and self.b_low > a_period_mid:
                    open_type = "OTD ^"
                    logger.debug("DOGW | open_type_algorithm | Condition met: OTD ^ (bottom_5 < day_open <= bottom_15 and b_low > a_period_mid)")
                elif top_25 < self.day_open <= top_15 and self.b_high < bottom_25:
                    open_type = "OTD v"
                    logger.debug("DOGW | open_type_algorithm | Condition met: OTD v (top_25 < day_open <= top_15 and b_high < bottom_25)")
                elif bottom_15 <= self.day_open < bottom_25 and self.b_low > top_25:
                    open_type = "OTD ^"
                    logger.debug("DOGW | open_type_algorithm | Condition met: OTD ^ (bottom_15 <= day_open < bottom_25 and b_low > top_25)")
                elif self.day_open > top_25 and self.b_low > a_period_mid:
                    open_type = "ORR ^"
                    logger.debug("DOGW | open_type_algorithm | Condition met: ORR ^ (day_open > top_25 and b_low > a_period_mid)")
                elif self.day_open < bottom_25 and self.b_high < a_period_mid:
                    open_type = "ORR v"
                    logger.debug("DOGW | open_type_algorithm | Condition met: ORR v (day_open < bottom_25 and b_high < a_period_mid)")
                else:
                    if overlap_pct >= 0.25:
                        open_type = "OAIR"
                    elif overlap_pct < 0.25:
                        if self.day_open > self.prior_high:
                            open_type = "OAOR ^"
                        elif self.day_open < self.prior_low:
                            open_type = "OAOR v"
                        else:
                            open_type = "OAIR"        
        logger.debug(f"DOGW | open_type_algorithm | Determined Open Type: {open_type}")
        return open_type    
        
    def exp_range(self):

        # Calculation (product specific or Not)
        if not self.prior_close:
            logger.error(f"DOGW | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f"DOGW | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        
        if self.product_name == 'ES':
            exp_range = round(((self.prior_close * (self.es_impvol/100)) * math.sqrt(1/252)) , 2)
            exp_hi = (self.prior_close + exp_range)
            exp_lo = (self.prior_close - exp_range)
            
            logger.debug(f"DOGW | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
            return exp_range, exp_hi, exp_lo
        
        elif self.product_name == 'NQ':
            exp_range = round(((self.prior_close * (self.nq_impvol/100)) * math.sqrt(1/252)) , 2)
            exp_hi = (self.prior_close + exp_range)
            exp_lo = (self.prior_close - exp_range)
            
            logger.debug(f"DOGW | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
            return exp_range, exp_hi, exp_lo
        
        elif self.product_name == 'RTY':
            exp_range = round(((self.prior_close * (self.rty_impvol/100)) * math.sqrt(1/252)) , 2)
            exp_hi = (self.prior_close + exp_range)
            exp_lo = (self.prior_close - exp_range)
        
            logger.debug(f"DOGW | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
            return exp_range, exp_hi, exp_lo
        
        elif self.product_name == 'CL':
            exp_range = round(((self.prior_close * (self.cl_impvol/100)) * math.sqrt(1/252)) , 2)
            exp_hi = (self.prior_close + exp_range)
            exp_lo = (self.prior_close - exp_range)
            
            logger.debug(f"DOGW | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
            return exp_range, exp_hi, exp_lo
        
        else:
            raise ValueError(f"DOGW | exp_range | Product: {self.product_name} | Note: Unknown Product")    
      
    def total_delta(self):
        logger.debug(f"DOGW | total_delta | Product: {self.product_name} | Note: Running")       
        total_delta = self.total_ovn_delta + self.total_rth_delta   
        logger.debug(f"DOGW | total_delta | TOTAL_DELTA: {total_delta}")
        return total_delta   
        
    # ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self): # This is where the critical criteria go
        
        self.used_atr = self.ib_high - self.ib_low
        self.remaining_atr = max((self.ib_atr - self.used_atr), 0)
        self.target = f"40% of average IB Left to target"
        
        # Direction Based Logic
        if self.direction == "short":
            self.or_condition = self.cpl < self.orl
        elif self.direction == "long":
            self.or_condition = self.cpl > self.orh
        else:
            self.atr_condition = False
            self.or_condition = False
                        
        # Driving Input
        logic = (
            self.opentype
            in 
            ["OD v", "OD ^", "OTD v", "OTD ^", "ORR ^", "ORR v", "OAOR ^", "OAOR v"]
            and 
            self.or_condition
            and
            self.atr_condition
            ) 
        
        logger.debug(f"DOGW | input | Product: {self.product_name} | LOGIC: {logic}")
        
        return logic
    
    # ---------------------------------- Opportunity Window ------------------------------------ #   
    def time_window(self):
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
        if self.product_name == 'CL':
            start_time = self.crude_dogw_start
            end_time = self.crude_ib
            logger.debug(f"DOGW | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_dogw_start
            end_time = self.equity_ib
            logger.debug(f"DOGW | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f"DOGW | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        if start_time <= self.current_time <= end_time:
            logger.debug(f"DOGW | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f"DOGW | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False
    
    # ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
        
        # Define Direction
        self.direction = "short" if self.opentype in ["OD v", "OTD v", "ORR v", "OAOR v"] else "long"
        self.color = "red" if self.direction == "short" else "green"
    
        # Driving Input
        if self.input() and self.time_window():
            
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)   
                logger.debug(f"DOGW | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                
                if self.direction != last_alert: 
                    logger.info(f"DOGW | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Logic 40% Atr Left
                    if self.atr_condition: 
                        self.c_within_atr = "x" 
                    else:
                        self.c_within_atr = "  "
                    # Logic For VWAP Slope
                    self.c_between = "  "
                    if self.direction == "short" and self.p_vpoc < self.cpl < self.eth_vwap:
                        self.c_between = "x"
                    elif self.direction == "long" and self.eth_vwap < self.cpl < self.p_vpoc:
                        self.c_between = "x"
                    # Logic for 50% of ETH Expected Range Left
                    if abs(self.eth_vwap - self.p_vpoc) <= (self.exp_rng * 0.05):
                        self.c_align = "x"
                    else: 
                        self.c_align = "  "  
         
                    # Logic For Orderflow
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"
                    # Logic For euro IB
                    self.c_euro_ib = "  "
                    if self.direction == "short" and self.cpl < self.euro_ibl:
                        self.c_euro_ib = "x"
                    elif self.direction == "long" and self.cpl > self.euro_ibh:
                        self.c_euro_ib = "x"
                    # Logic For Above / Below Opening Range
                    self.c_or = "  "
                    if self.direction == "short" and self.cpl < self.orl:
                        self.c_or = "x"
                    elif self.direction == "long" and self.cpl > self.orh:
                        self.c_or = "x"
                    # Logic for RVOL
                    if self.rvol > 1.20:
                        self.c_rvol = "x"
                    else:
                        self.c_rvol = " "                    
                                            
                    # Logic for Score 
                    self.score = sum(1 for condition in [self.c_orderflow, self.c_euro_ib, self.c_or, self.c_rvol,] if condition == "x")   
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f"DOGW | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f"DOGW | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f"DOGW | check | Product: {self.product_name} | Note: Condition Not Met")
    
    # ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):
        
        pro_color = self.product_color.get(self.product_name)
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
            raise ValueError(f"PVAT | discord_message | Note: Invalid direction '{self.direction}'")
        
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
        embed.set_timestamp()
        
        embed.add_embed_field(name="**Criteria**", value="\u200b", inline=False)

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
        embed.add_embed_field(name="**Alert Time / Price**", value=f"_{alert_time_formatted}_ EST | {self.cpl}_", inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"DOGW | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
        alert_details = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'product': self.product_name,
            'playbook': '#DOGW',
            'direction': self.direction,
            'alert_price': self.cpl,
            'score': self.score,
            'target': self.prior_mid,
        }
        log_alert_async(alert_details)