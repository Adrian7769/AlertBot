import logging
import math
from discord_webhook import DiscordWebhook, DiscordEmbed
from alertbot.utils import config
from alertbot.alerts.base import Base
import threading
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class IB_Equity_Alert(Base):
    def __init__(self, files):
        super().__init__(files=files)
        
    # ---------------------- Specific Calculations ------------------------- #
    def ib_info(self, ib_high, ib_low, ib_atr):
        ib_range = round((ib_high - ib_low), 2)
        ib_vatr = round((ib_range / ib_atr), 2)
        if ib_vatr > 1.1:
            ib_type = "Wide IB"
        elif ib_vatr < 0.85:
            ib_type = "Narrow IB"
        elif 0.85 <= ib_vatr <= 1.1:
            ib_type = "Average IB"
        return ib_range, ib_type, round((ib_vatr*100), 2)
    def exp_range_info(self, prior_close, cpl, ovn_to_ibh, ovn_to_ibl, impvol):
        exp_range = round(((prior_close * (impvol / 100)) * math.sqrt(1 / 252)), 2)
        exp_hi = (prior_close + exp_range)
        exp_lo = (prior_close - exp_range)
        range_used = round(((ovn_to_ibh - ovn_to_ibl) / exp_range), 2)
        if abs(range_used) >= 1:
            exhausted = "Exhausted"
        elif abs(range_used) <= 0.55:
            exhausted = "Below Avg"
        else:
            exhausted = "Nominal"
        if cpl > exp_hi:
            range_up = "Exhausted"
        else:
            range_up = round(abs((exp_hi - cpl) / (exp_range * 2) * 100), 2)
        if cpl < exp_lo:
            range_down = "Exhausted"
        else:
            range_down = round(abs((exp_lo - cpl) / (exp_range * 2)* 100), 2)
        return exhausted, range_used*100, range_up, range_down, exp_range
    def gap_info(self, day_open, prior_high, prior_low, exp_range):
        gap = ""
        gap_tier = ""
        gap_size = 0
        if day_open > prior_high:
            gap_size = round((day_open - prior_high), 2)
            gap = "Gap Up"
            if exp_range == 0:
                gap_tier = "Undefined"  
            else:
                gap_ratio = round((gap_size / exp_range) , 2)
                if gap_ratio <= 0.5:
                    gap_tier = "Tier 1"
                elif gap_ratio <= 0.75:
                    gap_tier = "Tier 2"
                else:
                    gap_tier = "Tier 3"
        elif day_open < prior_low:
            gap_size = round((prior_low - day_open), 2)
            gap = "Gap Down"
            if exp_range == 0:
                gap_tier = "Undefined" 
            else:
                gap_ratio = round((gap_size / exp_range) , 2)
                if gap_ratio <= 0.5:
                    gap_tier = "Tier 1"
                elif gap_ratio <= 0.75:
                    gap_tier = "Tier 2"
                else:
                    gap_tier = "Tier 3"
        else:
            gap = "No Gap"
            gap_tier = "Tier 0"
            gap_size = 0
        return gap, gap_tier, gap_size
    def posture(self, cpl, fd_vpoc, td_vpoc, exp_range):
        threshold = round((exp_range * 0.68), 2)
        if (abs(cpl - fd_vpoc) <= threshold) and (abs(fd_vpoc - td_vpoc) <= threshold):
            posture = "PRICE=5D=20D"
        elif (cpl > fd_vpoc + threshold) and (fd_vpoc > td_vpoc + threshold):
            posture = "PRICE^5D^20D"
        elif (cpl < fd_vpoc - threshold) and (fd_vpoc < td_vpoc - threshold):
            posture = "PRICEv5Dv20D"
        elif (abs(cpl - fd_vpoc) <= threshold) and (fd_vpoc > td_vpoc + threshold):
            posture = "PRICE=5D^20D"
        elif (cpl > fd_vpoc + threshold) and (abs(fd_vpoc - td_vpoc) <= threshold):
            posture = "PRICE^5D=20D"
        elif (cpl < fd_vpoc - threshold) and (abs(fd_vpoc - td_vpoc) <= threshold):
            posture = "PRICEv5D=20D"
        elif (abs(cpl - fd_vpoc) <= threshold) and (fd_vpoc < td_vpoc - threshold):
            posture = "PRICE=5Dv20D"
        elif (cpl > fd_vpoc + threshold) and (fd_vpoc < td_vpoc - threshold):
            posture = "PRICE^5Dv20D"
        elif (cpl < fd_vpoc - threshold) and (fd_vpoc > td_vpoc + threshold):
            posture = "PRICEv5D^20D"
        else:
            posture = "Other"
        return posture
    def open_type(self, a_high, a_low, b_high, b_low, day_open, orh, orl, prior_high, prior_low, day_high, day_low):
        a_period_mid = round(((a_high + a_low) / 2), 2)
        current_sub_low = min(a_low, b_low)
        current_sub_high = max(a_high, b_high)
        overlap = max(0, min(current_sub_high, prior_high) - max(current_sub_low, prior_low))
        total_range = day_high - day_low
        if day_open == a_high and (b_high < a_period_mid):
            open_type = "OD v"
        elif day_open == a_low and (b_low > a_period_mid):
            open_type = "OD ^"
        elif (day_open > a_period_mid) and (b_high < a_period_mid):
            open_type = "OTD v"
        elif (day_open < a_period_mid) and (b_low > a_period_mid):
            open_type = "OTD ^"
        elif (day_open > a_period_mid) and (b_low > a_period_mid) and (b_high > orh):
            open_type = "ORR ^"
        elif (day_open < a_period_mid) and (b_high < a_period_mid) and (b_low < orl):
            open_type = "ORR v"
        elif overlap >= 0.5 * total_range:
            open_type = "OAIR"
        elif (overlap < 0.5 * total_range) and (day_open >= prior_high):
            open_type = "OAOR ^"
        elif (overlap < 0.5 * total_range) and (day_open <= prior_low):
            open_type = "OAOR v"
        else:
            open_type = "Other"
        return open_type
    # ---------------------- Alert Preparation ------------------------- #
    def send_alert(self):
        threads = []
        for product_name in ['ES', 'NQ', 'RTY']:
            thread = threading.Thread(target=self.process_product, args=(product_name,))
            thread.start()
            threads.append(thread)
            time.sleep(1)

        for thread in threads:
            thread.join()

    def process_product(self, product_name):
        try:
            local_product = product_name
            variables = self.fetch_latest_variables(local_product)
            if not variables:
                logger.error(f" IB_EQUITY | process_product | Product: {local_product} |  Note: No data available ")
                return
            
            ib_atr = round(variables.get(f'{local_product}_IB_ATR'), 2)
            ib_high = round(variables.get(f'{local_product}_IB_HIGH'), 2)
            ib_low = round(variables.get(f'{local_product}_IB_LOW'), 2)
            prior_close = round(variables.get(f'{local_product}_PRIOR_CLOSE'), 2)
            day_open = round(variables.get(f'{local_product}_DAY_OPEN'), 2)
            prior_high = round(variables.get(f'{local_product}_PRIOR_HIGH'), 2)
            prior_low = round(variables.get(f'{local_product}_PRIOR_LOW'), 2)
            cpl = round(variables.get(f'{local_product}_CPL'), 2)
            fd_vpoc = round(variables.get(f'{local_product}_5D_VPOC'), 2)
            td_vpoc = round(variables.get(f'{local_product}_20D_VPOC'), 2)
            ovn_to_ibh = round(variables.get(f'{local_product}_OVNTOIB_HI'), 2)
            ovn_to_ibl = round(variables.get(f'{local_product}_OVNTOIB_LO'), 2)
            a_high = round(variables.get(f'{local_product}_A_HIGH'), 2)
            a_low = round(variables.get(f'{local_product}_A_LOW'), 2)
            b_high = round(variables.get(f'{local_product}_B_HIGH'), 2)
            b_low = round(variables.get(f'{local_product}_B_LOW'), 2)
            orh = round(variables.get(f'{local_product}_ORH'), 2)
            orl = round(variables.get(f'{local_product}_ORL'), 2)
            rvol = round(variables.get(f'{local_product}_CUMULATIVE_RVOL'), 2)
            overnight_high = round(variables.get(f'{local_product}_OVNH'), 2)
            overnight_low = round(variables.get(f'{local_product}_OVNL'), 2)
            day_high = round(variables.get(f'{local_product}_DAY_HIGH'), 2)
            day_low = round(variables.get(f'{local_product}_DAY_LOW'), 2) 
            impvol = config.cl_impvol
            vwap_slope = variables.get(f'{local_product}_VWAP_SLOPE')

            color_name = self.product_color.get(local_product, ":black_large_square:") 
            color_value = self.get_color(local_product)
            
            # Calculations
            ib_range, ib_type, ib_vatr = self.ib_info(
                ib_high, ib_low, ib_atr
                )
            exhausted, range_used, range_up, range_down, exp_range = self.exp_range_info(
                prior_close, cpl, ovn_to_ibh, ovn_to_ibl, impvol
                )
            gap, gap_tier, gap_size = self.gap_info(
                day_open, prior_high, prior_low, exp_range
                )
            posture = self.posture(
                cpl, fd_vpoc, td_vpoc, exp_range
                )
            open_type = self.open_type(
                a_high, a_low, b_high, b_low, day_open, orh, orl, prior_high, prior_low, day_high, day_low
                )
            
            if vwap_slope >= 0.08 or vwap_slope <= -0.08:
                vwap_type = "Strong"
            else:
                vwap_type = "Weak"
            
            try:
                embed_title = f"{color_name} **{local_product} - Context - IB Check-In** :loudspeaker:"
                embed = DiscordEmbed(
                    title=embed_title,
                    description=(
                        f"**Open Type**: {open_type} \n"
                        f"**{ib_type}**: {ib_range}p | {round(ib_vatr, 2)}% of Avg\n"
                        f"**Vwap {vwap_type}**: {vwap_slope*100}° \n"
                    ),
                    color=color_value
                )
                embed.set_timestamp()  

                if gap != 'No Gap':
                    embed.add_embed_field(name=f":warning: {gap}", value=f"**Size**: {gap_size}p | **Tier**: {gap_tier}", inline=False)
 
                if day_high < overnight_high and day_low > overnight_low:
                    embed.add_embed_field(name=":night_with_stars: Overnight Stat", value="In Play", inline=False)

                embed.add_embed_field(name=":chart_with_upwards_trend: Rvol", value=f"{rvol}%", inline=False)
                embed.add_embed_field(name=":balance_scale: Current Posture", value=f"{posture}", inline=False)

                embed.add_embed_field(name=":bar_chart: Expected Range", value=(
                    f"**Rng Used**: {exhausted} | {range_used}% Used \n"
                    f"**Range Left Up**: {range_up}{'' if range_up == 'Exhausted' else '%'} \n"
                    f"**Range Left Down**: {range_down}{'' if range_down == 'Exhausted' else '%'} "
                ), inline=False)
                
                self.send_alert_embed(embed, product_name=local_product, username=None, avatar_url=None)
                
            except Exception as e:
                logger.error(f" IB_EQUITY | process_product | Product: {local_product} | Error sending Discord message: {e}")
        except Exception as e:
            logger.error(f" IB_EQUITY | process_product | Product: {local_product} | Error processing: {e}")