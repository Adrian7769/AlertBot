import logging
import math
import threading
from datetime import datetime
from alertbot.utils import config
from discord_webhook import DiscordEmbed
from alertbot.alerts.base import Base
from datetime import datetime, time
from zoneinfo import ZoneInfo
from alertbot.source.alert_logger import log_alert_async
from collections import defaultdict

logger = logging.getLogger(__name__)

last_alerts = {}
last_alerts_lock = threading.Lock()

class TRCT(Base):
    def __init__(self, product_name, variables):    
        super().__init__(product_name=product_name, variables=variables)
        
        # Variables (Round All Variables)
        self.day_high = round(variables.get(f'{product_name}_DAY_HIGH'), 2)
        self.day_low = round(variables.get(f'{product_name}_DAY_LOW'), 2)           
        self.prior_high = round(self.variables.get(f'{self.product_name}_PRIOR_HIGH'), 2)
        self.prior_low = round(self.variables.get(f'{self.product_name}_PRIOR_LOW'), 2)
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
        self.prior_ibh = round(self.variables.get(f'{self.product_name}_PRIOR_IB_HIGH'), 2)
        self.prior_ibl = round(self.variables.get(f'{self.product_name}_PRIOR_IB_LOW'), 2)        
        self.eth_top_2 = round(variables.get(f'{product_name}_ETH_TOP_2'), 2)
        self.eth_top_1 = round(variables.get(f'{product_name}_ETH_TOP_1'), 2)
        self.eth_bottom_1 = round(variables.get(f'{product_name}_ETH_BOTTOM_1'), 2)
        self.eth_bottom_2 =  round(variables.get(f'{product_name}_ETH_BOTTOM_2'), 2)    
        self.day_vpoc = round(variables.get(f'{product_name}_DAY_VPOC'), 2)  
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        self.exp_rng = self.exp_range() 

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
        logger.debug(f" TRCT | prior_day | Prior Day Type: {day_type}")
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
        exp_range = round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)), 2)
        logger.debug(f" TRCT | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range}")
        return exp_range 
    
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def trend_day(self):
        """
        For a 'trend day':
        - For long: 1.) Day high must exceed IB_high + 0.5 * IB_range
                    2.) Acceptance Outside of IB Range. Defined as 
                    No New Period Lows Made Inside of IB Range. 
                    Ex.) So If "D" Period Low is at 1800 and It is within the IB range, then The Following
                    Period "E" Low cannot be below 1800 or that would make a New Low INSIDE The IB Range. We must check this criteria
                    for all periods after A Period and up to the current Period. It is important to clarify that we only
                    care about New Lows made INSIDE of IB range, not outside.
                    3.) We must also check that Day_VPOC > Than IBH.
                    4.) Prior Session Must Be A Rotational Day. So def prior_day must return a normal variation, normal day, neutral center, or non-trend.
                    5.) self.cpl must be > than The current session MID ((day_high + day_low) / 2)
                    6.) We cannot touch RTH or ETH VWAP after IB Extension. So this can perhaps be defined as: If Day High > IBH then 
                    no period Low AFTER the period that extended IB can be less than or equal to ETH VWAP or RTH VWAP. 
                    Ex.) if C period extended IBH to the upside, then D period and all the way to the current period cannot be less than or equal to RTH or ETH VWAP.
                    7.) Value must be following price, this is defined as: RTH VPOC must be within the range of the current or past period. So if the range of 
                    the current period is 1850 to 1750 and the range from the past period is from 1830 to 1720 the RTH VPOC must be greater than prior period low but less than 
                    current period high. 
        - For short: 1.) Day low must be below IB_low - 0.5 * IB_range
                     2.) Acceptance Outside of IB Range. Defined as 
                     No New Period Highs Made Inside of IB Range. 
                     Ex.) So If "D" Period High is at 1800 and It is within the IB range, then The Following
                     Period "E" High cannot be above 1800 or that would make a New High INSIDE The IB Range. We must check this criteria
                     for all periods after A Period and up to the current Period. It is important to clarify that we only
                     care about New Highs made INSIDE of IB range, not outside.
                     3.) We must also check that Day_VPOC < Than IBL.
                     4.) Prior Session Must Be A Rotational Day. So def prior_day must return a normal variation, normal day, neutral center, or non-trend.
                     5.) self.cpl must be < than The current session MID ((day_high + day_low) / 2)
                     6.) We cannot touch RTH or ETH VWAP after IB Extension. So this can perhaps be defined as: If Day Low < IBL then 
                     no period High AFTER the period that extended IB can be Greater than or equal to ETH VWAP or RTH VWAP. 
                     Ex.) if C period extended IBL to the downside, then D period (D is the Next period after C) and all the way to the current period cannot be greater than or equal to RTH or ETH VWAP.
                     7.) Value must be following price, this is defined as: RTH VPOC must be within the range of the current or past period. So if the range of 
                     the current period is 1850 to 1750 and the range from the past period is from 1870 to 1770 the RTH VPOC must be less than prior period high but greater than 
                     current period low.
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

        # --- LONG DIRECTION ---
        if self.direction == "long":
            # 1) Day high must exceed IB_high + 0.5 * IB_range.
            condition1 = self.day_high > self.ib_high + 0.5 * ib_range

            # 2) Acceptance Outside IB Range: no new period LOW (inside IB range) that is lower than a previous period low.
            acceptance = True
            prior_low = None
            for period in finished_periods:
                var_name = f"{self.product_name}_{period}_LOW"
                period_low = self.variables.get(var_name)
                if period_low is None:
                    continue
                period_low = round(period_low, 2)
                if prior_low is not None:
                    # If a new period's low is lower than the last accepted low and is inside IB range, acceptance fails.
                    if period_low < prior_low and self.ib_low <= period_low <= self.ib_high:
                        acceptance = False
                        break
                # Only update prior_low if the period low is inside IB range.
                if self.ib_low <= period_low <= self.ib_high:
                    prior_low = period_low

            # 3) Day_VPOC must be greater than IB_high.
            condition3 = self.p_vpoc > self.ib_high

            # 4) Prior session must be rotational.
            condition4 = self.prior_day() in ["Rotational"]

            # 5) self.cpl must be greater than current session MID.
            current_mid = (self.day_high + self.day_low) / 2
            condition5 = self.cpl > current_mid

            # 6) After IB extension (first period where HIGH > IB_high), no subsequent period low can be <= ETH VWAP.
            extension_found = False
            condition6 = True
            for period in finished_periods:
                var_name_high = f"{self.product_name}_{period}_HIGH"
                period_high = self.variables.get(var_name_high)
                if period_high is None:
                    continue
                period_high = round(period_high, 2)
                if not extension_found and period_high > self.ib_high:
                    extension_found = True
                    continue  # Only consider periods after extension.
                if extension_found:
                    var_name_low = f"{self.product_name}_{period}_LOW"
                    period_low = self.variables.get(var_name_low)
                    if period_low is None:
                        continue
                    period_low = round(period_low, 2)
                    # If any subsequent period low is <= ETH VWAP (or RTH VWAP if defined similarly), condition fails.
                    if period_low <= self.eth_vwap:
                        condition6 = False
                        break
            # 7) Value must be following price: RTH VPOC must be within the range of the last finished period or the current period.
            if len(finished_periods) >= 2:
                prior_period = finished_periods[-2]
                current_period = finished_periods[-1]
                prior_low = self.variables.get(f"{self.product_name}_{prior_period}_LOW")
                current_high = self.variables.get(f"{self.product_name}_{current_period}_HIGH")
                if prior_low is not None and current_high is not None:
                    prior_low = round(prior_low, 2)
                    current_high = round(current_high, 2)
                    condition7 = (prior_low < self.day_vpoc < current_high)
                else:
                    condition7 = False
            else:
                condition7 = False
                
            return (condition1 and acceptance and condition3 and condition4 and condition5 and condition6 and condition7)

        # --- SHORT DIRECTION ---
        elif self.direction == "short":
            # 1) Day low must be below IB_low - 0.5 * IB_range.
            condition1 = self.day_low < self.ib_low - 0.5 * ib_range
            # 2) Acceptance Outside IB Range: no new period HIGH (inside IB range) that is higher than a previous period high.
            acceptance = True
            prior_high = None
            for period in finished_periods:
                var_name = f"{self.product_name}_{period}_HIGH"
                period_high = self.variables.get(var_name)
                if period_high is None:
                    continue
                period_high = round(period_high, 2)
                if prior_high is not None:
                    if period_high > prior_high and self.ib_low <= period_high <= self.ib_high:
                        acceptance = False
                        break
                if self.ib_low <= period_high <= self.ib_high:
                    prior_high = period_high
            # 3) Day_VPOC must be less than IB_low.
            condition3 = self.p_vpoc < self.ib_low
            # 4) Prior session must be rotational.
            condition4 = self.prior_day() in ["Rotational"]
            # 5) self.cpl must be less than current session MID.
            current_mid = (self.day_high + self.day_low) / 2
            condition5 = self.cpl < current_mid
            # 6) After IB extension (first period where LOW < IB_low), no subsequent period high can be >= ETH VWAP.
            extension_found = False
            condition6 = True
            for period in finished_periods:
                var_name_low = f"{self.product_name}_{period}_LOW"
                period_low = self.variables.get(var_name_low)
                if period_low is None:
                    continue
                period_low = round(period_low, 2)
                if not extension_found and period_low < self.ib_low:
                    extension_found = True
                    continue
                if extension_found:
                    var_name_high = f"{self.product_name}_{period}_HIGH"
                    period_high = self.variables.get(var_name_high)
                    if period_high is None:
                        continue
                    period_high = round(period_high, 2)
                    if period_high >= self.eth_vwap:
                        condition6 = False
                        break
            # 7) Value must be following price: RTH VPOC must be within the range of the last finished period or current period.
            if len(finished_periods) >= 2:
                prior_period = finished_periods[-2]
                current_period = finished_periods[-1]
                prior_high = self.variables.get(f"{self.product_name}_{prior_period}_HIGH")
                current_low = self.variables.get(f"{self.product_name}_{current_period}_LOW")
                if prior_high is not None and current_low is not None:
                    prior_high = round(prior_high, 2)
                    current_low = round(current_low, 2)
                    condition7 = (current_low < self.day_vpoc < prior_high)
                else:
                    condition7 = False
            else:
                condition7 = False
            return (condition1 and acceptance and condition3 and condition4 and condition5 and condition6 and condition7)
        else:
            return False
    def float_range(start, stop, step):
        epsilon = 1e-9
        num_steps = int(math.floor((stop - start) / step + 0.5))
        for i in range(num_steps + 1):
            val = start + i * step
            if val > stop + epsilon:
                break
            yield round(val, 10)
    def single_prints(self, finished_periods):
        if len(finished_periods) < 3:
            return False
        first_subperiod = finished_periods[0]
        last_subperiod = finished_periods[-1]
        middle_periods = finished_periods[1:-1]
        tick_size_map = {
            "ES": 0.25,
            "NQ": 0.25,
            "RTY": 0.10,
            "CL": 0.01
        }
        tick_size = tick_size_map.get(self.product_name, 1.0)
        price_map = defaultdict(set)
        min_price = float('inf')
        max_price = float('-inf')
        for period in finished_periods:
            p_low = self.variables.get(f"{self.product_name}_{period}_LOW")
            p_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
            if p_low is None or p_high is None:
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
            return False
        lowest_overlapped_price = None
        for price in self.float_range(min_price, max_price, tick_size):
            if len(price_map[price]) >= 2:
                lowest_overlapped_price = price
                break
        highest_overlapped_price = None
        reversed_prices = list(self.float_range(min_price, max_price, tick_size))
        reversed_prices.reverse()
        for price in reversed_prices:
            if len(price_map[price]) >= 2:
                highest_overlapped_price = price
                break
        if (lowest_overlapped_price is None or
            highest_overlapped_price is None or
            lowest_overlapped_price >= highest_overlapped_price):
            return False
        for price in self.float_range(lowest_overlapped_price, highest_overlapped_price, tick_size):
            if len(price_map[price]) == 1:
                (unique_period,) = price_map[price]
                if unique_period in middle_periods:
                    return True
        return False
    def strong_trending(self):
        """
        For a 'strong trending':
        - For long: 1.) Acceptance inside "Trending Channel". Defined as no new period lows created while below self.eth_top_1. 
                        We only consider the period lows AFTER IBH EXTENSION. IBH extension is defined as the first period high that is greater than IB_High.
                        A "new period low" is defined by a period low being lower than the previous periods low. So if C Period has a low at 1850 and D period has a
                        low at 1830 AND 1850 lies below self.eth_top_1 then the condition would return false, because we made a NEW low outside of the trending channel.
                        Please note that we can make lows as long as they are within the trending channel!
                    EX.) Lets say that C Period is the first period to "Extend" The Initial Balance High. 
                         Then We only consider Periods After C period, for the Trending Channel Criteria.
                    2.) Prior Session Must Be A Rotational Day. So def prior_day must return "Rotational", anything else and the condition must return false.
                    3.) We cannot touch RTH or ETH VWAP after IB Extension. So this can perhaps be defined as: If Day High > IBH then 
                    no period Low AFTER the period that extended IB can be less than or equal to ETH VWAP or RTH VWAP.
                    Ex.) if C period extended IBH to the upside, then D period and all the way to the current period cannot be less than or equal to RTH or ETH VWAP.
                    4.) self.cpl must be > than The current session MID ((day_high + day_low) / 2)
                    5.) The Auction must be "One-time-Framing" for at least the prior 3 periods AFTER the period that extends the Initial Balance High.
                    One-Time-Framing is a pattern of Consecutive Higher Highs and consecutive Higher Lows for each period.
                    Ex.) If C period is the period that happens to extend the initial balance high (C period high > IBH) then if D period High is > than C period High
                    and D Period Low is > than C period Low than that we would be one time framing for 1 period, every time that pattern continues with each
                    period then we would add 1. If the pattern is violated, then we go back to 0 and restart. This condition must only be true if we have "One Time Framed"
                    for at least 3 or more periods SINCE the IB Extension Period. So if D period High was the First Period High to be > than IBH then we start Counting from D Period.
                    6.) Single Prints Must Be Present In the Current Trading Session. Single prints are defined prices that only get traded by one period. So if 
                    you were to take the period ranges and represent them as blocks, the single prints in the "profile" would only have 1 block and thus be a single print. But we do not look at the
                    periods on the edges, they are not considered single prints.
        - For short: 1.) Acceptance inside "Trending Channel". Defined as no new period highs created while above self.eth_bottom_1. 
                        We only consider the period Highs AFTER IBL EXTENSION. IBL extension is defined as the first period Low that is less than IB_Low.
                        A "new period High" is defined by a period High being Higher than the previous periods High. So if C Period has a High at 1850 and D period has a
                        High at 1860 AND 1850 lies above self.eth_bottom_1 then the condition would return false, because we made a NEW High outside of the trending channel.
                        Please note that we can make highs as long as they are within the trending channel!
                    EX.) Lets say that C Period is the first period to "Extend" The Initial Balance Low. 
                         Then We only consider Periods After C period, for the Trending Channel Criteria.
                    2.) Prior Session Must Be A Rotational Day. So def prior_day must return "Rotational", anything else and the condition must return false.
                    3.) We cannot touch RTH or ETH VWAP after IB Extension. So this can perhaps be defined as: If Day Low < IBL then 
                    no period High AFTER the period that extended IB can be greater than or equal to ETH VWAP or RTH VWAP.
                    Ex.) if C period extended IBL to the downside, then D period and all the way to the current period cannot be less than or equal to RTH or ETH VWAP.
                    4.) self.cpl must be > than The current session MID ((day_high + day_low) / 2)
                    5.) The Auction must be "One-time-Framing" for at least the prior 3 periods AFTER the period that extends the Initial Balance High.
                    One-Time-Framing is a pattern of Consecutive Higher Highs and consecutive Higher Lows for each period.
                    Ex.) If C period is the period that happens to extend the initial balance high (C period high > IBH) then if D period High is > than C period High
                    and D Period Low is > than C period Low than that we would be one time framing for 1 period, every time that pattern continues with each
                    period then we would add 1. If the pattern is violated, then we go back to 0 and restart. This condition must only be true if we have "One Time Framed"
                    for at least 3 or more periods SINCE the IB Extension Period. So if D period High was the First Period High to be > than IBH then we start Counting from D Period.
                    6.) Single Prints Must Be Present In the Current Trading Session. Single prints are defined prices that only get traded by one period. So if 
                    you were to take the period ranges and represent them as blocks, the single prints in the "profile" would only have 1 block and thus be a single print. But we do not look at the
                    periods on the edges, they are not considered single prints.        
        """
        # Define period schedule based on product type.
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

        # --- Identify IBH Extension ---
        ext_found = False
        ext_index = None
        for i, period in enumerate(finished_periods):
            high_var = f"{self.product_name}_{period}_HIGH"
            period_high = self.variables.get(high_var)
            if period_high is None:
                continue
            period_high = round(period_high, 2)
            if period_high > self.ib_high:
                ext_found = True
                ext_index = i
                break

        if not ext_found:
            # If no extension has occurred, strong trending cannot be confirmed.
            return False

        # --- Condition 1: Trending Channel Acceptance ---
        trending_acceptance = True
        prior_low = None
        # Iterate through periods after IB extension.
        for i in range(ext_index, len(finished_periods)):
            period = finished_periods[i]
            low_var = f"{self.product_name}_{period}_LOW"
            period_low = self.variables.get(low_var)
            if period_low is None:
                continue
            period_low = round(period_low, 2)
            if i == ext_index:
                prior_low = period_low
                continue
            # If new period low is lower than the previous period low and the previous low is below self.eth_top_1,
            # then a new low has been created outside of the trending channel.
            if prior_low is not None and period_low < prior_low and prior_low < self.eth_top_1:
                trending_acceptance = False
                break
            # Update prior_low if the current low is within the trending channel.
            if self.ib_low <= period_low <= self.eth_top_1:
                prior_low = period_low

        # --- Condition 2: Prior Session Must Be Rotational ---
        rotational_set = {"Normal Var ^", "Normal Day ^", "Neutral Center", "Non-Trend"}
        condition2 = self.prior_day() in rotational_set

        # --- Condition 3: No VWAP Touch After Extension ---
        condition3 = True
        for i in range(ext_index + 1, len(finished_periods)):
            period = finished_periods[i]
            low_var = f"{self.product_name}_{period}_LOW"
            period_low = self.variables.get(low_var)
            if period_low is None:
                continue
            period_low = round(period_low, 2)
            if period_low <= self.eth_vwap:
                condition3 = False
                break

        # --- Condition 4: Current Price Above Session Mid ---
        current_mid = (self.day_high + self.day_low) / 2
        condition4 = self.cpl > current_mid

        # --- Condition 5: One-Time Framing Count >= 3 ---
        one_time_count = 0
        if ext_index < len(finished_periods) - 1:
            prev_period = finished_periods[ext_index]
            prev_high = self.variables.get(f"{self.product_name}_{prev_period}_HIGH")
            prev_low = self.variables.get(f"{self.product_name}_{prev_period}_LOW")
            if prev_high is not None:
                prev_high = round(prev_high, 2)
            if prev_low is not None:
                prev_low = round(prev_low, 2)
            for period in finished_periods[ext_index + 1:]:
                current_high = self.variables.get(f"{self.product_name}_{period}_HIGH")
                current_low = self.variables.get(f"{self.product_name}_{period}_LOW")
                if current_high is None or current_low is None:
                    continue
                current_high = round(current_high, 2)
                current_low = round(current_low, 2)
                if prev_high is None or prev_low is None:
                    continue
                if current_high > prev_high and current_low > prev_low:
                    one_time_count += 1
                    prev_high = current_high
                    prev_low = current_low
                else:
                    one_time_count = 0  # reset if pattern breaks
            condition5 = one_time_count >= 3
        else:
            condition5 = False

        # --- Condition 6: Single Prints Must Be Present ---
        condition6 = self.single_prints()

        # --- Combine All Conditions ---
        return (trending_acceptance and condition2 and condition3 and condition4 and condition5 and condition6)

    def input(self):
        """
        This revised input method now incorporates both trend day and strong trending checks.
        """
        ib_range = self.ib_high - self.ib_low

        # Existing direction-based base conditions.
        if self.direction == "short":
            self.atr_condition = abs(self.ib_low - self.p_vpoc) <= self.remaining_atr
            self.or_condition = self.cpl < self.orl
            base_trend_condition = self.day_low < self.ib_low - 0.5 * ib_range

            # Include your existing period high scan logic for short acceptance.
            acceptance_condition = True
            # ... (your period high scanning logic here) ...

        elif self.direction == "long":
            self.atr_condition = abs(self.ib_high - self.p_vpoc) <= self.remaining_atr
            self.or_condition = self.cpl > self.orh
            # For long, basic trend day requires the day high exceeds IBH + 0.5*(IB_range)
            base_trend_condition = self.day_high > self.ib_high + 0.5 * ib_range
            acceptance_condition = True  # further refined in check_trend_day below
        else:
            return False

        # Base logic conditions (unchanged from your code)
        base_logic = (
            self.p_low - (self.exp_rng * 0.15) <= self.day_open <= self.p_high + (self.exp_rng * 0.15)
            and self.p_low + (self.exp_rng * 0.10) <= self.cpl <= self.p_high - (self.exp_rng * 0.10)
            and self.atr_condition
            and abs(self.cpl - self.p_vpoc) > self.exp_rng * 0.1
            and self.or_condition
        )

        # Check for trend day conditions.
        self.trend_day = base_logic and self.check_trend_day()

        # Check for strong trending (singles) regardless of the trend day flag.
        self.strong_trending = self.check_strong_trending()

        # In your alert logic you might now decide:
        # - If trend_day is True, then #TRCT (Trend Day) conditions are met.
        # - If strong_trending is also True, add an extra flag or modify the alert.
        # They can both be true simultaneously.
        final_logic = self.trend_day or self.strong_trending

        logger.debug(f" TRCT | input | Product: {self.product_name} | Trend Day: {self.trend_day}, Strong Trending: {self.strong_trending}, Final Logic: {final_logic}")
        return final_logic

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
        
        # Define Direction
        if self.day_low < self.ib_low:
            self.direction = "short"
        elif self.day_high > self.ib_high:
            self.direction = "long"
        elif self.day_high > self.ib_high and self.day_low < self.ib_low:
            logger.info(f" TRCT | check | Product: {self.product_name} | Note: Neutral Behavior Detected, Returning")
            return
        else:
            logger.info(f" TRCT | check | Product: {self.product_name} | Note: No IB Extension Detected")
            return
        self.color = "red" if self.direction == "short" else "green"
        # Driving Input
        if self.time_window() and self.input():
            
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)   
                logger.debug(f" TRCT | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                
                if self.direction != last_alert: 
                    logger.info(f" TRCT | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # Logic For Trend Day
                    if self.atr_condition: 
                        self.c_within_atr = "x" 
                    else:
                        self.c_within_atr = "  "                    
                    # Logic For Strong Trending
                    if self.atr_condition: 
                        self.c_within_atr = "x" 
                    else:
                        self.c_within_atr = "  "                     
                    # Logic For Acceptance Outside Of IB
                    if self.atr_condition: 
                        self.c_within_atr = "x" 
                    else:
                        self.c_within_atr = "  "
                    # Logic For Strong Slope to VWAP
                    if self.atr_condition: 
                        self.c_within_atr = "x" 
                    else:
                        self.c_within_atr = "  "
                    # Logic For One Time Framing
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"
                    # Logic For Holding in Trending Channel
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x" 
                    # Logic For Within 1 EXP Move of 5D
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"  
                    # Logic For Value Following Price
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x" 
                    # Logic For Above / Below RTH MID
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x" 
                    # Logic For Prior Day Was Rotational
                    self.c_orderflow = "  "
                    if self.direction == "short" and self.delta < 0:
                        self.c_orderflow = "x"
                    elif self.direction == "long" and self.delta > 0:
                        self.c_orderflow = "x"                                                                      
                    # Logic for Score 
                    self.score = sum(1 for condition in [self.c_within_atr] if condition == "x")   
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f" TRCT | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f" TRCT | check | Product: {self.product_name} | Note: Alert: {self.direction} Is Same")
        else:
            logger.info(f" TRCT | check | Product: {self.product_name} | Note: Condition Not Met")
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
            raise ValueError(f" TRCT | discord_message | Note: Invalid direction '{self.direction}'")
        
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
        logger.info(f"TRCT | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
        alert_details = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'product': self.product_name,
            'playbook': '#TRCT',
            'direction': self.direction,
            'alert_price': self.cpl,
            'score': self.score,
            'target': self.prior_mid,
        }
        log_alert_async(alert_details)