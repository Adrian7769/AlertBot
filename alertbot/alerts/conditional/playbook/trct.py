import logging
import math
import threading
from datetime import datetime
from alertbot.utils import config
from discord_webhook import DiscordEmbed
from alertbot.alerts.base import Base
from datetime import datetime, time
from zoneinfo import ZoneInfo
from collections import defaultdict

logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class TRCT(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables (Round All Variables)
        self.day_high = self.safe_round(variables.get(f'{product_name}_DAY_HIGH'))
        self.day_low = self.safe_round(variables.get(f'{product_name}_DAY_LOW'))           
        self.prior_high = self.safe_round(variables.get(f'{self.product_name}_PRIOR_HIGH'))
        self.prior_low = self.safe_round(variables.get(f'{self.product_name}_PRIOR_LOW'))
        self.cpl = self.safe_round(variables.get(f'{self.product_name}_CPL'))
        self.prior_close = self.safe_round(variables.get(f'{self.product_name}_PRIOR_CLOSE'))
        self.ib_high = self.safe_round(variables.get(f'{product_name}_IB_HIGH'))
        self.ib_low = self.safe_round(variables.get(f'{product_name}_IB_LOW'))
        self.prior_ibh = self.safe_round(variables.get(f'{self.product_name}_PRIOR_IB_HIGH'))
        self.prior_ibl = self.safe_round(variables.get(f'{self.product_name}_PRIOR_IB_LOW'))          
        self.day_vpoc = self.safe_round(variables.get(f'{product_name}_DAY_VPOC')) 
        self.vwap_slope = variables.get(f'{product_name}_VWAP_SLOPE')
        self.fd_vpoc = self.safe_round(variables.get(f'{product_name}_5D_VPOC'))
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        self.exp_rng = self.exp_range() 
        
    def safe_round(self, value, digits=2):
        if value is None:
            logger.error(f"TRCT | safe_round | Product: {self.product_name} | Missing value for rounding; defaulting to 0.")
            return 0
        try:
            return round(value, digits)
        except Exception as e:
            logger.error(f"TRCT | safe_round | Product: {self.product_name} | Error rounding value {value}: {e}")
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
        logger.debug(f" TRCT | prior_day | Product: {self.product_name} | Prior Day Type: {day_type}")
        return day_type
    
    def exp_range(self):
        if not self.prior_close:
            logger.error(f" TRCT | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" TRCT | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)
        if impvol is None:
            raise ValueError(f" TRCT | exp_range | Product: {self.product_name} | Note: Unknown Product")
        exp_range = self.safe_round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)))
        logger.debug(f" TRCT | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range}")
        return exp_range 
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def trend_day(self):
        """
        For a 'trend day':
        - For long:
        1) Day high must exceed IB_high + 0.5 * IB_range
        2) Acceptance Outside of IB Range: No New Period Lows Made Inside of IB Range.
            Example: If "D" Period Low is at 1800 within IB range, then "E" Low cannot be below 1800
            if it's still inside IB range.
        3) Day_VPOC > IBH
        4) Prior Session Must Be Rotational
        5) self.cpl > current session MID
        6) No period Low <= VWAP after IB extension
        7) RTH VPOC must be within range of the last finished or current period.

        - For short:
        1) Day low < IB_low - 0.5 * IB_range
        2) Acceptance Outside IB Range: No New Period Highs Made Inside IB Range.
        3) Day_VPOC < IBL
        4) Prior Session Must Be Rotational
        5) self.cpl < current session MID
        6) No period High >= VWAP after IB extension
        7) RTH VPOC within the last/current period range.
        """
        ib_range = self.ib_high - self.ib_low
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

        logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | TPO Periods: {finished_periods}")

        # --- LONG DIRECTION ---
        if self.direction == "long":
            # CRITICAL1: Day high must exceed IB_high + 0.5 * IB_range.
            condition1 = self.day_high > self.ib_high + 0.5 * ib_range
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL1: day_high({self.day_high}) > ib_high({self.ib_high}) + 0.5*ib_range --> {condition1}")

            # CRITICAL2: Acceptance Outside IB Range.
            acceptance = True
            prior_low = None
            for period in finished_periods:
                var_name = f"{self.product_name}_{period}_LOW"
                period_low = self.variables.get(var_name)
                if period_low is None:
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | Acceptance: No LOW data for period {period}. Skipping.")
                    continue
                period_low = self.safe_round(period_low)
                if prior_low is not None:
                    if period_low < prior_low and self.ib_low <= period_low <= self.ib_high:
                        logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL2: Acceptance Failed: period {period} low({period_low}) < prior_low({prior_low}) inside IB.")
                        acceptance = False
                        break
                if self.ib_low <= period_low <= self.ib_high:
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | Acceptance: Updating prior_low => {period_low}")
                    prior_low = period_low

            # CRITICAL3: Day_VPOC must be greater than IB_high.
            condition3 = self.day_vpoc > self.ib_high
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL3: day_vpoc({self.day_vpoc}) > ib_high({self.ib_high}) --> {condition3}")

            # CRITICAL4: Prior session must be rotational.
            prior_day_type = self.prior_day()
            condition4 = prior_day_type in ["Rotational"]
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL4: prior_day({prior_day_type}) == 'Rotational' --> {condition4}")

            # CRITICAL5: self.cpl must be greater than current session MID.
            current_mid = (self.day_high + self.day_low) / 2
            condition5 = self.cpl > current_mid
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL5: cpl({self.cpl}) > current_mid({round(current_mid, 2)}) --> {condition5}")

            # CRITICAL6: After IB extension, no subsequent period low can be <= its period ETH VWAP.
            extension_found = False
            condition6 = True
            ib_extension_period = None
            for period in finished_periods:
                var_name_high = f"{self.product_name}_{period}_HIGH"
                period_high = self.variables.get(var_name_high)
                if period_high is None:
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: No HIGH data for period {period}. Skipping.")
                    continue
                period_high = round(period_high, 2)
                if not extension_found and period_high > self.ib_high:
                    extension_found = True
                    ib_extension_period = period
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: Found IB extension at period {period} with high({period_high}).")
                    continue
                if extension_found:
                    var_name_low = f"{self.product_name}_{period}_LOW"
                    period_low = self.variables.get(var_name_low)
                    if period_low is None:
                        logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: No LOW data for period {period}. Skipping.")
                        continue
                    period_low = self.safe_round(period_low)
                    vwap_var = f"{self.product_name}_ETH_VWAP_{period}"
                    period_vwap = self.variables.get(vwap_var)
                    if period_vwap is None:
                        logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: No VWAP data for period {period}. Skipping.")
                        continue
                    period_vwap = self.safe_round(period_vwap)
                    if period_low <= period_vwap:
                        logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: Failed at period {period}: low({period_low}) <= vwap({period_vwap}).")
                        condition6 = False
                        break

            # CRITICAL7: RTH VPOC must be within the range of the last finished or current period.
            if len(finished_periods) >= 2:
                period1 = finished_periods[-2]
                period2 = finished_periods[-1]
                period1_high = self.variables.get(f"{self.product_name}_{period1}_HIGH")
                period1_low = self.variables.get(f"{self.product_name}_{period1}_LOW")
                period2_high = self.variables.get(f"{self.product_name}_{period2}_HIGH")
                period2_low = self.variables.get(f"{self.product_name}_{period2}_LOW")
                if None not in (period1_high, period1_low, period2_high, period2_low):
                    period1_high = self.safe_round(period1_high)
                    period1_low = self.safe_round(period1_low)
                    period2_high = self.safe_round(period2_high)
                    period2_low = self.safe_round(period2_low)
                    high_range = max(period1_high, period2_high)
                    low_range = min(period1_low, period2_low)
                    condition7 = (low_range < self.day_vpoc < high_range)
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL7: Day VPOC ({self.day_vpoc}) within range ({low_range} - {high_range}) --> {condition7}")
                else:
                    condition7 = False
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL7: Insufficient period data for VPOC range check --> {condition7}")
            else:
                condition7 = False
                logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL7: Not enough finished periods for VPOC range check --> {condition7}")

            final_logic = condition1 and acceptance and condition3 and condition4 and condition5 and condition6 and condition7
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {final_logic} | CRITICAL1: {condition1} | CRITICAL2: {acceptance} | CRITICAL3: {condition3} | CRITICAL4: {condition4} | CRITICAL5: {condition5} | CRITICAL6: {condition6} | CRITICAL7: {condition7}")
            
            self.ib_acceptance_l = acceptance  # For Check Method.
            return final_logic

        # --- SHORT DIRECTION ---
        elif self.direction == "short":
            # CRITICAL1: Day low must be below IB_low - 0.5 * IB_range.
            condition1 = self.day_low < self.ib_low - 0.5 * ib_range
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL1: day_low({self.day_low}) < ib_low({self.ib_low}) - 0.5*ib_range --> {condition1}")

            # CRITICAL2: Acceptance Outside IB Range.
            acceptance = True
            prior_high = None
            for period in finished_periods:
                var_name = f"{self.product_name}_{period}_HIGH"
                period_high = self.variables.get(var_name)
                if period_high is None:
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | Acceptance: No HIGH data for period {period}. Skipping.")
                    continue
                period_high = self.safe_round(period_high)
                if prior_high is not None:
                    if period_high > prior_high and self.ib_low <= period_high <= self.ib_high:
                        logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL2: Acceptance Failed: period {period} high({period_high}) > prior_high({prior_high}) inside IB.")
                        acceptance = False
                        break
                if self.ib_low <= period_high <= self.ib_high:
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | Acceptance: Updating prior_high => {period_high}")
                    prior_high = period_high

            # CRITICAL3: Day_VPOC must be less than IB_low.
            condition3 = self.day_vpoc < self.ib_low
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL3: day_vpoc({self.day_vpoc}) < ib_low({self.ib_low}) --> {condition3}")

            # CRITICAL4: Prior session must be rotational.
            prior_day_type = self.prior_day()
            condition4 = prior_day_type in ["Rotational"]
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL4: prior_day({prior_day_type}) == 'Rotational' --> {condition4}")

            # CRITICAL5: self.cpl must be less than current session MID.
            current_mid = (self.day_high + self.day_low) / 2
            condition5 = self.cpl < current_mid
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL5: cpl({self.cpl}) < current_mid({round(current_mid, 2)}) --> {condition5}")

            # CRITICAL6: After IB extension, no subsequent period high can be >= its period ETH VWAP.
            extension_found = False
            condition6 = True
            ib_extension_period = None
            for period in finished_periods:
                var_name_low = f"{self.product_name}_{period}_LOW"
                period_low = self.variables.get(var_name_low)
                if period_low is None:
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: No LOW data for period {period}. Skipping.")
                    continue
                period_low = self.safe_round(period_low)
                if not extension_found and period_low < self.ib_low:
                    extension_found = True
                    ib_extension_period = period
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: Found IB extension at period {period} with low({period_low}).")
                    continue
                if extension_found:
                    var_name_high = f"{self.product_name}_{period}_HIGH"
                    period_high = self.variables.get(var_name_high)
                    if period_high is None:
                        logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: No HIGH data for period {period}. Skipping.")
                        continue
                    period_high = self.safe_round(period_high)
                    vwap_var = f"{self.product_name}_ETH_VWAP_{period}"
                    period_vwap = self.variables.get(vwap_var)
                    if period_vwap is None:
                        logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: No VWAP data for period {period}. Skipping.")
                        continue
                    period_vwap = self.safe_round(period_vwap)
                    if period_high >= period_vwap:
                        logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: Failed at period {period}: high({period_high}) >= vwap({period_vwap}).")
                        condition6 = False
                        break

            # CRITICAL7: RTH VPOC must be within the range of the last finished or current period.
            if len(finished_periods) >= 2:
                period1 = finished_periods[-2]
                period2 = finished_periods[-1]
                period1_high = self.variables.get(f"{self.product_name}_{period1}_HIGH")
                period1_low = self.variables.get(f"{self.product_name}_{period1}_LOW")
                period2_high = self.variables.get(f"{self.product_name}_{period2}_HIGH")
                period2_low = self.variables.get(f"{self.product_name}_{period2}_LOW")
                if None not in (period1_high, period1_low, period2_high, period2_low):
                    period1_high = self.safe_round(period1_high)
                    period1_low = self.safe_round(period1_low)
                    period2_high = self.safe_round(period2_high)
                    period2_low = self.safe_round(period2_low)
                    high_range = max(period1_high, period2_high)
                    low_range = min(period1_low, period2_low)
                    condition7 = (low_range < self.day_vpoc < high_range)
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL7: Day VPOC ({self.day_vpoc}) within range ({low_range} - {high_range}) --> {condition7}")
                else:
                    condition7 = False
                    logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL7: Insufficient period data for VPOC range check --> {condition7}")
            else:
                condition7 = False
                logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | CRITICAL7: Not enough finished periods for VPOC range check --> {condition7}")

            final_logic = condition1 and acceptance and condition3 and condition4 and condition5 and condition6 and condition7
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {final_logic} | CRITICAL1: {condition1} | CRITICAL2: {acceptance} | CRITICAL3: {condition3} | CRITICAL4: {condition4} | CRITICAL5: {condition5} | CRITICAL6: {condition6} | CRITICAL7: {condition7}")
            
            self.ib_acceptance_s = acceptance
            self.value_following_price = condition7
            return final_logic
        else:
            logger.debug(f"TRCT | trend_day | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: False | No valid direction detected.")
            return False


    def float_range(self, start, stop, step):
        """
        Yields a sequence of floating-point numbers from `start` up to `stop`
        (inclusive), stepping by `step`. 
        """
        epsilon = 1e-9
        num_steps = int(math.floor((stop - start) / step + 0.5))
        logger.debug(f"TRCT | float_range | Product: {self.product_name} | start={start}, stop={stop}, step={step}, num_steps={num_steps}")
        for i in range(num_steps + 1):
            val = start + i * step
            if val > stop + epsilon:
                break
            yield_val = round(val, 10)
            yield yield_val

    def single_prints(self, finished_periods):
        """
        Returns True if there's at least one single print *within the overlapped region*
        of the session and inside a 'middle' sub-period (not the first or last).

        A single print is defined as a price that appears in exactly one 'middle'
        sub-period's range, strictly within the 'lowest_overlapped_price' and
        'highest_overlapped_price' boundaries.
        """
        logger.debug(f"TRCT | single_prints | Product: {self.product_name} | Finished Periods: {finished_periods}")
        if len(finished_periods) < 3:
            logger.debug(f"TRCT | single_prints | Product: {self.product_name} | Not enough periods (need >= 3). Returning False.")
            return False

        first_subperiod = finished_periods[0]
        last_subperiod = finished_periods[-1]
        middle_periods = finished_periods[1:-1]
        logger.debug(f"TRCT | single_prints | Product: {self.product_name} | Middle Sub-Periods: {middle_periods}")

        tick_size_map = {
            "ES": 0.25,
            "NQ": 0.25,
            "RTY": 0.10,
            "CL": 0.01
        }
        tick_size = tick_size_map.get(self.product_name, 1.0)
        logger.debug(f"TRCT | single_prints | Product: {self.product_name} | tick_size = {tick_size}")

        price_map = defaultdict(set)
        min_price = float('inf')
        max_price = float('-inf')

        # 1) Gather overall min/max and build price->subperiods map
        for period in finished_periods:
            p_low = self.variables.get(f"{self.product_name}_{period}_LOW")
            p_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
            if p_low is None or p_high is None:
                logger.debug(f"TRCT | single_prints | Product: {self.product_name} | Period {period} missing data (LOW or HIGH). Skipping.")
                continue
            low_val = float(p_low)
            high_val = float(p_high)

            if low_val < min_price:
                min_price = low_val
            if high_val > max_price:
                max_price = high_val

            for price in self.float_range(low_val, high_val, tick_size):
                price_map[price].add(period)

        if min_price == float('inf') or max_price == float('-inf'):
            logger.debug(f"TRCT | single_prints | Product: {self.product_name} | No valid min/max price found. Returning False.")
            return False

        logger.debug(f"TRCT | single_prints | Product: {self.product_name} | min_price: {min_price} | max_price={max_price}")

        # 2) Find the lowest_overlapped_price
        lowest_overlapped_price = None
        for price in self.float_range(min_price, max_price, tick_size):
            if len(price_map[price]) >= 2:
                lowest_overlapped_price = price
                logger.debug(f"TRCT | single_prints | Product: {self.product_name} | lowest_overlapped_price: {lowest_overlapped_price}")
                break

        # 3) Find the highest_overlapped_price
        highest_overlapped_price = None
        reversed_prices = list(self.float_range(min_price, max_price, tick_size))
        reversed_prices.reverse()
        for price in reversed_prices:
            if len(price_map[price]) >= 2:
                highest_overlapped_price = price
                logger.debug(f"TRCT | single_prints | Product: {self.product_name} | highest_overlapped_price: {highest_overlapped_price}")
                break

        # 4) If no overlapped region
        if (lowest_overlapped_price is None or
            highest_overlapped_price is None or
            lowest_overlapped_price >= highest_overlapped_price):
            logger.debug(f"TRCT | single_prints | Product: {self.product_name} | No valid overlapped region. Returning False.")
            return False

        logger.debug(f"TRCT | single_prints | Product: {self.product_name} | Overlapped region: {lowest_overlapped_price} -> {highest_overlapped_price}")

        # 5) Check for a price that belongs to exactly one middle sub-period
        for price in self.float_range(lowest_overlapped_price, highest_overlapped_price, tick_size):
            if len(price_map[price]) == 1:
                # Extract the single sub-period
                (unique_period,) = price_map[price]
                if unique_period in middle_periods:
                    logger.debug(f"TRCT | single_prints | Product: {self.product_name} | Found single print price={price} in sub-period={unique_period}. Returning True.")
                    return True

        logger.debug(f"TRCT | single_prints | Product: {self.product_name} | No single prints found. Returning False.")
        return False

    def strong_trending(self):
        """
        For a 'strong trending':
        -- LONG direction:
            1) After IBH extension, no new period lows below the previous period low
                if that previous low is itself below `eth_top_1_{previous_period}`.
            2) Prior session must be 'Rotational'.
            3) After IBH extension, no sub-period's low can be <= that sub-period's ETH VWAP.
            4) cpl > session MID.
            5) One-time framing >= 3 consecutive sub-periods with higher highs & higher lows
                after the extension sub-period.
            6) Single prints must be present.

            -- SHORT direction:
            1) After IBL extension, no new period highs above the previous period high
                if that previous high is itself above `eth_bottom_1_{previous_period}`.
            2) Prior session must be 'Rotational'.
            3) After IBL extension, no sub-period's high can be >= that sub-period's ETH VWAP.
            4) cpl < session MID.
            5) One-time framing >= 3 consecutive sub-periods with lower highs & lower lows
                after the extension sub-period.
            6) Single prints must be present.
        """
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
        logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | TPO Periods: {finished_periods}")

        if not finished_periods:
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | No finished periods. Returning False.")
            return False

        # Decide direction
        if self.direction == "long":
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Checking LONG strong trending criteria...")

            # 1) Find IBH extension
            ext_found = False
            ext_index = None
            for i, period in enumerate(finished_periods):
                p_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                if p_high is None:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing HIGH. Skipping.")
                    continue
                if self.safe_round(p_high) > self.ib_high:
                    ext_found = True
                    ext_index = i
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Found IBH extension at period {period}, index={i}, p_high={p_high}.")
                    break
            if not ext_found:
                logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | No IBH extension found. Returning False.")
                return False

            # Trending channel acceptance
            trending_acceptance = True
            outside_low = None
            for i in range(ext_index, len(finished_periods)):
                period = finished_periods[i]
                p_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                p_top1 = self.variables.get(f"{self.product_name}_ETH_TOP_1_{period}")
                if p_low is None or p_top1 is None:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Missing data (LOW or TOP_1) for period {period}. Skipping.")
                    continue
                p_low = self.safe_round(p_low)
                p_top1 = self.safe_round(p_top1)
                if p_low < p_top1:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} outside channel. low({p_low}) < top1({p_top1}).")
                    if outside_low is None:
                        outside_low = p_low
                        logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Setting outside_low={outside_low}.")
                    else:
                        if p_low < outside_low:
                            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | New lower outside low={p_low} < old outside_low={outside_low}. Failing.")
                            trending_acceptance = False
                            break

            # 2) Prior session must be 'Rotational'
            prior_session_type = self.prior_day()
            condition2 = (prior_session_type == "Rotational")
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL2: prior_day({prior_session_type}) == 'Rotational' --> {condition2}")

            # 3) No VWAP Touch after IBH extension
            condition3 = True
            for i in range(ext_index + 1, len(finished_periods)):
                period = finished_periods[i]
                p_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                if p_low is None:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing LOW. Skipping.")
                    continue
                p_low = self.safe_round(p_low)
                vwap_var = f"{self.product_name}_ETH_VWAP_{period}"
                period_vwap = self.variables.get(vwap_var)
                if period_vwap is None:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing VWAP. Skipping.")
                    continue
                period_vwap = self.safe_round(period_vwap)
                if p_low <= period_vwap:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} low({p_low}) <= vwap({period_vwap}). Failing CRITICAL3.")
                    condition3 = False
                    break

            # 4) cpl > session MID
            session_mid = (self.day_high + self.day_low) / 2
            condition4 = (self.cpl > session_mid)
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL4: cpl({self.cpl}) > session_mid({session_mid}) --> {condition4}")

            # 5) One-time framing >= 3 consecutive sub-periods after the extension
            one_time_count = 0
            if ext_index < len(finished_periods) - 1:
                prev_period = finished_periods[ext_index]
                prev_high = self.variables.get(f"{self.product_name}_{prev_period}_HIGH")
                prev_low = self.variables.get(f"{self.product_name}_{prev_period}_LOW")
                if prev_high is not None and prev_low is not None:
                    prev_high = self.safe_round(prev_high)
                    prev_low = self.safe_round(prev_low)
                    for period in finished_periods[ext_index + 1:]:
                        cur_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                        cur_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                        if cur_high is None or cur_low is None:
                            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Missing data in period {period} for OTF check. Skipping.")
                            continue
                        cur_high = self.safe_round(cur_high)
                        cur_low = self.safe_round(cur_low)
                        if cur_high > prev_high and cur_low > prev_low:
                            one_time_count += 1
                            prev_high = cur_high
                            prev_low = cur_low
                            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL5: OTF +1 => {one_time_count} during (period {period}).")
                        else:
                            one_time_count = 0
                            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL5: OTF reset to 0 during (period {period}).")
            condition5 = (one_time_count >= 3)
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL5: one_time_count({one_time_count}) >= 3 --> {condition5}")

            # 6) Single prints must be present
            condition6 = self.single_prints(finished_periods)
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: single_prints --> {condition6}")

            final_logic = trending_acceptance and condition2 and condition3 and condition4 and condition5 and condition6
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {final_logic} | CRITICAL1: {trending_acceptance} | CRITICAL2: {condition2} | CRITICAL3: {condition3} | CRITICAL4: {condition4} | CRITICAL5: {condition5} | CRITICAL6: {condition6}")
            
            # Make Accessible to Check Method.
            self.trending_acceptance_l = trending_acceptance
            self.session_mid_l = condition4
            self.one_time_framing_l = condition5
            
            return final_logic

        elif self.direction == "short":
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Checking SHORT strong trending criteria...")
            # 1) Find IBL extension
            ext_found = False
            ext_index = None
            for i, period in enumerate(finished_periods):
                p_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                if p_low is None:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing LOW. Skipping.")
                    continue
                if self.safe_round(p_low) < self.ib_low:
                    ext_found = True
                    ext_index = i
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Found IBL extension at period {period}, index={i}, p_low={p_low}.")
                    break
            if not ext_found:
                logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | No IBL extension found. Returning False.")
                return False

            trending_acceptance = True
            outside_high = None
            for i in range(ext_index, len(finished_periods)):
                period = finished_periods[i]
                p_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                p_bottom1 = self.variables.get(f"{self.product_name}_ETH_BOTTOM_1_{period}")
                if p_high is None or p_bottom1 is None:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Missing data (HIGH or BOTTOM_1) for period {period}. Skipping.")
                    continue
                p_high = self.safe_round(p_high)
                p_bottom1 = self.safe_round(p_bottom1)
                if p_high > p_bottom1:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} outside channel. high({p_high}) > bottom1({p_bottom1}).")
                    if outside_high is None:
                        outside_high = p_high
                        logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Setting outside_high={outside_high}.")
                    else:
                        if p_high > outside_high:
                            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | New higher outside high={p_high} > old outside_high={outside_high}. Failing.")
                            trending_acceptance = False
                            break

            # 2) Prior session must be 'Rotational'
            prior_session_type = self.prior_day()
            condition2 = (prior_session_type == "Rotational")
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL2: prior_day({prior_session_type}) == 'Rotational' --> {condition2}")

            # 3) No VWAP Touch after IBL extension
            condition3 = True
            for i in range(ext_index + 1, len(finished_periods)):
                period = finished_periods[i]
                p_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                if p_high is None:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing HIGH. Skipping.")
                    continue
                p_high = self.safe_round(p_high)
                vwap_var = f"{self.product_name}_ETH_VWAP_{period}"
                period_vwap = self.variables.get(vwap_var)
                if period_vwap is None:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} missing VWAP. Skipping.")
                    continue
                period_vwap = self.safe_round(period_vwap, 2)
                if p_high >= period_vwap:
                    logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Period {period} high({p_high}) >= vwap({period_vwap}). Failing condition3.")
                    condition3 = False
                    break

            # 4) cpl < session MID
            session_mid = (self.day_high + self.day_low) / 2
            condition4 = (self.cpl < session_mid)
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL4: cpl({self.cpl}) < session_mid({session_mid}) --> {condition4}")

            # 5) One-time framing >= 3 consecutive sub-periods after the extension
            one_time_count = 0
            if ext_index < len(finished_periods) - 1:
                prev_period = finished_periods[ext_index]
                prev_high = self.variables.get(f"{self.product_name}_{prev_period}_HIGH")
                prev_low = self.variables.get(f"{self.product_name}_{prev_period}_LOW")
                if prev_high is not None and prev_low is not None:
                    prev_high = self.safe_round(prev_high)
                    prev_low = self.safe_round(prev_low)
                    for period in finished_periods[ext_index + 1:]:
                        cur_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                        cur_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                        if cur_high is None or cur_low is None:
                            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Missing data in period {period} for OTF check. Skipping.")
                            continue
                        cur_high = self.safe_round(cur_high)
                        cur_low = self.safe_round(cur_low)
                        if cur_high < prev_high and cur_low < prev_low:
                            one_time_count += 1
                            prev_high = cur_high
                            prev_low = cur_low
                            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL5: OTF +1 => {one_time_count} (period {period}).")
                        else:
                            one_time_count = 0
                            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL5: OTF reset to 0 (period {period}).")
            condition5 = (one_time_count >= 3)
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL5: one_time_count({one_time_count}) >= 3 --> {condition5}")

            # 6) Single prints must be present
            condition6 = self.single_prints(finished_periods)
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | CRITICAL6: single_prints --> {condition6}")

            final_logic = trending_acceptance and condition2 and condition3 and condition4 and condition5 and condition6
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {final_logic} | CRITICAL1: {trending_acceptance} | CRITICAL2: {condition2} | CRITICAL3: {condition3} | CRITICAL4: {condition4} | CRITICAL5: {condition5} | CRITICAL6: {condition6}")
            
            self.trending_acceptance_s = trending_acceptance
            self.prior_session_rotational = condition2
            self.session_mid_s = condition4
            self.one_time_framing_s = condition5
            
            return final_logic

        else:
            logger.debug(f"TRCT | strong_trending | Product: {self.product_name} | Direction: {self.direction} | Invalid direction ({self.direction}). Returning False.")
            return False


    def input(self):
        def log_condition(condition, description):
            logger.debug(f"TRCT | input | Product: {self.product_name} | Direction: {self.direction} | {description} --> {condition}")
            return condition

        trend_day_result = log_condition(self.trend_day(), "Trend Day Conditions")
        strong_trending_result = log_condition(self.strong_trending(), "Strong Trending Conditions")
        
        logic = trend_day_result or strong_trending_result

        logger.debug(f"TRCT | input | Product: {self.product_name} | FINAL_LOGIC: {logic} | Trend Day: {trend_day_result} | Strong Trending: {strong_trending_result}")
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
            logger.debug(f" TRCT | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        elif self.product_name in ['ES', 'RTY', 'NQ']:
            start_time = self.equity_ib
            end_time = self.equity_close
            logger.debug(f" TRCT | time_window | Product: {self.product_name} | Time Window: {start_time} - {end_time}")
        else:
            logger.warning(f" TRCT | time_window | Product: {self.product_name} | No time window defined.")
            return False  
        
        # Check if current time is within the window
        if start_time <= self.current_time <= end_time:
            logger.debug(f" TRCT | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" TRCT | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
        
        # Define Direction with Detailed Logging
        if self.day_low < self.ib_low:
            self.direction = "short"
            logger.debug(f" TRCT | check | Product: {self.product_name} | DIR_LOGIC: self.day_low({self.day_low}) < self.ib_low({self.ib_low}) -> short")
        elif self.day_high > self.ib_high:
            self.direction = "long"
            logger.debug(f" TRCT | check | Product: {self.product_name} | DIR_LOGIC: self.day_high({self.day_high}) > self.ib_high({self.ib_high}) -> long")
        elif self.day_high > self.ib_high and self.day_low < self.ib_low:
            logger.info(f" TRCT | check | Product: {self.product_name} | Note: Neutral Behavior Detected, Returning")
            return
        else:
            logger.info(f" TRCT | check | Product: {self.product_name} | Note: No IB Extension Detected, Returning")
            return

        self.color = "red" if self.direction == "short" else "green"
        
        # Driving Input Check with Detailed Logging
        if self.time_window() and self.input():
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)
                logger.debug(f" TRCT | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                if self.direction != last_alert:
                    logger.info(f" TRCT | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Logic For Trend Day
                    if self.trend_day():
                        self.c_trend_day = "x"
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: trend_day() True -> [{self.c_trend_day}]")
                    else:
                        self.c_trend_day = "  "
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: trend_day() False -> [{self.c_trend_day}]")
                    
                    # Logic For Strong Trending
                    if self.strong_trending():
                        self.c_strong_trending = "x"
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: strong_trending() True -> [{self.c_strong_trending}]")
                    else:
                        self.c_strong_trending = "  "
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: strong_trending() False -> [{self.c_strong_trending}]")
                    
                    # Logic For Acceptance Inside Trending Channel
                    if self.direction == "short":
                        if self.trending_acceptance_s:
                            self.c_trending_acceptance = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: trending_acceptance_s True -> [{self.c_trending_acceptance}]")
                        else:
                            self.c_trending_acceptance = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: trending_acceptance_s False -> [{self.c_trending_acceptance}]")
                    elif self.direction == "long":
                        if self.trending_acceptance_l:
                            self.c_trending_acceptance = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: trending_acceptance_l True -> [{self.c_trending_acceptance}]")
                        else:
                            self.c_trending_acceptance = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: trending_acceptance_l False -> [{self.c_trending_acceptance}]")
                    
                    # Logic For VWAP Strength
                    if self.direction == "short":
                        if self.vwap_slope < -0.05:
                            self.c_strong_vwap = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: self.vwap_slope({self.vwap_slope}) < -0.05 -> [{self.c_strong_vwap}]")
                        else:
                            self.c_strong_vwap = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: self.vwap_slope({self.vwap_slope}) >= -0.05 -> [{self.c_strong_vwap}]")
                    elif self.direction == "long":
                        if self.vwap_slope > 0.05:
                            self.c_strong_vwap = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: self.vwap_slope({self.vwap_slope}) > 0.05 -> [{self.c_strong_vwap}]")
                        else:
                            self.c_strong_vwap = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: self.vwap_slope({self.vwap_slope}) <= 0.05 -> [{self.c_strong_vwap}]")
                    
                    # Logic For One-Time-Framing
                    if self.direction == "short":
                        if self.one_time_framing_s:
                            self.c_otf = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: one_time_framing_s True -> [{self.c_otf}]")
                        else:
                            self.c_otf = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: one_time_framing_s False -> [{self.c_otf}]")
                    elif self.direction == "long":
                        if self.one_time_framing_l:
                            self.c_otf = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: one_time_framing_l True -> [{self.c_otf}]")
                        else:
                            self.c_otf = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: one_time_framing_l False -> [{self.c_otf}]")
                    
                    # Logic For Acceptance Outside of IB Range
                    if self.direction == "short":
                        if self.ib_acceptance_s:
                            self.c_iba = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: ib_acceptance_s True -> [{self.c_iba}]")
                        else:
                            self.c_iba = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: ib_acceptance_s False -> [{self.c_iba}]")
                    elif self.direction == "long":
                        if self.ib_acceptance_l:
                            self.c_iba = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: ib_acceptance_l True -> [{self.c_iba}]")
                        else:
                            self.c_iba = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: ib_acceptance_l False -> [{self.c_iba}]")
                    
                    # Logic For Within 1 EXP Move of 5D
                    if self.cpl < (self.fd_vpoc + self.exp_rng) and self.cpl > (self.fd_vpoc - self.exp_rng):
                        self.c_fd_exp = "x"
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: self.cpl({self.cpl}) within 1 EXP move of fd_vpoc({self.fd_vpoc}) ± exp_rng({self.exp_rng}) -> [{self.c_fd_exp}]")
                    else:
                        self.c_fd_exp = "  "
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_7: self.cpl({self.cpl}) outside 1 EXP move of fd_vpoc({self.fd_vpoc}) ± exp_rng({self.exp_rng}) -> [{self.c_fd_exp}]")
                    
                    # Logic For Value Following Price
                    if self.value_following_price:
                        self.c_v_fp = "x"
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_8: value_following_price True -> [{self.c_v_fp}]")
                    else:
                        self.c_v_fp = "  "
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_8: value_following_price False -> [{self.c_v_fp}]")
                    
                    # Logic For Above / Below RTH MID
                    if self.direction == "short":
                        if self.session_mid_s:
                            self.c_sm = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: session_mid_s True -> [{self.c_sm}]")
                        else:
                            self.c_sm = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: session_mid_s False -> [{self.c_sm}]")
                    elif self.direction == "long":
                        if self.session_mid_l:
                            self.c_sm = "x"
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: session_mid_l True -> [{self.c_sm}]")
                        else:
                            self.c_sm = "  "
                            logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_9: session_mid_l False -> [{self.c_sm}]")
                    
                    # Logic For Prior Day Was Rotational
                    if self.prior_day() == "Rotational":
                        self.c_rotational = "x"
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_10: prior_day() returned Rotational -> [{self.c_rotational}]")
                    else:
                        self.c_rotational = "  "
                        logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_10: prior_day() did not return Rotational -> [{self.c_rotational}]")
                    
                    # Score Calculation Logging
                    self.score = sum(1 for condition in [
                        self.c_rotational, self.c_sm, self.c_v_fp, self.c_fd_exp, self.c_iba,
                        self.c_otf, self.c_strong_vwap, self.c_trending_acceptance, self.c_strong_trending, self.c_trend_day
                    ] if condition == "x")
                    logger.debug(f" TRCT | check | Product: {self.product_name} | Direction: {self.direction} | SCORE: {self.score}/10")
                    
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" TRCT | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" TRCT | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.info(f" TRCT | check | Product: {self.product_name} | Note: Condition(s) Not Met")

# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):
        
        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        
        direction_settings = {
            "long": {
                "emoji_indicator": "🔼",
                "destination": "Highs",
                "mid": "Above",
            },
            "short": {
               
                "destination": "Lows",
                "mid": "Below",
                "emoji_indicator": "🔽",
            }
        }

        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" TRCT | discord_message | Product: {self.product_name} | Note: Invalid direction '{self.direction}'")
        if self.direction == "long":
            if self.vwap_slope > 0.05:
                inline_text = f"Strong Slope to dVWAP: ({self.vwap_slope*100})\n"
            else:
                inline_text = f"Strong Slope to dVWAP \n"
        elif self.direction == "short":
            if self.vwap_slope < -0.05:
                inline_text = f"Strong Slope to dVWAP: ({self.vwap_slope*100})\n"
            else:
                inline_text = f"Strong Slope to dVWAP \n"        
        # Title Construction with Emojis
        title = f"**{self.product_name} - Playbook Alert** - **TRCT** {settings['emoji_indicator']}"

        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: _{settings['destination']} of the session in the last hour\n"
                f"**Risk**: Wrong if auction stops OTF for more than one 30m period, accepts back inside IB, or returns to VWAP\n"
                f"**Driving Input**:The auction is presenting a trend day. This trade seeks entry with the participants who are driving trend.\n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp()  # Automatically sets the timestamp to current time

        # Criteria Header
        embed.add_embed_field(name="**Criteria**", value="\u200b", inline=False)

        # Criteria Details
        criteria = (
            f"• [{self.c_trend_day}] Trend Day | [{self.c_strong_trending}] Strong Trending\n"
            f"• [{self.c_otf}] One Time Framing \n"
            f"• [{self.c_iba}] Acceptance Outside of IB Range\n"
            f"• [{self.c_strong_vwap}] {inline_text}"
            f"• [{self.c_trending_acceptance}] Holding In Trending Channel\n"
            f"• [{self.c_v_fp}] Value Following Price\n"
            f"• [{self.c_sm}] {settings['mid']} RTH Mid\n"
            f"• [{self.c_rotational}] Prior Day Was Rotational\n"
            f"• [{self.c_fd_exp}] Within 1 Expected Move of the 5D\n"
        )
        embed.add_embed_field(name="\u200b", value=criteria, inline=False)

        # Playbook Score
        embed.add_embed_field(name="**Playbook Score**", value=f"_{self.score} / 9_", inline=False)
        
        # Alert Time and Price Context
        alert_time_text = f"**Alert Time / Price**: _{alert_time_formatted} EST | {self.cpl}_"
        embed.add_embed_field(name="\u200b", value=alert_time_text, inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"TRCT | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")