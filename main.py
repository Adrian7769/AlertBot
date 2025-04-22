from watchdog.observers import Observer
from alertbot.source.filechange import *
from alertbot.utils import config
from alertbot.source.startup import *
from alertbot.alerts.periodic.ib_crude import IB_Crude_Alert
from alertbot.alerts.periodic.ib_equity import IB_Equity_Alert
from alertbot.alerts.periodic.economic import Economic
from alertbot.alerts.periodic.gap_equity import Gap_Check_Equity
from alertbot.alerts.periodic.gap_crude import Gap_Check_Crude
from logs.Logging_Config import setup_logging
from zoneinfo import ZoneInfo
import time
from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os

#                Necessary Additions by 4/07/25
# ------------------------------------------------------------ #
# Optimization!
# ------------------------------------------------------------ #

def main():
    start_time = time.time()
    setup_logging()
    logger = logging.getLogger(__name__)
    initialization = Initialization()
    logger.debug(" Main | Note: Fetching External Data\n")
    # ------------------------- Startup Processes ------------------------------ #
    es_impvol, nq_impvol, rty_impvol, cl_impvol = initialization.grab_impvol(external_impvol)
    config.set_impvol(es_impvol, nq_impvol, rty_impvol, cl_impvol)
    es_bias, nq_bias, rty_bias, cl_bias = initialization.grab_bias(external_bias)
    config.set_bias(es_bias, nq_bias, rty_bias, cl_bias)
    es_swing_bias, nq_swing_bias, rty_swing_bias, cl_swing_bias = initialization.grab_swing_bias(external_swing_bias)
    config.set_swing_bias(es_swing_bias, nq_swing_bias, rty_swing_bias, cl_swing_bias)    
    # ---------------------- Publish Prep PDFs to Discord ------------------------ #
    ib_equity_alert = IB_Equity_Alert(files)
    ib_crude_alert = IB_Crude_Alert(files)
    economic_alert = Economic(files)
    gap_check_equity_alert = Gap_Check_Equity(files)
    gap_check_crude_alert = Gap_Check_Crude(files)
    est = ZoneInfo('America/New_York')
    # ---------------------- Initialize APScheduler ----------------------------- #
    scheduler = BackgroundScheduler(timezone=est)
    # Schedule Econ Alert at 8:55 AM EST every day
    scheduler.add_job(
        economic_alert.send_alert,
        trigger=CronTrigger(hour=8, minute=55, timezone=est),
        name='Economic Alert',
        misfire_grace_time=60
    )
    # Schedule Gap Check Equity 9:30 AM EST every day
    scheduler.add_job(
        gap_check_equity_alert.send_alert,
        trigger=CronTrigger(hour=9, minute=30,second=45, timezone=est),
        name='Gap Check Equity',
        misfire_grace_time=60
    )      
    # Schedule Gap Check Crude at 9:00 AM EST every day
    scheduler.add_job(
        gap_check_crude_alert.send_alert,
        trigger=CronTrigger(hour=9, minute=0, second=40, timezone=est),
        name='Gap Check Crude',
        misfire_grace_time=60
    )    
    # Schedule IB Equity Alert at 10:30 AM EST every day
    scheduler.add_job(
        ib_equity_alert.send_alert,
        trigger=CronTrigger(hour=10, minute=30, second=1, timezone=est),
        name='IB Equity Alert',
        misfire_grace_time=60
    )
    # Schedule IB Crude Alert at 10:00 AM EST every day
    scheduler.add_job(
        ib_crude_alert.send_alert,
        trigger=CronTrigger(hour=10, minute=0, second=1, timezone=est),
        name='IB Crude Alert',
        misfire_grace_time=60
    )
    scheduler.start()
    logger.info("APScheduler started.")
    # ---------------------- Start Monitoring Files ----------------------------- #
    logger.info(" Main | Note: Press Enter To Start Monitoring...")
    input("")
    event_handler = FileChangeHandler(files, conditions, debounce_interval=1.0)
    observer = Observer()
    directories_to_watch = set(os.path.dirname(os.path.abspath(task["filepath"])) for task in files)
    for directory in directories_to_watch:
        observer.schedule(event_handler, path=directory, recursive=False)
    observer.start()
    logger.info(" Main | Note: Monitoring started. Press 'Ctrl+C' to stop.")
    try:
        while True:
            time.sleep(1) 
    except KeyboardInterrupt:
        logger.info(" Main | Note: Shutting down...")
        observer.stop()
        scheduler.shutdown()
    observer.join()
    end_time = time.time()
    elapsed_time = timedelta(seconds=end_time - start_time)
    logger.info(f"\n Main | Note: Script ran for {elapsed_time}")
if __name__ == '__main__': 
    main()