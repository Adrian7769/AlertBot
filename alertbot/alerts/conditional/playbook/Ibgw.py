import logging
import math
import threading
from datetime import datetime, time
from alertbot.utils import config
from discord_webhook import DiscordEmbed
from alertbot.alerts.base import Base
from zoneinfo import ZoneInfo
logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class IBGW(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables (Round All Variables)
        self.prior_vpoc = self.safe_round(variables.get(f'{self.product_name}_PRIOR_VPOC'))
        self.day_open = self.safe_round(variables.get(f'{self.product_name}_DAY_OPEN'))
        self.prior_high = self.safe_round(variables.get(f'{self.product_name}_PRIOR_HIGH'))
        self.prior_low = self.safe_round(variables.get(f'{self.product_name}_PRIOR_LOW'))
        self.ib_atr = self.safe_round(variables.get(f'{self.product_name}_IB_ATR'))
        self.euro_ibh = self.safe_round(variables.get(f'{self.product_name}_EURO_IBH'))
        self.euro_ibl = self.safe_round(variables.get(f'{self.product_name}_EURO_IBL'))
        self.cpl = self.safe_round(variables.get(f'{self.product_name}_CPL'))
        self.prior_close = self.safe_round(variables.get(f'{self.product_name}_PRIOR_CLOSE'))
        self.prior_ibh = self.safe_round(variables.get(f'{self.product_name}_PRIOR_IB_HIGH'))
        self.prior_ibl = self.safe_round(variables.get(f'{self.product_name}_PRIOR_IB_LOW'))                
        self.ib_high = self.safe_round(variables.get(f'{product_name}_IB_HIGH'))
        self.ib_low = self.safe_round(variables.get(f'{product_name}_IB_LOW'))     
        self.day_high = self.safe_round(variables.get(f'{product_name}_DAY_HIGH'))
        self.day_low = self.safe_round(variables.get(f'{product_name}_DAY_LOW'))             
        self.a_high = self.safe_round(variables.get(f'{product_name}_A_HIGH'))
        self.a_low = self.safe_round(variables.get(f'{product_name}_A_LOW'))
        self.orh = self.safe_round(variables.get(f'{self.product_name}_ORH'))
        self.orl = self.safe_round(variables.get(f'{self.product_name}_ORL'))        
        self.b_high = self.safe_round(variables.get(f'{product_name}_B_HIGH'))
        self.b_low = self.safe_round(variables.get(f'{product_name}_B_LOW')) 
        self.vwap_slope = variables.get(f'{product_name}_VWAP_SLOPE')  
        self.fd_vpoc = self.safe_round(variables.get(f'{product_name}_5D_VPOC'))
        self.td_vpoc = self.safe_round(variables.get(f'{product_name}_20D_VPOC'))
        self.overnight_high = self.safe_round(variables.get(f'{product_name}_OVNH'))
        self.overnight_low = self.safe_round(variables.get(f'{product_name}_OVNL'))                     
        self.day_vpoc = self.safe_round(variables.get(f'{product_name}_DAY_VPOC')) 
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.exp_rng = self.exp_range() 
        
    def safe_round(self, value, digits=2):
        if value is None:
            logger.error(f"IBGW | safe_round | Product: {self.product_name} | Missing value for rounding; defaulting to 0.")
            return 0
        try:
            return round(value, digits)
        except Exception as e:
            logger.error(f"IBGW | safe_round | Product: {self.product_name} | Error rounding value {value}: {e}")
            return 0 
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
            day_type = "Semi-Rotational"
        elif (self.prior_high > self.prior_ibh and self.prior_low >= self.prior_ibl and
            self.prior_high >= self.prior_ibh + (self.prior_ibh - self.prior_ibl) and
            self.prior_close <= self.prior_ibh + (self.prior_ibh - self.prior_ibl)):
            day_type = "Semi-Directional"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and  # IB EXTENSION DOWN
            self.prior_low <= self.prior_ibl - 0.5 * (self.prior_ibh - self.prior_ibl) and # LOW IS BELOW 1.5x IB
            self.prior_low >= self.prior_ibl - (self.prior_ibh - self.prior_ibl)): # LOW IS ABOVE 2x IB
            day_type = "Semi-Rotational"
        elif (self.prior_low < self.prior_ibl and self.prior_high <= self.prior_ibh and # IB EXTENSION DOWN
            self.prior_low <= self.prior_ibl - (self.prior_ibh - self.prior_ibl) and # LOW IS BELOW 2x IB
            self.prior_close >= self.prior_ibl - (self.prior_ibh - self.prior_ibl)): # CLOSE IS WITHIN 2x IB
            day_type = "Semi-Directional"
        else:
            day_type = "Other"
        logger.debug(f" IBGW | prior_day | Product: {self.product_name} | Prior Day Type: {day_type}")
        return day_type
    
    def open_type(self):
        a_period_mid = round(((self.a_high + self.a_low) / 2), 2)
        current_sub_low = min(self.a_low, self.b_low)
        current_sub_high = max(self.a_high, self.b_high)
        overlap = max(0, min(current_sub_high, self.prior_high) - max(current_sub_low, self.prior_low))
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
        logger.debug(f"IBGW | open_type | Product {self.product_name} | Open Type: {open_type}")              
        return open_type 
    
    def exp_range(self):
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
        exp_range = self.safe_round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)))
        logger.debug(f" IBGW | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range}")
        return exp_range
    
    def one_time_framing(self):
        if self.product_name == "CL":
            period_times = {
                'A': time(9, 0), 'B': time(9, 30), 'C': time(10, 0),
                'D': time(10, 30), 'E': time(11, 0), 'F': time(11, 30),
                'G': time(12, 0), 'H': time(12, 30), 'I': time(13, 0),
                'J': time(13, 30), 'K': time(14, 0),
            }
            logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Using CL period times.")
        else:
            period_times = {
                'A': time(9, 30), 'B': time(10, 0), 'C': time(10, 30),
                'D': time(11, 0), 'E': time(11, 30), 'F': time(12, 0),
                'G': time(12, 30), 'H': time(13, 0), 'I': time(13, 30),
                'J': time(14, 0), 'K': time(14, 30), 'L': time(15, 0),
                'M': time(15, 30),
            }
            logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Using non-CL period times.")

        now = datetime.now(self.est).time()
        logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Current time: {now}")
        
        sorted_periods = sorted(period_times.items(), key=lambda x: x[1])
        current_period = None
        finished_periods = []
        
        for i, (period, start_time) in enumerate(sorted_periods):
            if i < len(sorted_periods) - 1:
                next_start = sorted_periods[i + 1][1]
                if start_time <= now < next_start:
                    current_period = period
                    finished_periods = [p for p, t in sorted_periods[:i]]
                    break
            else:
                if now >= start_time:
                    current_period = period
                    finished_periods = [p for p, t in sorted_periods[:i]]
                    break
                    
        logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Current Period: {current_period}")
        logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Finished periods: {finished_periods}")
        
        if len(finished_periods) < 2:
            logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Not enough finished periods. Returning False.")
            return False

        period1, period2 = finished_periods[-2], finished_periods[-1]
        logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Last two periods selected: {period1}, {period2}")
        
        p1_high = self.variables.get(f"{self.product_name}_{period1}_HIGH")
        p1_low = self.variables.get(f"{self.product_name}_{period1}_LOW")
        p2_high = self.variables.get(f"{self.product_name}_{period2}_HIGH")
        p2_low = self.variables.get(f"{self.product_name}_{period2}_LOW")
        logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Prior Two Period Raw values: {period1} HIGH={p1_high}, LOW={p1_low}; {period2} HIGH={p2_high}, LOW={p2_low}")
        
        if None in (p1_high, p1_low, p2_high, p2_low):
            logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | One or more period values missing. Returning False.")
            return False
            
        p1_high = self.safe_round(p1_high)
        p1_low = self.safe_round(p1_low)
        p2_high = self.safe_round(p2_high)
        p2_low = self.safe_round(p2_low)
        logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Prior Two Period Rounded values: {period1} HIGH={p1_high}, LOW={p1_low}; {period2} HIGH={p2_high}, LOW={p2_low}")
        
        current_period_high = self.variables.get(f"{self.product_name}_{current_period}_HIGH")
        current_period_low = self.variables.get(f"{self.product_name}_{current_period}_LOW")
        if current_period_high is None or current_period_low is None:
            logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Current period values not found. Returning False.")
            return False
        current_period_high = self.safe_round(current_period_high)
        current_period_low = self.safe_round(current_period_low)
        logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Current period {current_period} HIGH={current_period_high}, LOW={current_period_low}")
        
        if self.direction == "long":
            if p2_high > p1_high and p2_low > p1_low:
                logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Upward one time framing detected for prior periods.")
                if current_period_low >= p2_low:
                    logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Current period acceptable (inside or extending upward). Returning True.")
                    return True
                else:
                    logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Current period low {current_period_low} is below prior low {p2_low}. Returning False.")
                    return False
            else:
                logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Prior periods are not upward one time framing. Returning False.")
                return False
                
        elif self.direction == "short":
            if p2_high < p1_high and p2_low < p1_low:
                logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Downward one time framing detected for prior periods.")
                if current_period_high <= p2_high:
                    logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Current period acceptable (inside or extending downward). Returning True.")
                    return True
                else:
                    logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Current period high {current_period_high} is above prior high {p2_high}. Returning False.")
                    return False
            else:
                logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Prior periods are not downward one time framing. Returning False.")
                return False
                
        else:
            logger.debug(f"IBGW | one_time_framing | Product: {self.product_name} | Invalid direction specified. Returning False.")
            return False

# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        def log_condition(condition, description):
            logger.debug(f"IBGW | input | Product: {self.product_name} | Direction: {self.direction} | {description} --> {condition}")
            return condition
        if self.direction == "short":
            self.crit1 = log_condition(
                self.day_low >= self.ib_low - 0.5 * (self.ib_high - self.ib_low),
                f"CRITICAL1: day_low({self.day_low}) >= ib_low({self.ib_low}) - 0.5*(ib_high({self.ib_high}) - ib_low({self.ib_low}))"
            )
        elif self.direction == "long":
            self.crit1 = log_condition(
                self.day_high <= self.ib_high + 0.5 * (self.ib_high - self.ib_low),
                f"CRITICAL1: day_high({self.day_high}) <= ib_high({self.ib_high}) + 0.5*(ib_high({self.ib_high}) - ib_low({self.ib_low}))"
            )
        crit2 = log_condition(
            (self.ib_high - self.ib_low) / self.ib_atr <= 0.85,
            f"CRITICAL2: ((ib_high({self.ib_high}) - ib_low({self.ib_low}))/ib_atr({self.ib_atr})) <= 0.85"
        )
        logic = self.crit1 and crit2
        logger.debug(f"IBGW | input | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {logic} | "
                    f"CRITICAL1: {self.crit1} | CRITICAL2: {crit2}")
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
                logger.debug(f"IBGW | time_window | Product: {self.product_name} | Within equity alert window: {self.current_time}")
                return True
            else:
                logger.debug(f"IBGW | time_window | Product: {self.product_name} | Outside equity alert window: {self.current_time}")
                return False
        elif self.product_name == 'CL':
            if self.crude_ib <= self.current_time <= self.crude_close:
                logger.debug(f"IBGW | time_window | Product: {self.product_name} | Within crude alert window: {self.current_time}")
                return True
            else:
                logger.debug(f"IBGW | time_window | Product: {self.product_name} | Outside crude alert window: {self.current_time}")
                return False
        else:
            logger.warning(f"IBGW | time_window | Product: {self.product_name} | No time window defined for product")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
        # Determine Direction with Detailed Logging
        if self.day_high > self.ib_high and self.day_low < self.ib_low:
            if self.cpl < self.ib_low:
                self.direction = "short"
                logger.debug(f" IBGW | check | Product: {self.product_name} | DIR_LOGIC: self.cpl({self.cpl}) < self.ib_low({self.ib_low}) -> short")
            elif self.cpl > self.ib_high:
                self.direction = "long"
                logger.debug(f" IBGW | check | Product: {self.product_name} | DIR_LOGIC: self.cpl({self.cpl}) > self.ib_high({self.ib_high}) -> long")
            else:
                logger.debug(f" IBGW | check | Product: {self.product_name} | Note: In Middle Of IB Range While Neutral, Returning.")
                return False  # In Middle Of IB Range While Neutral
        else:
            if self.day_low < self.ib_low:
                self.direction = "short"
                logger.debug(f" IBGW | check | Product: {self.product_name} | DIR_LOGIC: self.day_low({self.day_low}) < self.ib_low({self.ib_low}) -> short")
            elif self.day_high > self.ib_high:
                self.direction = "long"
                logger.debug(f" IBGW | check | Product: {self.product_name} | DIR_LOGIC: self.day_high({self.day_high}) > self.ib_high({self.ib_high}) -> long")
            else:
                logger.debug(f" IBGW | check | Product: {self.product_name} | Note: No IB Extension, Returning.")
                return False  # No IB Extension

        # Driving Input Check with Detailed Logging
        if self.time_window() and self.input():
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)
                logger.debug(f" IBGW | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                if self.direction != last_alert:
                    logger.info(f" IBGW | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # CRITERIA 1: Directional Open
                    if self.direction == "short":
                        if self.open_type() in ["OD v", "OTD v", "ORR v", "OAOR v"]:
                            self.c_directional_open = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: open_type() returned {self.open_type()} -> [{self.c_directional_open}]")
                        else:
                            self.c_directional_open = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: open_type() returned {self.open_type()} -> [{self.c_directional_open}]")
                    elif self.direction == "long":
                        if self.open_type() in ["OD ^", "OTD ^", "ORR ^", "OAOR ^"]:
                            self.c_directional_open = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: open_type() returned {self.open_type()} -> [{self.c_directional_open}]")
                        else:
                            self.c_directional_open = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: open_type() returned {self.open_type()} -> [{self.c_directional_open}]")
                    
                    # CRITERIA 2: One Time Framing (past 3)
                    if self.one_time_framing():
                        self.c_otf = "x"
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: one_time_framing() True -> [{self.c_otf}]")
                    else:
                        self.c_otf = "  "
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: one_time_framing() False -> [{self.c_otf}]")
                    
                    # CRITERIA 3: Clear Magnet
                    if self.direction == "short":
                        if (self.fd_vpoc >= self.ib_low - (self.ib_high - self.ib_low) or
                            self.td_vpoc >= self.ib_low - (self.ib_high - self.ib_low) or
                            self.prior_vpoc >= self.ib_low - (self.ib_high - self.ib_low)):
                            self.c_magnet = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: One of (fd_vpoc({self.fd_vpoc}), td_vpoc({self.td_vpoc}), prior_vpoc({self.prior_vpoc})) >= (ib_low({self.ib_low}) - IB_range({self.ib_high - self.ib_low})) -> [{self.c_magnet}]")
                        else:
                            self.c_magnet = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: Clear magnet criteria not met -> [{self.c_magnet}]")
                    elif self.direction == "long":
                        if (self.fd_vpoc <= self.ib_high + (self.ib_high - self.ib_low) or
                            self.td_vpoc <= self.ib_high + (self.ib_high - self.ib_low) or
                            self.prior_vpoc <= self.ib_high + (self.ib_high - self.ib_low)):
                            self.c_magnet = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: One of (fd_vpoc({self.fd_vpoc}), td_vpoc({self.td_vpoc}), prior_vpoc({self.prior_vpoc})) <= (ib_high({self.ib_high}) + IB_range({self.ib_high - self.ib_low})) -> [{self.c_magnet}]")
                        else:
                            self.c_magnet = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: Clear magnet criteria not met -> [{self.c_magnet}]")
                    
                    # CRITERIA 4: Not Hit 1.5x IB
                    if self.crit1:
                        self.c_ib_ext_half = "x"
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: crit1 is True -> [{self.c_ib_ext_half}]")
                    else:
                        self.c_ib_ext_half = "  "
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: crit1 is False -> [{self.c_ib_ext_half}]")
                    
                    # CRITERIA 5: IB Narrow to Average
                    self.ib_range = round((self.ib_high - self.ib_low), 2)
                    self.ib_vatr = round((self.ib_range / self.ib_atr), 2)
                    if self.ib_vatr <= 0.85:
                        self.c_narrow_ib = "x"
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: (ib_high({self.ib_high}) - ib_low({self.ib_low})/ib_atr({self.ib_atr})) <= 0.85 -> [{self.c_narrow_ib}]")
                    else:
                        self.c_narrow_ib = "  "
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: (ib_high({self.ib_high}) - ib_low({self.ib_low})/ib_atr({self.ib_atr})) > 0.85 -> [{self.c_narrow_ib}]")
                    
                    # CRITERIA 6: Less than 50% expected range used
                    self.day_range_used = max(self.overnight_high, self.day_high) - min(self.overnight_low, self.day_low)
                    self.range_used = round((self.day_range_used / self.exp_rng),2)
                    if self.range_used > 0.5:
                        self.c_exp_rng = "  "
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: remaining_range({self.range_used}) >= 0.5 -> [{self.c_exp_rng}]")
                    else:
                        self.c_exp_rng = "x"
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: remaining_range({self.range_used}) < 0.5 -> [{self.c_exp_rng}]")
                    
                    # CRITERIA 7: c_euro IB
                    if self.direction == "short":
                        if self.cpl < self.euro_ibl:
                            self.c_euro_ib = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: self.cpl({self.cpl}) < euro_ibl({self.euro_ibl}) -> [{self.c_euro_ib}]")
                        else:
                            self.c_euro_ib = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: self.cpl({self.cpl}) >= euro_ibl({self.euro_ibl}) -> [{self.c_euro_ib}]")
                    elif self.direction == "long":
                        if self.cpl > self.euro_ibh:
                            self.c_euro_ib = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: self.cpl({self.cpl}) > euro_ibh({self.euro_ibh}) -> [{self.c_euro_ib}]")
                        else:
                            self.c_euro_ib = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: self.cpl({self.cpl}) <= euro_ibh({self.euro_ibh}) -> [{self.c_euro_ib}]")
                    
                    # CRITERIA 8: Skew in Profile Toward IB Extreme
                    if self.direction == "short":
                        if self.day_vpoc <= self.ib_low + round(0.33 * (self.ib_high - self.ib_low), 2):
                            self.c_skew = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_8: day_vpoc({self.day_vpoc}) <= ib_low({self.ib_low}) + 0.33*(ib_range) -> [{self.c_skew}]")
                        else:
                            self.c_skew = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_8: day_vpoc({self.day_vpoc}) > ib_low({self.ib_low}) + 0.33*(ib_range) -> [{self.c_skew}]")
                    elif self.direction == "long":
                        if self.day_vpoc >= self.ib_high - round(0.33 * (self.ib_high - self.ib_low), 2):
                            self.c_skew = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_8: day_vpoc({self.day_vpoc}) >= ib_high({self.ib_high}) - 0.33*(ib_range) -> [{self.c_skew}]")
                        else:
                            self.c_skew = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_8: day_vpoc({self.day_vpoc}) < ib_high({self.ib_high}) - 0.33*(ib_range) -> [{self.c_skew}]")
                    
                    # CRITERIA 9: IB Broke from Composite Reference (5d, 20d for now)
                    if (self.ib_low < self.fd_vpoc < self.ib_high) or (self.ib_low < self.td_vpoc < self.ib_high):
                        self.c_composite_ref = "x"
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: fd_vpoc({self.fd_vpoc}) or td_vpoc({self.td_vpoc}) within IB range ({self.ib_low}-{self.ib_high}) -> [{self.c_composite_ref}]")
                    else:
                        self.c_composite_ref = "  "
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: Composite reference criteria not met -> [{self.c_composite_ref}]")
                    
                    # CRITERIA 10: Prior Session Balanced (Rotational)
                    if self.prior_day() in ["Rotational", "Semi-Rotational"]:
                        self.c_rotational = "x"
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_10: prior_day() returned Rotational or Semi-Rotational -> [{self.c_rotational}]")
                    else:
                        self.c_rotational = "  "
                        logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_10: prior_day() did not return Rotational or Semi-Rotational -> [{self.c_rotational}]")
                    
                    # CRITERIA 11: Noticeable Slope to VWAP
                    if self.direction == "short":
                        if self.vwap_slope < -0.06:
                            self.c_vwap_slope = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_11: vwap_slope({self.vwap_slope}) < -0.05 -> [{self.c_vwap_slope}]")
                        else:
                            self.c_vwap_slope = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_11: vwap_slope({self.vwap_slope}) >= -0.05 -> [{self.c_vwap_slope}]")
                    elif self.direction == "long":
                        if self.vwap_slope > 0.06:
                            self.c_vwap_slope = "x"
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_11: vwap_slope({self.vwap_slope}) > 0.05 -> [{self.c_vwap_slope}]")
                        else:
                            self.c_vwap_slope = "  "
                            logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_11: vwap_slope({self.vwap_slope}) <= 0.05 -> [{self.c_vwap_slope}]")
                    
                    # Score Calculation Logging
                    self.score = sum(1 for condition in [
                        self.c_directional_open, self.c_otf, self.c_euro_ib, self.c_magnet, self.c_ib_ext_half,
                        self.c_narrow_ib, self.c_exp_rng, self.c_skew, self.c_composite_ref, self.c_rotational,
                        self.c_vwap_slope
                    ] if condition == "x")
                    logger.debug(f" IBGW | check | Product: {self.product_name} | Direction: {self.direction} | SCORE: {self.score}/11")
                    
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" IBGW | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" IBGW | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f" IBGW | check | Product: {self.product_name} | Note: Condition(s) Not Met")

# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):

        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        
        direction_settings = {
            "long": {
                "destination": "IBH",
                "mid": "Above",
                "emoji_indicator": "🔼",
            },
            "short": {
                "destination": "IBL",
                "mid": "Below",
                "emoji_indicator": "🔽",
            }
        }
 
        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" IBGW | discord_message | Product: {self.product_name} | Note: Invalid direction '{self.direction}'")
        
        if self.direction == "long":
            self.destination = self.ib_high + 0.5 * (self.ib_high - self.ib_low)
            if self.open_type() in ["OTD ^", "OD ^", "ORR ^", "OAOR ^"]:
                ot = self.open_type()
                colon = ":"
            else:
                ot = ""
                colon = ""
        elif self.direction == "short":
            self.destination = self.ib_low - 0.5 * (self.ib_high - self.ib_low)
            if self.open_type() in ["OTD v", "OD v", "ORR v", "OAOR ^"]:
                ot = self.open_type()
                colon = ":"
            else:
                ot = ""            
                colon = ""
        if self.direction == "long":
            if self.vwap_slope > 0.06:
                inline_text = f"Noticeable Slope to dVWAP: ({round((self.vwap_slope*100),2)}°)\n"
            else:
                inline_text = f"Noticeable Slope to dVWAP \n"
        elif self.direction == "short":
            if self.vwap_slope < -0.06:
                inline_text = f"Noticeable Slope to dVWAP: ({round((self.vwap_slope*100),2)}°)\n"
            else:
                inline_text = f"Noticeable Slope to dVWAP \n"
        # Title Construction with Emojis
        title = f"**{self.product_name} - Playbook Alert** - **IBGW** {settings['emoji_indicator']}"
    
        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: {round(self.destination,2)} ({settings['destination']} 1.5x) \n"
                f"**Risk**: Price Quickly Rejects IB Range Extension \n"
                f"**Driving Input**: This trade seeks entry on the breach of the Initial Balance toward a pre-defined target \n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()

        # Criteria Header
        embed.add_embed_field(name="**Criteria**", value="", inline=False)

        # Criteria Details
        criteria = (
            f"- **[{self.c_directional_open}]** Favorable Directional Open{colon} {ot} \n"
            f"- **[{self.c_otf}]** One-Time Framing \n"
            f"- **[{self.c_exp_rng}]** Less than 50% Expected Range Used: ({round((self.range_used*100),2)}%) \n"
            f"- **[{self.c_narrow_ib}]** IB is Narrow to Average: ({round((self.ib_vatr*100), 2)}%) \n"
            f"- **[{self.c_skew}]** Skew In Profile Towards IB {settings['destination']} \n"
            f"- **[{self.c_composite_ref}]** IB Broke From Composite Value Reference \n"
            f"- **[{self.c_rotational}]** Prior Session Was Balanced \n"
            f"- **[{self.c_vwap_slope}]** {inline_text}"
            f"- **[{self.c_ib_ext_half}]** Have Not Hit 1.5x {settings['destination']} \n"
            f"- **[{self.c_magnet}]** Clear Magnet Ahead \n"
            f"- **[{self.c_euro_ib}]** {settings['mid']} Euro {settings['destination']} \n"
        )
        embed.add_embed_field(name="", value=criteria, inline=False)

        # Playbook Score
        embed.add_embed_field(name="**Playbook Score**", value=f"_{self.score} / 11_", inline=False)
        
        # Alert Time and Price Context
        alert_time_text = f"**Alert Time / Price**: _{alert_time_formatted} EST | {self.cpl}_"
        embed.add_embed_field(name="", value=alert_time_text, inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"IBGW | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")