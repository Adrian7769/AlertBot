import logging
import math
import threading
from datetime import datetime, time
from alertbot.utils import config
from discord_webhook import DiscordEmbed
from alertbot.alerts.base import Base
from alertbot.source.alert_logger import log_alert_async
from zoneinfo import ZoneInfo
logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class XTFD(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables (Round All Variables)
        self.prior_vpoc = round(self.variables.get(f'{self.product_name}_PRIOR_VPOC'), 2)
        self.day_vpoc = round(variables.get(f'{product_name}_DAY_VPOC'), 2)         
        self.day_open = round(self.variables.get(f'{self.product_name}_DAY_OPEN'), 2)
        self.prior_high = round(self.variables.get(f'{self.product_name}_PRIOR_HIGH'), 2)
        self.prior_low = round(self.variables.get(f'{self.product_name}_PRIOR_LOW'), 2)
        self.ib_atr = round(self.variables.get(f'{self.product_name}_IB_ATR'), 2)
        self.day_high = round(variables.get(f'{product_name}_DAY_HIGH'), 2)
        self.day_low = round(variables.get(f'{product_name}_DAY_LOW'), 2)         
        self.euro_ibh = round(self.variables.get(f'{self.product_name}_EURO_IBH'), 2)
        self.euro_ibl = round(self.variables.get(f'{self.product_name}_EURO_IBL'), 2)
        self.orh = round(self.variables.get(f'{self.product_name}_ORH'), 2)
        self.orl = round(self.variables.get(f'{self.product_name}_ORL'), 2)
        self.vwap_slope = variables.get(f'{product_name}_VWAP_SLOPE')        
        self.eth_vwap = round(self.variables.get(f'{self.product_name}_ETH_VWAP'), 2)
        self.cpl = round(self.variables.get(f'{self.product_name}_CPL'), 2)
        self.prior_ibh = round(self.variables.get(f'{self.product_name}_PRIOR_IB_HIGH'), 2)
        self.prior_ibl = round(self.variables.get(f'{self.product_name}_PRIOR_IB_LOW'), 2)         
        self.prior_close = round(self.variables.get(f'{self.product_name}_PRIOR_CLOSE'), 2)
        self.top_one_eth_vwap = round(self.variables.get(f'{self.product_name}_ETH_TOP_1'))
        self.bottom_one_eth_vwap = round(self.variables.get(f'{self.product_name}_ETH_BOTTOM_1'))
        self.a_high = round(variables.get(f'{product_name}_A_HIGH'), 2)
        self.a_low = round(variables.get(f'{product_name}_A_LOW'), 2)
        self.b_high = round(variables.get(f'{product_name}_B_HIGH'), 2)
        self.b_low = round(variables.get(f'{product_name}_B_LOW'), 2)        
        self.overnight_high = round(variables.get(f'{product_name}_OVNH'), 2)
        self.overnight_low = round(variables.get(f'{product_name}_OVNL'), 2)        
        self.ib_high = round(self.variables.get(f'{product_name}_IB_HIGH'), 2)
        self.ib_low = round(self.variables.get(f'{product_name}_IB_LOW'), 2)
        
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        
        self.exp_rng = self.exp_range() 

# ---------------------------------- Specific Calculations ------------------------------------ #   
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
        logger.debug(f" TRCT | prior_day | Prior Day Type: {day_type}")
        return day_type    
    def exp_range(self):

        # Calculation (product specific or Not)
        if not self.prior_close:
            logger.error(f" XTFD | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" XTFD | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)

        if impvol is None:
            raise ValueError(f"XTFD | exp_range | Product: {self.product_name} | Note: Unknown Product")

        exp_range = round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)), 2)

        logger.debug(f" XTFD | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range}")
        return exp_range
    def vwap_touch(self):
        """
        Check for no VWAP touch after IB extension.
        
        This method:
        1. Calculates finished periods based on product and current time.
        2. Determines the extension index (IBH for long, IBL for short).
        3. Checks that no period after the extension touches VWAP:
        - For LONG: No period's low is <= its VWAP.
        - For SHORT: No period's high is >= its VWAP.
        
        Returns:
            True if no VWAP touch is detected after the extension, False otherwise.
        """
        logger.debug(f" XTFD | Checking VWAP touch for direction {self.direction}")

        # Determine period times based on product.
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
        logger.debug(f" XTFD | Finished Periods: {finished_periods}")

        if not finished_periods:
            logger.debug(" XTFD | No finished periods. Returning False.")
            return False

        # Determine the extension index (ext_index) based on direction.
        ext_index = None
        if self.direction == "long":
            for i, period in enumerate(finished_periods):
                p_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                if p_high is None:
                    logger.debug(f" XTFD | Period {period} missing HIGH. Skipping.")
                    continue
                if round(p_high, 2) > self.ib_high:
                    ext_index = i
                    logger.debug(f" XTFD | Found IBH extension at period {period}, index={i}, p_high={p_high}.")
                    break
            if ext_index is None:
                logger.debug(" XTFD | No IBH extension found. Returning False.")
                return False

            # Check VWAP touches for LONG.
            for i in range(ext_index + 1, len(finished_periods)):
                period = finished_periods[i]
                p_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                if p_low is None:
                    logger.debug(f" XTFD | Period {period} missing LOW. Skipping.")
                    continue
                p_low = round(p_low, 2)
                vwap_var = f"{self.product_name}_ETH_VWAP_{period}"
                period_vwap = self.variables.get(vwap_var)
                if period_vwap is None:
                    logger.debug(f" XTFD | Period {period} missing VWAP. Skipping.")
                    continue
                period_vwap = round(period_vwap, 2)
                if p_low <= period_vwap:
                    logger.debug(f" XTFD | Period {period} low({p_low}) <= VWAP({period_vwap}). VWAP touch detected.")
                    return False
            return True

        elif self.direction == "short":
            for i, period in enumerate(finished_periods):
                p_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                if p_low is None:
                    logger.debug(f" XTFD | Period {period} missing LOW. Skipping.")
                    continue
                if round(p_low, 2) < self.ib_low:
                    ext_index = i
                    logger.debug(f" XTFD | Found IBL extension at period {period}, index={i}, p_low={p_low}.")
                    break
            if ext_index is None:
                logger.debug(" XTFD | No IBL extension found. Returning False.")
                return False

            # Check VWAP touches for SHORT.
            for i in range(ext_index + 1, len(finished_periods)):
                period = finished_periods[i]
                p_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                if p_high is None:
                    logger.debug(f" XTFD | Period {period} missing HIGH. Skipping.")
                    continue
                p_high = round(p_high, 2)
                vwap_var = f"{self.product_name}_ETH_VWAP_{period}"
                period_vwap = self.variables.get(vwap_var)
                if period_vwap is None:
                    logger.debug(f" XTFD | Period {period} missing VWAP. Skipping.")
                    continue
                period_vwap = round(period_vwap, 2)
                if p_high >= period_vwap:
                    logger.debug(f" XTFD | Period {period} high({p_high}) >= VWAP({period_vwap}). VWAP touch detected.")
                    return False
            return True

        else:
            logger.debug(" XTFD | Invalid direction specified.")
            return False
    
    def one_time_framing(self):
        """
        Determines one-time framing conditions based on the last two finished periods.
        Extensive logging is provided to trace computation values.
        
        Returns:
            True if one-time framing condition is met, False otherwise.
        """
        # Define period times based on the product.
        if self.product_name == "CL":
            period_times = {
                'A': time(9, 0), 'B': time(9, 30), 'C': time(10, 0),
                'D': time(10, 30), 'E': time(11, 0), 'F': time(11, 30),
                'G': time(12, 0), 'H': time(12, 30), 'I': time(13, 0),
                'J': time(13, 30), 'K': time(14, 0),
            }
            logger.debug("one_time_framing | Using CL period times.")
        else:
            period_times = {
                'A': time(9, 30), 'B': time(10, 0), 'C': time(10, 30),
                'D': time(11, 0), 'E': time(11, 30), 'F': time(12, 0),
                'G': time(12, 30), 'H': time(13, 0), 'I': time(13, 30),
                'J': time(14, 0), 'K': time(14, 30), 'L': time(15, 0),
                'M': time(15, 30),
            }
            logger.debug("one_time_framing | Using non-CL period times.")
        
        # Get the current time based on the established timezone.
        now = datetime.now(self.est).time()
        logger.debug(f"one_time_framing | Current time: {now}")
        
        # Sort periods and filter out the finished ones.
        sorted_periods = sorted(period_times.items(), key=lambda x: x[1])
        finished_periods = [p for p, t in sorted_periods if t <= now]
        logger.debug(f"one_time_framing | Finished periods: {finished_periods}")
        
        if len(finished_periods) < 2:
            logger.debug("one_time_framing | Not enough finished periods. Returning False.")
            return False
        
        # Consider the last two finished periods.
        last_two = finished_periods[-2:]
        period1, period2 = last_two[0], last_two[1]
        logger.debug(f"one_time_framing | Last two periods selected: {period1}, {period2}")
        
        # Retrieve high and low values for both periods.
        p1_high = self.variables.get(f"{self.product_name}_{period1}_HIGH")
        p1_low = self.variables.get(f"{self.product_name}_{period1}_LOW")
        p2_high = self.variables.get(f"{self.product_name}_{period2}_HIGH")
        p2_low = self.variables.get(f"{self.product_name}_{period2}_LOW")
        logger.debug(f"one_time_framing | Raw values: {period1} HIGH={p1_high}, LOW={p1_low}; {period2} HIGH={p2_high}, LOW={p2_low}")
        
        # If any value is missing, the check fails.
        if None in (p1_high, p1_low, p2_high, p2_low):
            logger.debug("one_time_framing | One or more period values missing. Returning False.")
            return False
        
        # Round the values to two decimals.
        p1_high = round(p1_high, 2)
        p1_low = round(p1_low, 2)
        p2_high = round(p2_high, 2)
        p2_low = round(p2_low, 2)
        logger.debug(f"one_time_framing | Rounded values: {period1} HIGH={p1_high}, LOW={p1_low}; {period2} HIGH={p2_high}, LOW={p2_low}")
        
        # Get the current day's high and low.
        current_high = self.day_high
        current_low = self.day_low
        logger.debug(f"one_time_framing | Current day's HIGH={current_high}, LOW={current_low}")
        
        # Evaluate the one-time framing conditions based on direction.
        if self.direction == "long":
            logger.debug("one_time_framing | Evaluating conditions for LONG direction.")
            if p2_high > p1_high and p2_low > p1_low:
                logger.debug(f"one_time_framing | {period2} values are greater than {period1} values.")
                if current_high > p2_high and current_low > p2_low:
                    logger.debug("one_time_framing | Current day values exceed period2 values. Returning True.")
                    return True
                else:
                    logger.debug("one_time_framing | Current day values do not exceed period2 values. Returning False.")
                    return False
            else:
                logger.debug("one_time_framing | Condition failed: period2 values are not both greater than period1 values for LONG. Returning False.")
                return False

        elif self.direction == "short":
            logger.debug("one_time_framing | Evaluating conditions for SHORT direction.")
            if p2_high < p1_high and p2_low < p1_low:
                logger.debug(f"one_time_framing | {period2} values are lower than {period1} values.")
                if current_high < p2_high and current_low < p2_low:
                    logger.debug("one_time_framing | Current day values are lower than period2 values. Returning True.")
                    return True
                else:
                    logger.debug("one_time_framing | Current day values are not lower than period2 values. Returning False.")
                    return False
            else:
                logger.debug("one_time_framing | Condition failed: period2 values are not both lower than period1 values for SHORT. Returning False.")
                return False
        else:
            logger.debug("one_time_framing | Invalid direction specified. Returning False.")
            return False
         
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        self.used_range = max(self.overnight_high, self.day_high) - min(self.overnight_low, self.day_low)
        self.remaining_range = self.exp_rng - self.used_range
        if self.direction == "short":
            self.no_skew = self.day_vpoc < self.ib_high - 0.35 * (self.ib_high - self.ib_low)
        elif self.direction == "long":
            self.no_skew = self.day_vpoc > self.ib_low + 0.35 * (self.ib_high - self.ib_low)
        logic = (
            (self.ib_high - self.ib_low) / self.ib_atr >= 1.00 # Wider Than Avg IB 
            and self.remaining_range >= (0.75 * self.exp_rng) # Used 75% or More of EXP Range
            and self.ib_low < self.day_vpoc < self.ib_low # Dvpoc Must be Inside IB Range
            and self.no_skew # No Skew to Profile in Direction of IB Extension
            and (abs(self.cpl - self.day_vpoc)) > 0.35 * (self.day_high - self.day_low) # At least 35% of RTH Range between Price and Dvpoc
            )    
        logger.debug(f" XTFD | input | Product: {self.product_name} | LOGIC: {logic}")
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
        
        if self.day_high > self.ib_high and self.day_low < self.ib_low:
            if self.cpl < self.ib_low:
                self.direction = "long" 
            elif self.cpl > self.ib_high:
                self.direction = "short"   
            else:
                return False # In Middle Of IB Range While Neutral
        else:
            if self.day_low < self.ib_low:
                self.direction = "long"
            elif self.day_high > self.ib_high:
                self.direction = "short"
            else:
                return False # No IB Extension
        
        # Driving Input
        if self.time_window() and self.input():
            
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)   
                logger.debug(f" XTFD | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                if self.direction != last_alert: 
                    logger.info(f" XTFD | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Critical Criteria
                    self.c_expected_range = "x"
                    self.c_no_skew = "x"
                    self.c_wide_ib = "x"
                    self.c_divergence = "x"
                    # Logic For one Not time framing (past 3)
                    if not self.one_time_framing():
                        self.c_not_otf = "x"
                    else:
                        self.c_not_otf = "  "
                    # Logic for No Slope to VWAP
                    if self.direction == "short": 
                        if self.vwap_slope > -0.03:
                            self.c_vwap_slope = "x" 
                        else:
                            self.c_vwap_slope = "  "
                    elif self.direction == "long":
                        if self.vwap_slope < 0.03:
                            self.c_vwap_slope = "x" 
                        else:
                            self.c_vwap_slope = "  "                     
                    # Logic for VWAP Touch after IB Extension
                    if not self.vwap_touch():
                        self.c_touch_vwap = "x"
                    else:
                        self.c_touch_vwap = "  "
                    # Logic for is prior session was a directional day
                    if self.prior_day() == "Directional":
                        self.c_directional = "x"
                    else:
                        self.c_directional = "  "  
                    # Logic for Within 1SD of VWAP
                    if self.direction == "short": 
                        if self.cpl < self.top_one_eth_vwap:
                            self.c_osd = "x" 
                        else:
                            self.c_osd = "  "
                    elif self.direction == "long":
                        if self.cpl > self.bottom_one_eth_vwap:
                            self.c_osd = "x" 
                        else:
                            self.c_osd = "  "
                    # Logic for Non Directional Open
                    if self.open_type() == "OAIR":
                        self.c_non_dir_open = "x"
                    else:
                        self.c_non_dir_open = "  "
                    # Logic For 1.5x IB Stat Complete
                    if self.direction == "short":
                        if self.day_low <= self.ib_low - 0.5 * (self.ib_high - self.ib_low):
                            self.c_ib_ext_stat = "x"
                        else:
                            self.c_ib_ext_stat = "  "
                    elif self.direction == "long":
                        if self.day_high >= self.ib_high + 0.5 * (self.ib_high - self.ib_low) : 
                            self.c_ib_ext_stat = "x"    
                        else:
                            self.c_ib_ext_stat = "  "                                  
                    # Logic for Score 
                    self.score = sum(1 for condition in [self.c_expected_range, self.c_no_skew, self.c_wide_ib, self.c_divergence, self.c_not_otf, self.c_vwap_slope, self.c_touch_vwap, self.c_directional, self.c_osd, self.c_non_dir_open, self.c_ib_ext_stat] if condition == "x")   
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" XTFD | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" XTFD | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.debug(f" XTFD | check | Product: {self.product_name} | Note: Condition Not Met")
# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):

        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        direction_settings = {
            "long": {
                "dir_indicator": "^",
                "destination": "IBL",
            },
            "short": {
                "dir_indicator": "v",
                "destination": "IBH",
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

        # Title Construction with Emojis
        title = f"**{self.product_name} - Playbook Alert** - **XTFD {settings['dir_indicator']}**"
    
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
            f"• [{self.c_divergence}] Price to Value Divergence \n"
            f"• [{self.c_non_dir_open}] Non-Directional Open{colon} {ot} \n"
            f"• [{self.c_not_otf}] Rotational Day (Not One-Time Framing) \n"
            f"• [{self.c_expected_range}] At Least 75% of Expected Range Used \n"
            f"• [{self.c_wide_ib}] IB is Average to Wide: ({(self.ib_high - self.ib_low / self.ib_atr)*100}%) \n"
            f"• [{self.c_no_skew}] No Skew to Profile toward {settings['destination']} Extreme \n"
            f"• [{self.c_directional}] Prior Session was Directional \n"
            f"• [{self.c_vwap_slope}] No Slope to VWAP"
            f"• [{self.c_ib_ext_stat}] 1.5x {settings['destination']} Stat Complete \n"
            f"• [{self.c_touch_vwap}] Touched VWAP After {settings['destination']} Extension.\n"
            f"• [{self.c_osd}] Within 1 Standard Deviation of VWAP"
            f"• [{self.c_directional}] Prior Session was Directional"
        )
        embed.add_embed_field(name="\u200b", value=criteria, inline=False)

        # Playbook Score
        embed.add_embed_field(name="**Playbook Score**", value=f"_{self.score} / 11_", inline=False)
        
        # Alert Time and Price Context
        alert_time_text = f"**Alert Time / Price**: _{alert_time_formatted} EST | {self.cpl}_"
        embed.add_embed_field(name="\u200b", value=alert_time_text, inline=False)

        return embed 
    
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"XTFD | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
        alert_details = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'product': self.product_name,
            'playbook': '#XTFD',
            'direction': self.direction,
            'alert_price': self.cpl,
            'score': self.score,
            'target': self.day_vpoc,
        }
        log_alert_async(alert_details)