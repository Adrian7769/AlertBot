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
        
        # Conditionally round B period data only if the current time is at or past the B period start
        if self.product_name == 'CL':
            b_period_start_time = time(9, 30)
        else:
            b_period_start_time = time(10, 0)
        current_time = datetime.now(self.est).time()
        if current_time >= b_period_start_time:
            self.b_high = self.safe_round(variables.get(f'{product_name}_B_HIGH'))
            self.b_low = self.safe_round(variables.get(f'{product_name}_B_LOW'))
        else:
            self.b_high = 0
            self.b_low = 0

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
        # Calculate A period statistics
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

        logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                    f"Computed A Period Values: a_high={self.a_high}, a_low={self.a_low}, "
                    f"a_period_mid={a_period_mid}, a_period_range={a_period_range}, "
                    f"top_0={top_0}, top_5={top_5}, top_15={top_15}, top_25={top_25}, "
                    f"bottom_0={bottom_0}, bottom_5={bottom_5}, bottom_15={bottom_15}, bottom_25={bottom_25}")

        # Get current time from EST
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
        logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                    f"Current Time: {self.current_time}")

        # Determine B period start time based on product
        if self.product_name == 'CL':
            b_period_start_time = time(9, 30)  
        else:
            b_period_start_time = time(10, 0)  
        logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                    f"B Period Start Time: {b_period_start_time}")

        b_period_active = self.current_time >= b_period_start_time
        logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                    f"B Period Active: {b_period_active}")

        overlap_pct = 0
        if b_period_active and self.b_high > 0 and self.b_low > 0:
            overlap = max(0, min(self.day_high, self.prior_high) - max(self.day_low, self.prior_low))
            total_range = self.day_high - self.day_low
            overlap_pct = overlap / total_range if total_range > 0 else 0
            logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                        f"B Period Data: b_high={self.b_high}, b_low={self.b_low}, "
                        f"day_high={self.day_high}, prior_high={self.prior_high}, "
                        f"day_low={self.day_low}, prior_low={self.prior_low} | "
                        f"Overlap={overlap}, Total Range={total_range}, Overlap %={overlap_pct}")
        else:
            if b_period_active:
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                            f"B Period Active but missing data: b_high={self.b_high}, b_low={self.b_low}")
            else:
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                            f"B Period Not Active (current_time={self.current_time} < required={b_period_start_time})")

        # Evaluate conditions based on whether B period is active or not
        if not b_period_active:
            logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                        f"Evaluating A Period Conditions with day_open={self.day_open}")
            if self.day_open == self.a_high:
                open_type = "OD v"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                            f"Condition: day_open == a_high ({self.day_open} == {self.a_high}) => Open Type: {open_type}")
            elif self.day_open == self.a_low:
                open_type = "OD ^"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                            f"Condition: day_open == a_low ({self.day_open} == {self.a_low}) => Open Type: {open_type}")
            elif top_5 < self.day_open < top_0:
                open_type = "OTD v"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                            f"Condition: top_5 < day_open < top_0 ({top_5} < {self.day_open} < {top_0}) => Open Type: {open_type}")
            elif bottom_0 < self.day_open < bottom_5:
                open_type = "OTD ^"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                            f"Condition: bottom_0 < day_open < bottom_5 ({bottom_0} < {self.day_open} < {bottom_5}) => Open Type: {open_type}")
            else:
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                            f"No A Period condition met; defaulting to Wait")
        else:
            logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                        f"Evaluating B Period Conditions with day_open={self.day_open}")
            if self.b_high == 0 and self.b_low == 0:
                open_type = "Wait"
                logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                            f"B Period data is zero (b_high={self.b_high}, b_low={self.b_low}); Open Type set to Wait")
            else:
                if self.day_open == self.a_high:
                    open_type = "OD v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: day_open == a_high ({self.day_open} == {self.a_high}) => Open Type: {open_type}")
                elif self.day_open == self.a_low:
                    open_type = "OD ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: day_open == a_low ({self.day_open} == {self.a_low}) => Open Type: {open_type}")
                elif top_5 < self.day_open < top_0:
                    open_type = "OTD v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: top_5 < day_open < top_0 ({top_5} < {self.day_open} < {top_0}) => Open Type: {open_type}")
                elif bottom_0 < self.day_open < bottom_5:
                    open_type = "OTD ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: bottom_0 < day_open < bottom_5 ({bottom_0} < {self.day_open} < {bottom_5}) => Open Type: {open_type}")
                elif top_15 < self.day_open <= top_5 and self.b_high < a_period_mid:
                    open_type = "OTD v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: top_15 < day_open <= top_5 ({top_15} < {self.day_open} <= {top_5}) and "
                                f"b_high < a_period_mid ({self.b_high} < {a_period_mid}) => Open Type: {open_type}")
                elif bottom_5 < self.day_open <= bottom_15 and self.b_low > a_period_mid:
                    open_type = "OTD ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: bottom_5 < day_open <= bottom_15 ({bottom_5} < {self.day_open} <= {bottom_15}) and "
                                f"b_low > a_period_mid ({self.b_low} > {a_period_mid}) => Open Type: {open_type}")
                elif top_25 < self.day_open <= top_15 and self.b_high < bottom_25:
                    open_type = "OTD v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: top_25 < day_open <= top_15 ({top_25} < {self.day_open} <= {top_15}) and "
                                f"b_high < bottom_25 ({self.b_high} < {bottom_25}) => Open Type: {open_type}")
                elif bottom_15 <= self.day_open < bottom_25 and self.b_low > top_25:
                    open_type = "OTD ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: bottom_15 <= day_open < bottom_25 ({bottom_15} <= {self.day_open} < {bottom_25}) and "
                                f"b_low > top_25 ({self.b_low} > {top_25}) => Open Type: {open_type}")
                elif self.day_open > top_25 and self.b_low > a_period_mid:
                    open_type = "ORR ^"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: day_open > top_25 ({self.day_open} > {top_25}) and "
                                f"b_low > a_period_mid ({self.b_low} > {a_period_mid}) => Open Type: {open_type}")
                elif self.day_open < bottom_25 and self.b_high < a_period_mid:
                    open_type = "ORR v"
                    logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                f"Condition: day_open < bottom_25 ({self.day_open} < {bottom_25}) and "
                                f"b_high < a_period_mid ({self.b_high} < {a_period_mid}) => Open Type: {open_type}")
                else:
                    if overlap_pct >= 0.25:
                        open_type = "OAIR"
                        logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                    f"Condition: overlap_pct >= 0.25 ({overlap_pct} >= 0.25) => Open Type: {open_type}")
                    elif overlap_pct < 0.25:
                        if self.day_open > self.prior_high:
                            open_type = "OAOR ^"
                            logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                        f"Condition: day_open > prior_high ({self.day_open} > {self.prior_high}) => Open Type: {open_type}")
                        elif self.day_open < self.prior_low:
                            open_type = "OAOR v"
                            logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                        f"Condition: day_open < prior_low ({self.day_open} < {self.prior_low}) => Open Type: {open_type}")
                        else:
                            open_type = "OAIR"
                            logger.debug(f"DOGW | open_type_algorithm | Product: {self.product_name} | "
                                        f"No clear criteria met; defaulting to OAIR => Open Type: {open_type}")
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
        
        # Determine Direction based on Open Type with Detailed Logging
        if self.opentype == "OAIR":
            logger.debug(f"DOGW | check | Product: {self.product_name} | Open type is OAIR; returning False.")
            return False
        elif self.opentype in ["OD v", "OTD v", "OAOR v", "ORR v"]:
            self.direction = "short"
            logger.debug(f"DOGW | check | Product: {self.product_name} | DIR_LOGIC: opentype({self.opentype}) indicates short")
        elif self.opentype in ["OD ^", "OTD ^", "OAOR ^", "ORR ^"]:
            self.direction = "long"
            logger.debug(f"DOGW | check | Product: {self.product_name} | DIR_LOGIC: opentype({self.opentype}) indicates long")
        else:
            logger.debug(f"DOGW | check | Product: {self.product_name} | Open type not recognized; returning False.")
            return False

        self.color = "red" if self.direction == "short" else "green"

        # Driving Input Check with Detailed Logging
        if self.time_window() and self.input():
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)
                logger.debug(f"DOGW | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                if self.direction != last_alert:
                    logger.info(f"DOGW | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # CRITERIA 1: 40% ATR Left
                    if self.atr_condition == True:
                        self.c_within_atr = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: atr_condition True -> [{self.c_within_atr}]")
                    else:
                        self.c_within_atr = "  "
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: atr_condition False -> [{self.c_within_atr}]")
                    
                    # CRITERIA 2: 50% of ETH Expected Range Left
                    if (self.overnight_high - self.overnight_low) <= (self.exp_rng * 0.5):
                        self.c_exp_rng = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: ETH expected range condition met -> [{self.c_exp_rng}]")
                    else:
                        self.c_exp_rng = "  "
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: ETH expected range condition not met -> [{self.c_exp_rng}]")
                    
                    # CRITERIA 3: VWAP Slope
                    self.c_vwap_slope = "  "
                    if self.direction == "short" and self.vwap_slope < -0.10:
                        self.c_vwap_slope = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: vwap_slope({self.vwap_slope}) < -0.10 -> [{self.c_vwap_slope}]")
                    elif self.direction == "long" and self.vwap_slope > 0.10:
                        self.c_vwap_slope = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: vwap_slope({self.vwap_slope}) > 0.10 -> [{self.c_vwap_slope}]")
                    else:
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: VWAP slope criteria not met -> [{self.c_vwap_slope}]")
                    
                    # CRITERIA 4: Orderflow
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: delta({self.delta}) < 0 for short -> [{self.c_orderflow}]")
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: delta({self.delta}) > 0 for long -> [{self.c_orderflow}]")
                    else:
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: Orderflow criteria not met -> [{self.c_orderflow}]")
                    
                    # CRITERIA 5: Euro IB
                    self.c_euro_ib = "  "
                    if self.direction == "short" and self.cpl < self.euro_ibl:
                        self.c_euro_ib = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: cpl({self.cpl}) < euro_ibl({self.euro_ibl}) -> [{self.c_euro_ib}]")
                    elif self.direction == "long" and self.cpl > self.euro_ibh:
                        self.c_euro_ib = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: cpl({self.cpl}) > euro_ibh({self.euro_ibh}) -> [{self.c_euro_ib}]")
                    else:
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: Euro IB criteria not met -> [{self.c_euro_ib}]")
                    
                    # CRITERIA 6: Above / Below Opening Range
                    self.c_or = "  "
                    if self.direction == "short" and self.cpl < self.orl:
                        self.c_or = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: cpl({self.cpl}) < orl({self.orl}) for short -> [{self.c_or}]")
                    elif self.direction == "long" and self.cpl > self.orh:
                        self.c_or = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: cpl({self.cpl}) > orh({self.orh}) for long -> [{self.c_or}]")
                    else:
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: Opening Range criteria not met -> [{self.c_or}]")
                    
                    # CRITERIA 7: RVOL
                    if self.rvol > 1.20:
                        self.c_rvol = "x"
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: rvol({self.rvol}) > 1.20 -> [{self.c_rvol}]")
                    else:
                        self.c_rvol = "  "
                        logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: rvol({self.rvol}) <= 1.20 -> [{self.c_rvol}]")
                    
                    # Score Calculation Logging
                    self.score = sum(1 for condition in [
                        self.c_orderflow, self.c_euro_ib, self.c_or, self.c_rvol, self.c_exp_rng, self.c_vwap_slope, self.c_within_atr
                    ] if condition == "x")
                    logger.debug(f"DOGW | check | Product: {self.product_name} | Direction: {self.direction} | SCORE: {self.score}/7")
                    
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
                "euro": "IBH",
                "emoji_indicator": "🔼",
            },
            "short": {
                "risk": "Above",
                "criteria": "Below",
                "or": "Low",
                "euro": "IBL",
                "emoji_indicator": "🔽",
            }
        }

        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f"DOGW | discord_message | Product: {self.product_name} | Note: Invalid direction '{self.direction}'")
        
        title = f"**{self.product_name} - Playbook Alert** - **DOGW** {settings['emoji_indicator']}"

        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: {self.target} (Avg Range IB)\n"
                f"**Risk**: Wrong if price accepts {settings['risk']} HWB of A period or {settings['risk']} ETH VWAP\n"
                f"**Driving Input**: Auction is presenting a directional open type\n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()
        
        embed.add_embed_field(name="**Criteria**", value="", inline=False)
        
        # Confidence
        criteria = (
            f"- **[{self.c_within_atr}]** 40% Of Average IB Left To Target\n"
            f"- **[{self.c_exp_rng}]** 50% Of ETH Expected Range Left\n"
            f"- **[{self.c_vwap_slope}]** Strong Slope To VWAP\n"
            f"- **[{self.c_orderflow}]** Supportive Cumulative Delta ({self.delta})\n"
            f"- **[{self.c_vwap_slope}]** Elevated RVOL ({self.rvol}%)\n"
            f"- **[{self.c_or}]** {settings['criteria']} 30s OR {settings['or']}\n"
            f"- **[{self.c_euro_ib}]** {settings['criteria']} Euro {settings['euro']}\n"
        )
        embed.add_embed_field(name="\u200b", value=criteria, inline=False)

        # Playbook Score
        embed.add_embed_field(name="**Playbook Score**", value=f"{self.score} / 7", inline=False)
        
        alert_time_text = f"**Alert Time / Price**: {alert_time_formatted} EST | {self.cpl}"
        embed.add_embed_field(name="", value=alert_time_text, inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"DOGW | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
