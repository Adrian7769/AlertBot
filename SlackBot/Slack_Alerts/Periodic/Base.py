import os
import slack
from datetime import datetime
import logging
from logs.Logging_Config import setup_logging
from SlackBot.Source.Startup import Initialization 
from dotenv import load_dotenv

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

class Base_Periodic:
    slack_channels = {
        'ES': 'alert_es',
        'NQ': 'alert_nq',
        'RTY': 'alert_rty',
        'CL': 'alert_cl'
    }
    product_color = {
        'ES': 'blue',
        'NQ': 'green',
        'RTY': 'orange',
        'CL': 'purple'
    }

    def __init__(self, files):
        self.files = files
        slack_token = os.getenv("SLACK_TOKEN") 
        self.slack_client = slack.WebClient(token=slack_token)
        self.current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def fetch_latest_variables(self, product_name):
        all_variables = Initialization.prep_data(self.files)
        return all_variables.get(product_name)

    def send_slack_message(self, channel, message):
        if channel:
            try:
                response = self.slack_client.chat_postMessage(channel=channel, text=message) 
                logger.info(f"| Slack Response: {response['ts']}|")
                
            except Exception as e:
                logger.error(f"Failed to send message to {channel}: {e}")
        else:
            logger.warning(f"No Slack channel configured for the product.")