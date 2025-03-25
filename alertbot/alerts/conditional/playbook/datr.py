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
        self.prior_close = self.safe_round(variables.get(f'{self.product_name}_PRIOR_CLOSE'))
        self.day_open = self.safe_round(variables.get(f'{self.product_name}_DAY_OPEN'))
        self.prior_high = self.safe_round(variables.get(f'{self.product_name}_PRIOR_HIGH'))
        self.prior_low = self.safe_round(variables.get(f'{self.product_name}_PRIOR_LOW'))
        self.prior_ibh = self.safe_round(variables.get(f'{self.product_name}_PRIOR_IB_HIGH'))
        self.prior_ibl = self.safe_round(variables.get(f'{self.product_name}_PRIOR_IB_LOW'))
        self.total_ovn_delta = self.safe_round(variables.get(f'{self.product_name}_TOTAL_OVN_DELTA'))
        self.total_rth_delta = self.safe_round(variables.get(f'{self.product_name}_TOTAL_RTH_DELTA'))
        self.prior_vpoc = self.safe_round(variables.get(f'{self.product_name}_PRIOR_VPOC'))  
        self.eth_vwap = variables.get(f'{self.product_name}_ETH_VWAP')       
        self.cpl = self.safe_round(variables.get(f'{self.product_name}_CPL'))
        self.es_impvol = config.es_impvol
        self.nq_impvol = config.nq_impvol
        self.rty_impvol = config.rty_impvol
        self.cl_impvol = config.cl_impvol 
        self.delta = self.total_delta()
        self.exp_rng = self.exp_range()
        self.prior_day_type = self.prior_day()
        self.prior_mid = ((self.prior_high + self.prior_low) / 2)
    def safe_round(self, value, digits=2):
        if value is None:
            logger.error(f"DATR | safe_round | Product: {self.product_name} | Missing value for rounding; defaulting to 0.")
            return 0
        try:
            return round(value, digits)
        except Exception as e:
            logger.error(f"DATR | safe_round | Product: {self.product_name} | Error rounding value {value}: {e}")
            return 0
# ---------------------------------- Specific Calculations ------------------------------------ #   
    def exp_range(self):
        if not self.prior_close:
            logger.error(f" DATR | exp_range | Product: {self.product_name} | Note: No Close Found")
            raise ValueError(f" DATR | exp_range | Product: {self.product_name} | Note: Need Close For Calculation!")
        impvol = {
            'ES': self.es_impvol,
            'NQ': self.nq_impvol,
            'RTY': self.rty_impvol,
            'CL': self.cl_impvol
        }.get(self.product_name)
        if impvol is None:
            raise ValueError(f" DATR | exp_range | Product: {self.product_name} | Note: Unknown Product")
        exp_range = self.safe_round(((self.prior_close * (impvol / 100)) * math.sqrt(1/252)))
        exp_hi = self.safe_round(self.prior_close + exp_range)
        exp_lo = self.safe_round(self.prior_close - exp_range)
        logger.debug(f" DATR | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range} | EXP_HI: {exp_hi} | EXP_LO: {exp_lo}")
        return exp_range, exp_hi, exp_lo
    def total_delta(self):      
        total_delta = self.total_ovn_delta + self.total_rth_delta
        logger.debug(f" DATR | total_delta | Product: {self.product_name} | TOTAL_DELTA: {total_delta}")
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
        logger.debug(f" DATR | prior_day | Product: {self.product_name} | Prior Day: {day_type}")
        return day_type
# ---------------------------------- Driving Input Logic ------------------------------------ #   
    def input(self):
        def log_condition(condition, description):
            logger.debug(f"DATR | input | Product: {self.product_name} | Direction: {self.direction} | {description} --> {condition}")
            return condition
        tolerance = self.exp_rng * 0.15
        prior_mid = (self.prior_high + self.prior_low) / 2
        logic = False
        crit2 = None
        crit3 = None
        crit1 = log_condition((self.prior_high - tolerance) > self.day_open > (self.prior_low + tolerance), f"CRITICAL1: (self.prior_high({self.prior_high}) - tolerance({tolerance})) > self.day_open({self.day_open}) > (self.prior_low({self.prior_low}) + tolerance({tolerance}))")
        if crit1:
            if self.direction == 'Higher':
                crit2 = log_condition(self.cpl > prior_mid, f"CRITICAL2: self.cpl({self.cpl}) > prior_mid({self.prior_mid})")
                crit3 = log_condition(self.prior_vpoc > ((self.prior_high + prior_mid) / 2), f"CRITICAL3: self.prior_vpoc({self.prior_vpoc}) > ((prior_high({self.prior_high}) + prior_mid({self.prior_mid})) / 2)")
                logic = crit2 and crit3
            elif self.direction == 'Lower':
                crit2 = log_condition(self.cpl < prior_mid, f"CRITICAL2: self.cpl({self.cpl}) < prior_mid({self.prior_mid})")
                crit3 = log_condition(self.prior_vpoc < ((self.prior_low + prior_mid) / 2), f"CRITICAL3: self.prior_vpoc({self.prior_vpoc}) < ((prior_low({self.prior_low}) + prior_mid({self.prior_mid})) / 2)")
                logic = crit2 and crit3
        logger.debug(f"DATR | input | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {logic} | CRITICAL1: {crit1} | CRITICAL2: {crit2} | CRITICAL3: {crit3}")
        return logic
# ---------------------------------- Opportunity Window ------------------------------------ #   
    def time_window(self):
        self.current_datetime = datetime.now(self.est)
        self.current_time = self.current_datetime.time()
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
        if start_time <= self.current_time <= end_time:
            logger.debug(f" DATR | time_window | Product: {self.product_name} | Within Window: {self.current_time}.")
            return True
        else:
            logger.debug(f" DATR | time_window | Product: {self.product_name} | Outside Window {self.current_time}.")
            return False
# ---------------------------------- Calculate Criteria ------------------------------------ #      
    def check(self):
        self.direction = None
        if self.prior_day_type == 'Trend ^':
            self.direction = 'Higher'
        elif self.prior_day_type == 'Trend v':
            self.direction = 'Lower'
        self.color = "red" if self.direction == "Lower" else "green"
        if self.time_window() and self.input():
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
                "target": f"{self.prior_high}",
                "destination": "High",
                "pv_indicator": "^",
                "risk": "above",
                "trend": "higher",
                "large": "large_",
                "c_hwb": "Above",
                "c_prior_vpoc": "above",
                "c_vwap": "Above",
            },
            "Lower": {
                "target": f"{self.prior_low}",
                "destination": "Low",
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
            raise ValueError(f" DATR | discord_message | Product: {self.product_name} | Note: Invalid direction '{self.direction}'")
        title = f":large_{pro_color}_square: **{self.product_name} - Playbook Alert** :{settings['large']}{self.color}_circle: **DATR {settings['pv_indicator']}**"
        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: _{settings['risk']} (Prior Session {settings['destination']})_\n"
                f"**Risk**: _Wrong if price accepts {settings['risk']} HWB of prior session_\n"
                f"**Driving Input**: _Prior Day was a trend {settings['trend']}_\n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp() 
        embed.add_embed_field(name="**Criteria**", value="\u200b", inline=False)
        criteria = (
            f"• **[{self.c_trend}]** Prior Day was Trend Day\n"
            f"• **[{self.c_open}]** Open Inside of Prior Range\n"
            f"• **[{self.c_hwb}]** {settings['c_hwb']} HWB of Prior Day Range\n"
            f"• **[{self.c_prior_vpoc}]** Prior Day VPOC {settings['c_prior_vpoc']} HWB of Prior Day Range\n"
            f"• **[{self.c_vwap}]** {settings['c_vwap']} ETH VWAP\n"
            f"• **[{self.c_orderflow}]** Supportive Cumulative Delta (*_{self.delta}_*)\n"
        )
        embed.add_embed_field(name="\u200b", value=criteria, inline=False)
        embed.add_embed_field(name="**Playbook Score**", value=f"_{self.score} / 6_", inline=False)
        embed.add_embed_field(name="**Alert Time / Price**", value=f"_{alert_time_formatted}_ EST | {self.cpl}_", inline=False)
        return embed   
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"DATR | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
                