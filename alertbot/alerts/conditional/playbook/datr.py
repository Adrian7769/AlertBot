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
        logger.debug(f" DATR | exp_range | Product: {self.product_name} | EXP_RNG: {exp_range}")
        return exp_range
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
        crit2 = False
        crit1 = log_condition((self.prior_high - tolerance) > self.day_open > (self.prior_low + tolerance), f"CRITICAL1: (self.prior_high({self.prior_high}) - tolerance({tolerance})) > self.day_open({self.day_open}) > (self.prior_low({self.prior_low}) + tolerance({tolerance}))")
        if crit1:
            if self.direction == 'Higher':
                crit2 = log_condition(self.cpl > prior_mid, f"CRITICAL2: self.cpl({self.cpl}) > prior_mid({self.prior_mid})")
                logic = crit2
            elif self.direction == 'Lower':
                crit2 = log_condition(self.cpl < prior_mid, f"CRITICAL2: self.cpl({self.cpl}) < prior_mid({self.prior_mid})")
                logic = crit2
        logger.debug(f"DATR | input | Product: {self.product_name} | Direction: {self.direction} | FINAL_LOGIC: {logic} | CRITICAL1: {crit1} | CRITICAL2: {crit2}")
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
        # Determine Direction with Detailed Logging
        self.direction = None
        if self.prior_day_type == 'Trend ^':
            self.direction = 'Higher'
            logger.debug(f"DATR | check | Product: {self.product_name} | DIR_LOGIC: prior_day_type({self.prior_day_type}) == 'Trend ^' -> Direction: {self.direction}")
        elif self.prior_day_type == 'Trend v':
            self.direction = 'Lower'
            logger.debug(f"DATR | check | Product: {self.product_name} | DIR_LOGIC: prior_day_type({self.prior_day_type}) == 'Trend v' -> Direction: {self.direction}")
        else:
            logger.debug(f"DATR | check | Product: {self.product_name} | Note: No Prior Trend Day; Returning.")
            return False

        self.color = "red" if self.direction == "Lower" else "green"

        # Driving Input Check with Detailed Logging
        if self.time_window() and self.input():
            with last_alerts_lock:
                last_alert = last_alerts.get(self.product_name)
                logger.debug(f"DATR | check | Product: {self.product_name} | Current Alert: {self.direction} | Last Alert: {last_alert}")
                if self.direction != last_alert:
                    logger.info(f"DATR | check | Product: {self.product_name} | Note: Condition Met")
                    
                    # CRITERIA 1: Trend Criterion (c_trend)
                    self.c_trend = "x"
                    logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_1: prior_day_type({self.prior_day_type}) in ['Trend ^','Trend v'] -> [{self.c_trend}]")
                    
                    # CRITERIA 2: Open Range Criterion (c_open)
                    if self.prior_low < self.day_open < self.prior_high:
                        self.c_open = "x"
                    else:
                        self.c_open = "  "
                    logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_2: prior_low({self.prior_low}) < day_open({self.day_open}) < prior_high({self.prior_high}) -> [{self.c_open}]")
                    
                    # CRITERIA 3: Orderflow Criterion (c_orderflow)
                    self.c_orderflow = "  "
                    if self.direction == "Lower" and self.delta < 0:
                        self.c_orderflow = "x"
                        logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: delta({self.delta}) < 0 for Lower -> [{self.c_orderflow}]")
                    elif self.direction == "Higher" and self.delta > 0:
                        self.c_orderflow = "x"
                        logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_3: delta({self.delta}) > 0 for Higher -> [{self.c_orderflow}]")
                    
                    # CRITERIA 4: VWAP Criterion (c_vwap)
                    self.c_vwap = "  "
                    if self.direction == "Lower" and self.cpl < self.eth_vwap:
                        self.c_vwap = "x"
                        logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: cpl({self.cpl}) < eth_vwap({self.eth_vwap}) for Lower -> [{self.c_vwap}]")
                    elif self.direction == "Higher" and self.cpl > self.eth_vwap:
                        self.c_vwap = "x"
                        logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_4: cpl({self.cpl}) > eth_vwap({self.eth_vwap}) for Higher -> [{self.c_vwap}]")
                    
                    # CRITERIA 5: Prior VPOC Criterion (c_prior_vpoc)
                    self.c_prior_vpoc = "  "
                    if self.direction == "Lower" and self.prior_vpoc < self.prior_mid:
                        self.c_prior_vpoc = "x"
                        logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: prior_vpoc({self.prior_vpoc}) < prior_mid({self.prior_mid}) for Lower -> [{self.c_prior_vpoc}]")
                    elif self.direction == "Higher" and self.prior_vpoc > self.prior_mid:
                        self.c_prior_vpoc = "x"
                        logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_5: prior_vpoc({self.prior_vpoc}) > prior_mid({self.prior_mid}) for Higher -> [{self.c_prior_vpoc}]")
                    
                    # CRITERIA 6: HWB Criterion (c_hwb)
                    self.c_hwb = "  "
                    if self.direction == "Lower" and self.cpl < self.prior_mid:
                        self.c_hwb = "x"
                        logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: cpl({self.cpl}) < prior_mid({self.prior_mid}) for Lower -> [{self.c_hwb}]")
                    elif self.direction == "Higher" and self.cpl > self.prior_mid:
                        self.c_hwb = "x"
                        logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | CRITERIA_6: cpl({self.cpl}) > prior_mid({self.prior_mid}) for Higher -> [{self.c_hwb}]")
                    
                    # Score Calculation Logging
                    self.score = sum(1 for condition in [self.c_trend, self.c_orderflow, self.c_open, self.c_vwap, self.c_prior_vpoc, self.c_hwb] if condition == "x")
                    logger.debug(f"DATR | check | Product: {self.product_name} | Direction: {self.direction} | SCORE: {self.score}/6")
                    
                    try:
                        last_alerts[self.product_name] = self.direction
                        self.execute()
                    except Exception as e:
                        logger.error(f"DATR | check | Product: {self.product_name} | Note: Failed to send Slack alert: {e}")
                else:
                    logger.debug(f"DATR | check | Product: {self.product_name} | Note: Alert: {self.direction} is Same")
        else:
            logger.debug(f"DATR | check | Product: {self.product_name} | Note: Condition(s) Not Met")

# ---------------------------------- Alert Preparation------------------------------------ #  
    def discord_message(self):
        alert_time_formatted = self.current_datetime.strftime('%H:%M:%S') 
        direction_settings = { 
            "Higher": {
                "target": f"{self.prior_high}",
                "destination": "High",
                "risk": "above",
                "trend": "higher",
                "c_hwb": "Above",
                "c_prior_vpoc": "above",
                "c_vwap": "Above",
                "emoji_indicator": "🔼",                
            },
            "Lower": {
                "target": f"{self.prior_low}",
                "destination": "Low",
                "risk": "below",
                "trend": "lower",
                "c_hwb": "Below",
                "c_prior_vpoc": "below",
                "c_vwap": "Below",
                "emoji_indicator": "🔽",                
            }
        }
        settings = direction_settings.get(self.direction)
        if not settings:
            raise ValueError(f" DATR | discord_message | Product: {self.product_name} | Note: Invalid direction '{self.direction}'")
        title = f"**{self.product_name} - Playbook Alert** - **DATR** {settings['emoji_indicator']}"
        embed = DiscordEmbed(
            title=title,
            description=(
                f"**Destination**: {settings['risk']} (Prior Session {settings['destination']})\n"
                f"**Risk**: Wrong if price accepts {settings['risk']} HWB of prior session\n"
                f"**Driving Input**: Prior Day was a trend {settings['trend']}\n"
            ),
            color=self.get_color()
        )
        embed.set_timestamp() 
        embed.add_embed_field(name="**Criteria**", value="", inline=False)
        criteria = (
            f"- **[{self.c_trend}]** Prior Day was Trend Day\n"
            f"- **[{self.c_open}]** Open Inside of Prior Range\n"
            f"- **[{self.c_hwb}]** {settings['c_hwb']} HWB of Prior Day Range\n"
            f"- **[{self.c_prior_vpoc}]** Prior Day VPOC {settings['c_prior_vpoc']} HWB of Prior Day Range\n"
            f"- **[{self.c_vwap}]** {settings['c_vwap']} ETH VWAP\n"
            f"- **[{self.c_orderflow}]** Supportive Cumulative Delta ({self.delta})\n"
        )
        embed.add_embed_field(name="", value=criteria, inline=False)
        embed.add_embed_field(name="**Playbook Score**", value=f"{self.score} / 6", inline=False)
        alert_time_text = f"**Alert Time / Price**: {alert_time_formatted} EST | {self.cpl}"
        embed.add_embed_field(name="", value=alert_time_text, inline=False)

        return embed   
    def execute(self):
        embed = self.discord_message()
        self.send_playbook_embed(embed, username=None, avatar_url=None)
        logger.info(f"DATR | execute | Product: {self.product_name} | Note: Alert Sent To Playbook Webhook")
                