import logging
import math
import threading
from datetime import datetime, time
from alertbot.utils import config
from discord_webhook import DiscordEmbed
from alertbot.alerts.base import Base
logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class DOGW(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
 
        # Variables (Round All Variables)
        self.day_open = self.safe_round(variables.get(f'{self.product_name}_DAY_OPEN'))
        self.prior_high = self.safe_round(variables.get(f'{self.product_name}_PRIOR_HIGH'))
        self.prior_low = self.safe_round(variables.get(f'{self.product_name}_PRIOR_LOW'))
        self.ib_atr = self.safe_round(variables.get(f'{self.product_name}_IB_ATR'))
        self.euro_ibh = self.safe_round(variables.get(f'{self.product_name}_EURO_IBH'))
        self.euro_ibl = self.safe_round(variables.get(f'{self.product_name}_EURO_IBL'))
        self.orh = self.safe_round(variables.get(f'{self.product_name}_ORH'))
        self.orl = self.safe_round(variables.get(f'{self.product_name}_ORL'))
        self.a_high = self.safe_round(variables.get(f'{product_name}_A_HIGH'))
        self.a_low = self.safe_round(variables.get(f'{product_name}_A_LOW'))
        self.b_high = self.safe_round(variables.get(f'{product_name}_B_HIGH'))
        self.b_low = self.safe_round(variables.get(f'{product_name}_B_LOW'))
        self.cpl = self.safe_round(variables.get(f'{self.product_name}_CPL'))
        self.total_ovn_delta = self.safe_round(variables.get(f'{self.product_name}_TOTAL_OVN_DELTA'))
        self.total_rth_delta = self.safe_round(variables.get(f'{self.product_name}_TOTAL_RTH_DELTA'))
        self.prior_close = self.safe_round(variables.get(f'{self.product_name}_PRIOR_CLOSE'))
        self.ib_high = self.safe_round(variables.get(f'{product_name}_IB_HIGH'))
        self.ib_low = self.safe_round(variables.get(f'{product_name}_IB_LOW'))
        self.rvol = self.safe_round(variables.get(f'{product_name}_RVOL'))
        self.day_high = self.safe_round(variables.get(f'{product_name}_DAY_HIGH'))
        self.day_low = self.safe_round(variables.get(f'{product_name}_DAY_LOW'))        
        self.vwap_slope = variables.get(f'{product_name}_VWAP_SLOPE')
        self.overnight_high = self.safe_round(variables.get(f'{product_name}_OVNH'))
        self.overnight_low = self.safe_round(variables.get(f'{product_name}_OVNL'))    
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        self.delta = self.total_delta()
        self.exp_rng, self.exp_hi, self.exp_lo = self.exp_range() 
        self.opentype = self.open_type_algorithm()
        
    def safe_round(self, value, digits=2):
        if value is None:
            logger.error(f"DOGW | safe_round | Product: {self.product_name} | Missing value for rounding; defaulting to 0.")
            return 0
        try:
            return round(value, digits)
        except Exception as e:
            logger.error(f"DOGW | safe_round | Product: {self.product_name} | Error rounding value {value}: {e}")
            return 0 
    # ---------------------------------- Specific Calculations ------------------------------------ #   
    def open_type_algorithm(self): 
        a_period_mid = self.safe_round(((self.a_high + self.a_low) / 2))
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
            logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Overlap: {overlap} | Total Range: {total_range} | Overlap %: {overlap_pct}")
        else:
            if b_period_active:
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | B period data not yet available (b_high or b_low is 0).")
        if not b_period_active:
            if self.day_open == self.a_high:
                open_type = "OD v"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OD v")
            elif self.day_open == self.a_low:
                open_type = "OD ^"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OD ^")
            elif top_5 < self.day_open < top_0:
                open_type = "OTD v"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OTD v")
            elif bottom_0 < self.day_open < bottom_5:
                open_type = "OTD ^"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OTD ^")
            else:
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: Wait (A period no specific open type)")
        else:
            if self.b_high == 0 and self.b_low == 0:
                open_type = "Wait"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | B period data not available yet. Open type set to Wait.")
            else:
                if self.day_open == self.a_high:
                    open_type = "OD v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OD v")
                elif self.day_open == self.a_low:
                    open_type = "OD ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OD ^")
                elif top_5 < self.day_open < top_0:
                    open_type = "OTD v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OTD v")
                elif bottom_0 < self.day_open < bottom_5:
                    open_type = "OTD ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OTD ^")
                elif top_15 < self.day_open <= top_5 and self.b_high < a_period_mid:
                    open_type = "OTD v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OTD v (top_15 < day_open <= top_5 and b_high < a_period_mid)")
                elif bottom_5 < self.day_open <= bottom_15 and self.b_low > a_period_mid:
                    open_type = "OTD ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OTD ^ (bottom_5 < day_open <= bottom_15 and b_low > a_period_mid)")
                elif top_25 < self.day_open <= top_15 and self.b_high < bottom_25:
                    open_type = "OTD v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OTD v (top_25 < day_open <= top_15 and b_high < bottom_25)")
                elif bottom_15 <= self.day_open < bottom_25 and self.b_low > top_25:
                    open_type = "OTD ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: OTD ^ (bottom_15 <= day_open < bottom_25 and b_low > top_25)")
                elif self.day_open > top_25 and self.b_low > a_period_mid:
                    open_type = "ORR ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: ORR ^ (day_open > top_25 and b_low > a_period_mid)")
                elif self.day_open < bottom_25 and self.b_high < a_period_mid:
                    open_type = "ORR v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | Condition met: ORR v (day_open < bottom_25 and b_high < a_period_mid)")
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
        logger.debug(f"DOGW | open_type_algorithm | Determined Open Type: {open_type} | Product: {self.product_name}")
        return open_type    
        
    def exp_range(self):

        if not self.prior_close:
            logger.error(f" DOGW | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" DOGW | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)

        if impvol is None:
            raise ValueError(f" DOGW | exp_range | Product: {self.product_name} | Note: Unknown Product")

        exp_range = self.safe_round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)))
        exp_hi = self.safe_round(self.prior_close + exp_range)
        exp_lo = self.safe_round(self.prior_close - exp_range)
        
        logger.debug(f" DOGW | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
        return exp_range, exp_hi, exp_lo
      
    def total_delta(self):
        total_delta = self.total_ovn_delta + self.total_rth_delta   
        logger.debug(f"DOGW | total_delta | Product: {self.product_name} | TOTAL_DELTA: {total_delta}")
        return total_delta   
        
    # ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        def log_condition(condition, description):
            logger.debug(f"DOGW | input | Product: {self.product_name} | Direction: {self.direction} | {description} --> {condition}")
            return condition

        self.used_atr = self.ib_high - self.ib_low
        self.remaining_atr = max((self.ib_atr - self.used_atr), 0)

        if self.direction == "long":
            self.target = self.ib_low + self.ib_atr
            crit1 = log_condition(self.cpl > self.orh, f"CRITICAL1: self.cpl({self.cpl}) > self.orh({self.orh})")
        elif self.direction == "short":
            self.target = self.ib_high - self.ib_atr
            crit1 = log_condition(self.cpl < self.orl, f"CRITICAL1: self.cpl({self.cpl}) < self.orl({self.orl})")
        else:
            self.target = None
            self.atr_condition = False
            self.or_condition = False

        crit2 = log_condition(self.remaining_atr >= 0.4 * self.ib_atr, f"CRITICAL2: remaining_atr({self.remaining_atr}) >= 0.4 * ib_atr({self.ib_atr})")

        crit3 = log_condition(
            self.opentype in ["OD v", "OD ^", "OTD v", "OTD ^", "ORR ^", "ORR v", "OAOR ^", "OAOR v"],
            f"CRITICAL3: self.opentype({self.opentype}) in ['OD v', 'OD ^', 'OTD v', 'OTD ^', 'ORR ^', 'ORR v', 'OAOR ^', 'OAOR v']"
        )
        crit4 = log_condition(
            (self.day_high <= self.ib_high and self.day_low >= self.ib_low),
            f"CRITICAL4: day_high({self.day_high}) <= ib_high({self.ib_high}) and day_low({self.day_low}) >= ib_low({self.ib_low})"
        )
        logic = crit1 and crit2 and crit3 and crit4
        logger.debug(f"DOGW | input | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {logic} | CRITICAL1: {crit1} | CRITICAL2: {crit2} | CRITICAL3: {crit3} | CRITICAL4: {crit4}")
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
        
        if self.opentype == "OAIR":
            logger.debug(f"DOGW | check | Product: {self.product_name} | Open type is OAIR; returning False.")
            return False
        elif self.opentype in ["OD v", "OTD v", "OAOR v", "ORR v"]:
            self.direction = "short"
        elif self.opentype in ["OD ^", "OTD ^", "OAOR ^", "ORR ^"]:
            self.direction = "long"
        else:
            logger.debug(f"DOGW | check | Product: {self.product_name} | Open type not recognized; returning False.")
            return False
        
        self.color = "red" if self.direction == "short" else "green"
    
        # Driving Input
        if self.time_window() and self.input():
            
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)   
                logger.debug(f"DOGW | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                
                if self.direction != last_alert: 
                    logger.info(f"DOGW | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Logic 40% Atr Left
                    if self.atr_condition == True: 
                        self.c_within_atr = "x" 
                    else:
                        self.c_within_atr = "  "
                    # Logic for 50% of ETH Expected Range Left
                    if (self.overnight_high - self.overnight_low) <= (self.exp_rng*0.5):
                        self.c_exp_rng = "x"
                    else: 
                        self.c_exp_rng = "  "  
                    # Logic For VWAP Slope
                    self.c_vwap_slope = "  "
                    if self.direction == "short" and self.vwap_slope < -0.10:
                        self.c_vwap_slope = "x"
                    elif self.direction == "long" and self.vwap_slope > 0.10:
                        self.c_vwap_slope = "x"         
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
                        self.c_rvol = "  "                    
                                            
                    # Logic for Score 
                    self.score = sum(1 for condition in [self.c_orderflow, self.c_euro_ib, self.c_or, self.c_rvol, self.c_exp_rng, self.c_vwap_slope, self.c_within_atr] if condition == "x")   
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f"DOGW | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f"DOGW | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f"DOGW | check | Product: {self.product_name} | Note: Condition(s) Not Met")
    
    # ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):
        
        pro_color = self.product_color.get(self.product_name)
        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        
        direction_settings = {
            "long": {
                "risk": "Below",
                "criteria": "Above",
                "or": "High",
                "euro": "IBH"

            },
            "short": {
                "risk": "Above",
                "criteria": "Below",
                "or": "Low",
                "euro": "IBL"
            }
        }

        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f"DOGW | discord_message | Product: {self.product_name} | Note: Invalid direction '{self.direction}'")
        
        title = f"**{self.product_name} - Playbook Alert** - **DOGW - {self.opentype}**"

        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: _{self.target} (Avg Range IB)_\n"
                f"**Risk**: Wrong if price accepts {settings['risk']} HWB of A period or {settings['risk']} ETH VWAP.\n"
                f"**Driving Input**: Auction is presenting a directional open type.\n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()
        
        embed.add_embed_field(name="**Criteria**", value="\u200b", inline=False)
        
        # Confidence
        criteria = (
            f"• **[{self.c_within_atr}]** 40% Of Average IB Left To Target\n"
            f"• **[{self.c_exp_rng}]** 50% Of ETH Expected Range Left\n"
            f"• **[{self.c_vwap_slope}]** Strong Slope To VWAP\n"
            f"• **[{self.c_orderflow}]** Supportive Cumulative Delta (*_{self.delta}_*)\n"
            f"• **[{self.c_vwap_slope}]** Elevated RVOL (*_{self.rvol}%_*)\n"
            f"• **[{self.c_or}]** {settings['criteria']} 30s OR {settings['or']}\n"
            f"• **[{self.c_euro_ib}]** {settings['criteria']} Euro {settings['euro']}\n"
        )
        embed.add_embed_field(name="\u200b", value=criteria, inline=False)

        # Playbook Score
        embed.add_embed_field(name="**Playbook Score**", value=f"_{self.score} / 7_", inline=False)
        
        # Alert Time and Price Context
        embed.add_embed_field(name="**Alert Time / Price**", value=f"_{alert_time_formatted}_ EST | {self.cpl}_", inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"DOGW | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")