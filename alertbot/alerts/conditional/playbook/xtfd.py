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

class XTFD(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        self.day_vpoc = self.safe_round(variables.get(f'{product_name}_DAY_VPOC'))
        self.day_open = self.safe_round(variables.get(f'{self.product_name}_DAY_OPEN'))
        self.prior_high = self.safe_round(variables.get(f'{self.product_name}_PRIOR_HIGH'))
        self.prior_low = self.safe_round(variables.get(f'{self.product_name}_PRIOR_LOW'))
        self.ib_atr = self.safe_round(variables.get(f'{self.product_name}_IB_ATR'))
        self.day_high = self.safe_round(variables.get(f'{product_name}_DAY_HIGH'))
        self.day_low = self.safe_round(variables.get(f'{product_name}_DAY_LOW'))
        self.vwap_slope = variables.get(f'{product_name}_VWAP_SLOPE')
        self.eth_vwap = variables.get(f'{self.product_name}_ETH_VWAP')
        self.cpl = self.safe_round(variables.get(f'{self.product_name}_CPL'))
        self.prior_ibh = self.safe_round(variables.get(f'{self.product_name}_PRIOR_IB_HIGH'))
        self.prior_ibl = self.safe_round(variables.get(f'{self.product_name}_PRIOR_IB_LOW'))
        self.prior_close = self.safe_round(variables.get(f'{self.product_name}_PRIOR_CLOSE'))
        self.top_one_eth_vwap = variables.get(f'{self.product_name}_ETH_TOP_1')
        self.bottom_one_eth_vwap = variables.get(f'{self.product_name}_ETH_BOTTOM_1')
        self.a_high = self.safe_round(variables.get(f'{product_name}_A_HIGH'))
        self.a_low = self.safe_round(variables.get(f'{product_name}_A_LOW'))
        self.b_high = self.safe_round(variables.get(f'{product_name}_B_HIGH'))
        self.b_low = self.safe_round(variables.get(f'{product_name}_B_LOW'))
        self.overnight_high = self.safe_round(variables.get(f'{product_name}_OVNH'))
        self.overnight_low = self.safe_round(variables.get(f'{product_name}_OVNL'))
        self.ib_high = self.safe_round(variables.get(f'{product_name}_IB_HIGH'))
        self.ib_low = self.safe_round(variables.get(f'{product_name}_IB_LOW'))
        self.orh = self.safe_round(variables.get(f'{self.product_name}_ORH'))
        self.orl = self.safe_round(variables.get(f'{self.product_name}_ORL'))
        
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.exp_rng = self.exp_range() 
        
    def safe_round(self, value, digits=2):
        if value is None:
            logger.error(f"XTFD | safe_round | Product: {self.product_name} | Missing value for rounding; defaulting to 0.")
            return 0
        try:
            return round(value, digits)
        except Exception as e:
            logger.error(f"XTFD | safe_round | Product: {self.product_name} | Error rounding value {value}: {e}")
            return 0
    
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
        logger.debug(f" XTFD | prior_day | Product: {self.product_name} | Prior Day Type: {day_type}")
        return day_type 
    
    def exp_range(self):
        if not self.prior_close:
            logger.error(f"XTFD | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f"XTFD | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)
        if impvol is None:
            raise ValueError(f"XTFD | exp_range | Product: {self.product_name} | Note: Unknown Product")
        exp_range = self.safe_round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)))
        logger.debug(f"XTFD | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range}")
        return exp_range
    
    def vwap_touch(self):
        logger.debug(f"XTFD | Checking VWAP touch for direction {self.direction}")

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
        
        now = datetime.now(ZoneInfo('America/New_York')).time()
        sorted_periods = sorted(period_times.items(), key=lambda x: x[1])
        finished_periods = [p for p, t in sorted_periods if t <= now]
        logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | TPO Periods: {finished_periods}")

        if not finished_periods:
            logger.debug(f"XTFD vwap_touch | Product: {self.product_name} | No finished periods. Returning False.")
            return False

        ext_index = None
        if self.direction == "short":
            for i, period in enumerate(finished_periods):
                p_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                if p_high is None:
                    logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing HIGH. Skipping.")
                    continue
                if self.safe_round(p_high) > self.ib_high:
                    ext_index = i
                    logger.debug(f"XTFD | vwap_touch| Product: {self.product_name} | Direction: {self.direction} | Found IBH extension at period {period}, index={i}, p_high={p_high}.")
                    break
            if ext_index is None:
                logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction: {self.direction} | No IBH extension found. Returning False.")
                return False

            for i in range(ext_index + 1, len(finished_periods)):
                period = finished_periods[i]
                p_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                if p_low is None:
                    logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing LOW. Skipping.")
                    continue
                p_low = self.safe_round(p_low)
                vwap_var = f"{self.product_name}_ETH_VWAP_{period}"
                period_vwap = self.variables.get(vwap_var)
                if period_vwap is None:
                    logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing VWAP. Skipping.")
                    continue
                period_vwap = self.safe_round(period_vwap)
                if p_low <= period_vwap:
                    logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction: {self.direction} | Period {period} low({p_low}) <= VWAP({period_vwap}). VWAP touch detected.")
                    return False
            return True

        elif self.direction == "long":
            for i, period in enumerate(finished_periods):
                p_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                if p_low is None:
                    logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing LOW. Skipping.")
                    continue
                if self.safe_round(p_low) < self.ib_low:
                    ext_index = i
                    logger.debug(f"XTFD vwap_touch | Product: {self.product_name} | Direction: {self.direction} | Found IBL extension at period {period}, index={i}, p_low={p_low}.")
                    break
            if ext_index is None:
                logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction: {self.direction} | No IBL extension found. Returning False.")
                return False

            for i in range(ext_index + 1, len(finished_periods)):
                period = finished_periods[i]
                p_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                if p_high is None:
                    logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing HIGH. Skipping.")
                    continue
                p_high = self.safe_round(p_high)
                vwap_var = f"{self.product_name}_ETH_VWAP_{period}"
                period_vwap = self.variables.get(vwap_var)
                if period_vwap is None:
                    logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing VWAP. Skipping.")
                    continue
                period_vwap = self.safe_round(period_vwap)
                if p_high >= period_vwap:
                    logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Direction {self.direction} | Period {period} high({p_high}) >= VWAP({period_vwap}). VWAP touch detected.")
                    return False
            return True

        else:
            logger.debug(f"XTFD | vwap_touch | Product: {self.product_name} | Invalid direction specified.")
            return False
    
    def one_time_framing(self):
        if self.product_name == "CL":
            period_times = {
                'A': time(9, 0), 'B': time(9, 30), 'C': time(10, 0),
                'D': time(10, 30), 'E': time(11, 0), 'F': time(11, 30),
                'G': time(12, 0), 'H': time(12, 30), 'I': time(13, 0),
                'J': time(13, 30), 'K': time(14, 0),
            }
            logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Using CL period times.")
        else:
            period_times = {
                'A': time(9, 30), 'B': time(10, 0), 'C': time(10, 30),
                'D': time(11, 0), 'E': time(11, 30), 'F': time(12, 0),
                'G': time(12, 30), 'H': time(13, 0), 'I': time(13, 30),
                'J': time(14, 0), 'K': time(14, 30), 'L': time(15, 0),
                'M': time(15, 30),
            }
            logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Using non-CL period times.")

        now = datetime.now(self.est).time()
        logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Current time: {now}")
        
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
                    
        logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Current Period: {current_period}")
        logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Finished periods: {finished_periods}")
        
        if len(finished_periods) < 2:
            logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Not enough finished periods. Returning False.")
            return False

        period1, period2 = finished_periods[-2], finished_periods[-1]
        logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Last two periods selected: {period1}, {period2}")
        
        p1_high = self.variables.get(f"{self.product_name}_{period1}_HIGH")
        p1_low = self.variables.get(f"{self.product_name}_{period1}_LOW")
        p2_high = self.variables.get(f"{self.product_name}_{period2}_HIGH")
        p2_low = self.variables.get(f"{self.product_name}_{period2}_LOW")
        logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Prior Two Period Raw values: {period1} HIGH={p1_high}, LOW={p1_low}; {period2} HIGH={p2_high}, LOW={p2_low}")
        
        if None in (p1_high, p1_low, p2_high, p2_low):
            logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | One or more period values missing. Returning False.")
            return False
            
        p1_high = self.safe_round(p1_high)
        p1_low = self.safe_round(p1_low)
        p2_high = self.safe_round(p2_high)
        p2_low = self.safe_round(p2_low)
        logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Prior Two Period Rounded values: {period1} HIGH={p1_high}, LOW={p1_low}; {period2} HIGH={p2_high}, LOW={p2_low}")
        
        current_period_high = self.variables.get(f"{self.product_name}_{current_period}_HIGH")
        current_period_low = self.variables.get(f"{self.product_name}_{current_period}_LOW")
        if current_period_high is None or current_period_low is None:
            logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Current period values not found. Returning False.")
            return False
        current_period_high = self.safe_round(current_period_high)
        current_period_low = self.safe_round(current_period_low)
        logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Current period {current_period} HIGH={current_period_high}, LOW={current_period_low}")
        
        if self.direction == "short":
            if p2_high > p1_high and p2_low > p1_low:
                logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Upward one time framing detected for prior periods.")
                if current_period_low >= p2_low:
                    logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Current period acceptable (inside or extending upward). Returning True.")
                    return True
                else:
                    logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Current period low {current_period_low} is below prior low {p2_low}. Returning False.")
                    return False
            else:
                logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Prior periods are not upward one time framing. Returning False.")
                return False
                
        elif self.direction == "long":
            if p2_high < p1_high and p2_low < p1_low:
                logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Downward one time framing detected for prior periods.")
                if current_period_high <= p2_high:
                    logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Current period acceptable (inside or extending downward). Returning True.")
                    return True
                else:
                    logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Current period high {current_period_high} is above prior high {p2_high}. Returning False.")
                    return False
            else:
                logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Direction: {self.direction} | Prior periods are not downward one time framing. Returning False.")
                return False
                
        else:
            logger.debug(f"XTFD | one_time_framing | Product: {self.product_name} | Invalid direction specified. Returning False.")
            return False

# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        def log_condition(condition, description):
            logger.debug(f"XTFD | input | Product: {self.product_name} | Direction: {self.direction} | {description} --> {condition}")
            return condition
        self.day_range_used = max(self.overnight_high, self.day_high) - min(self.overnight_low, self.day_low)
        self.range_used = round((self.day_range_used / self.exp_rng),2)
        if self.direction == "short":
            crit4 = log_condition(
                self.day_vpoc < self.ib_high - 0.35 * (self.ib_high - self.ib_low),
                f"CRITICAL4: day_vpoc({self.day_vpoc}) < ib_high({self.day_high}) - 0.35*(ib_high({self.ib_high}) - ib_low({self.ib_low}))"
            )
        elif self.direction == "long":
            crit4 = log_condition(
                self.day_vpoc > self.ib_low + 0.35 * (self.ib_high - self.ib_low),
                f"CRITICAL4: day_vpoc({self.day_vpoc}) > ib_low({self.ib_low}) + 0.35*(ib_high({self.ib_high}) - ib_low({self.ib_low}))"
            )
        crit1 = log_condition(
            (self.ib_high - self.ib_low) / self.ib_atr >= 1.00,
            f"CRITICAL1: (ib_high({self.ib_high}) - ib_low({self.ib_low}))/ib_atr({self.ib_atr}) >= 1.00"
        )
        crit2 = log_condition(
            self.range_used >= 0.75,
            f"CRITICAL2: range_used({self.range_used}) >= 0.75"
        )
        crit3 = log_condition(
            self.ib_low < self.day_vpoc < self.ib_high,
            f"CRITICAL3: ib_low({self.ib_low}) < day_vpoc({self.day_vpoc}) < ib_high({self.ib_high})"
        )
        crit5 = log_condition(
            abs(self.cpl - self.day_vpoc) > 0.35 * (self.day_high - self.day_low),
            f"CRITICAL5: abs(cpl({self.cpl}) - day_vpoc({self.day_vpoc})) > 0.35*(day_high({self.day_high}) - day_low({self.day_low}))"
        )
        logic = crit1 and crit2 and crit3 and crit4 and crit5
        logger.debug(f"XTFD | input | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {logic} | "
                    f"CRITICAL1: {crit1} | CRITICAL2: {crit2} | CRITICAL3: {crit3} | CRITICAL4: {crit4} | CRITICAL5: {crit5}")
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
                logger.debug(f"XTFD | time_window | Product: {self.product_name} | Within equity alert window: {self.current_time}")
                return True
            else:
                logger.debug(f"XTFD | time_window | Product: {self.product_name} | Outside equity alert window: {self.current_time}")
                return False
        elif self.product_name == 'CL':
            if self.crude_ib <= self.current_time <= self.crude_close:
                logger.debug(f"XTFD | time_window | Product: {self.product_name} | Within crude alert window: {self.current_time}")
                return True
            else:
                logger.debug(f"XTFD | time_window | Product: {self.product_name} | Outside crude alert window: {self.current_time}")
                return False
        else:
            logger.warning(f"XTFD | time_window | Product: {self.product_name} | No time window defined for product")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
        
        # Determine Direction Based on IB Range Logic with Logging
        if self.day_high > self.ib_high and self.day_low < self.ib_low:
            if self.cpl < self.ib_low:
                self.direction = "long"
                logger.debug(f" XTFD | check | Product: {self.product_name} | DIR_LOGIC: self.cpl({self.cpl}) < self.ib_low({self.ib_low}) -> long")
            elif self.cpl > self.ib_high:
                self.direction = "short"
                logger.debug(f" XTFD | check | Product: {self.product_name} | DIR_LOGIC: self.cpl({self.cpl}) > self.ib_high({self.ib_high}) -> short")
            else:
                logger.debug(f" XTFD | check | Product: {self.product_name} | Note: In Middle Of IB Range While Neutral, Returning.")
                return False  # In Middle Of IB Range While Neutral
        else:
            if self.day_low < self.ib_low:
                self.direction = "long"
                logger.debug(f" XTFD | check | Product: {self.product_name} | DIR_LOGIC: self.day_low({self.day_low}) < self.ib_low({self.ib_low}) -> long")
            elif self.day_high > self.ib_high:
                self.direction = "short"
                logger.debug(f" XTFD | check | Product: {self.product_name} | DIR_LOGIC: self.day_high({self.day_high}) > self.ib_high({self.ib_high}) -> short")
            else:
                logger.debug(f" XTFD | check | Product: {self.product_name} | Note: No IB Extension, Returning.")
                return False  # No IB Extension

        # Driving Input Check with Logging
        if self.time_window() and self.input():
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)
                logger.debug(f" XTFD | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                if self.direction != last_alert:
                    logger.info(f" XTFD | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Critical Criteria Logging
                    self.c_expected_range = "x"
                    logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: Set c_expected_range -> [{self.c_expected_range}]")
                    
                    self.c_no_skew = "x"
                    logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: Set c_no_skew -> [{self.c_no_skew}]")
                    
                    self.ib_range = round((self.ib_high - self.ib_low), 2)
                    self.ib_vatr = round((self.ib_range / self.ib_atr), 2)                       
                    self.c_wide_ib = "x"
                    logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: Set c_wide_ib -> [{self.c_wide_ib}]")
                    
                    self.c_divergence = "x"
                    logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: Set c_divergence -> [{self.c_divergence}]")
                    
                    # Logic For One Not Time Framing
                    if not self.one_time_framing():
                        self.c_not_otf = "x"
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: one_time_framing() False -> [{self.c_not_otf}]")
                    else:
                        self.c_not_otf = "  "
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: one_time_framing() True -> [{self.c_not_otf}]")
                    
                    # Logic for No Slope to VWAP
                    if -0.06 < self.vwap_slope < 0.06:
                        self.c_vwap_slope = "x"
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: -0.06 < self.vwap_slope({self.vwap_slope}) < 0.06 -> [{self.c_vwap_slope}]")
                    else:
                        self.c_vwap_slope = "  "
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: -0.06 < self.vwap_slope({self.vwap_slope}) < 0.06 -> [{self.c_vwap_slope}]")

                    # Logic for VWAP Touch after IB Extension
                    if not self.vwap_touch():
                        self.c_touch_vwap = "x"
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: vwap_touch() False -> [{self.c_touch_vwap}]")
                    else:
                        self.c_touch_vwap = "  "
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: vwap_touch() True -> [{self.c_touch_vwap}]")
                    
                    # Logic for Prior Session Directional Check
                    if self.prior_day() in ["Directional", "Semi-Directional"]:
                        self.c_directional = "x"
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_8: prior_day() returned Directional or Semi-Directional -> [{self.c_directional}]")
                    else:
                        self.c_directional = "  "
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_8: prior_day() did not return Directional or Semi-Directional -> [{self.c_directional}]")
                    
                    # Logic for Within 1SD of VWAP
                    if self.direction == "short":
                        if self.cpl < self.top_one_eth_vwap:
                            self.c_osd = "x"
                            logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: self.cpl({self.cpl}) < self.top_one_eth_vwap({self.top_one_eth_vwap}) -> [{self.c_osd}]")
                        else:
                            self.c_osd = "  "
                            logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: self.cpl({self.cpl}) >= self.top_one_eth_vwap({self.top_one_eth_vwap}) -> [{self.c_osd}]")
                    elif self.direction == "long":
                        if self.cpl > self.bottom_one_eth_vwap:
                            self.c_osd = "x"
                            logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: self.cpl({self.cpl}) > self.bottom_one_eth_vwap({self.bottom_one_eth_vwap}) -> [{self.c_osd}]")
                        else:
                            self.c_osd = "  "
                            logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: self.cpl({self.cpl}) <= self.bottom_one_eth_vwap({self.bottom_one_eth_vwap}) -> [{self.c_osd}]")
                    
                    # Logic for Non Directional Open
                    if self.open_type() == "OAIR":
                        self.c_non_dir_open = "x"
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_10: open_type() returned OAIR -> [{self.c_non_dir_open}]")
                    else:
                        self.c_non_dir_open = "  "
                        logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_10: open_type() did not return OAIR -> [{self.c_non_dir_open}]")
                    
                    # Logic For 1.5x IB Stat Complete
                    if self.direction == "short":
                        if self.day_low <= self.ib_low - 0.5 * (self.ib_high - self.ib_low):
                            self.c_ib_ext_stat = "x"
                            logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_11: self.day_low({self.day_low}) <= self.ib_low({self.ib_low}) - 0.5*(self.ib_high({self.ib_high})-self.ib_low({self.ib_low})) -> [{self.c_ib_ext_stat}]")
                        else:
                            self.c_ib_ext_stat = "  "
                            logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_11: self.day_low({self.day_low}) > self.ib_low({self.ib_low}) - 0.5*(self.ib_high({self.ib_high})-self.ib_low({self.ib_low})) -> [{self.c_ib_ext_stat}]")
                    elif self.direction == "long":
                        if self.day_high >= self.ib_high + 0.5 * (self.ib_high - self.ib_low):
                            self.c_ib_ext_stat = "x"
                            logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_11: self.day_high({self.day_high}) >= self.ib_high({self.ib_high}) + 0.5*(self.ib_high({self.ib_high})-self.ib_low({self.ib_low})) -> [{self.c_ib_ext_stat}]")
                        else:
                            self.c_ib_ext_stat = "  "
                            logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_11: self.day_high({self.day_high}) < self.ib_high({self.ib_high}) + 0.5*(self.ib_high({self.ib_high})-self.ib_low({self.ib_low})) -> [{self.c_ib_ext_stat}]")
                    
                    # Score Calculation Logging
                    self.score = sum(1 for condition in [
                        self.c_expected_range, self.c_no_skew, self.c_wide_ib, self.c_divergence,
                        self.c_not_otf, self.c_vwap_slope, self.c_touch_vwap, self.c_directional,
                        self.c_osd, self.c_non_dir_open, self.c_ib_ext_stat
                    ] if condition == "x")
                    logger.debug(f" XTFD | check | Product: {self.product_name} | Direction: {self.direction} | SCORE: {self.score}/11")
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" XTFD | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" XTFD | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f" XTFD | check | Product: {self.product_name} | Note: Condition(s) Not Met")

# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):

        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        direction_settings = {
            "long": {
                "emoji_indicator": "🔼",
                "destination": "IBL",
            },
            "short": {
                "emoji_indicator": "🔽",
                "destination": "IBH",
            }
        }
 
        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" XTFD | discord_message | Note: Invalid direction '{self.direction}'")
        
        if self.open_type() == "OAIR":
            ot = self.open_type()
            colon = ":"
        else:
            ot = ""   
            colon = ""      

        title = f"**{self.product_name} - Playbook Alert** - **XTFD** {settings['emoji_indicator']}"
    
        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: {self.day_vpoc} (DVPOC) \n"
                f"**Risk**: Wrong if Price is Unable to Accept Inside IB \n"
                f"**Driving Input**: IB Is Extended and Price is Divergent to Value \n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()

        embed.add_embed_field(name="**Criteria**", value="", inline=False)

        criteria = (
            f"- **[{self.c_divergence}]** Price to Value Divergence \n"
            f"- **[{self.c_non_dir_open}]** Non-Directional Open{colon} {ot} \n"
            f"- **[{self.c_not_otf}]** Rotational Day (Not One-Time Framing) \n"
            f"- **[{self.c_expected_range}]** At Least 75% of Expected Range Used: ({round((self.range_used*100),2)}%) \n"
            f"- **[{self.c_wide_ib}]** IB is Average to Wide: ({round((self.ib_vatr*100), 2)}%) \n"
            f"- **[{self.c_no_skew}]** No Skew to Profile toward {settings['destination']} Extreme \n"
            f"- **[{self.c_directional}]** Prior Session was Directional \n"
            f"- **[{self.c_vwap_slope}]** No Slope to VWAP: ({round((self.vwap_slope*100),2)}°) \n"
            f"- **[{self.c_ib_ext_stat}]** 1.5x {settings['destination']} Stat Complete \n"
            f"- **[{self.c_touch_vwap}]** Touched VWAP After {settings['destination']} Extension.\n"
            f"- **[{self.c_osd}]** Within 1 Standard Deviation of VWAP \n"
            f"- **[{self.c_directional}]** Prior Session was Directional \n"
        )
        embed.add_embed_field(name="", value=criteria, inline=False)

        embed.add_embed_field(name="**Playbook Score**", value=f"{self.score} / 11", inline=False)
        
        alert_time_text = f"**Alert Time / Price**: {alert_time_formatted} EST | {self.cpl}"
        embed.add_embed_field(name="", value=alert_time_text, inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"XTFD | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")