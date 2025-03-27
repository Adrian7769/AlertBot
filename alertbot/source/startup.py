import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from discord_webhook import DiscordEmbed
import logging
from alertbot.source.constants import *
from alertbot.alerts.base import Base
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import os 
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import time as time_module

logger = logging.getLogger(__name__)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_file(r"alertbot\utils\credentials.json", scopes=scopes)
client = gspread.authorize(creds)

class Initialization(Base):
    
    def grab_impvol(self, external_impvol): 
        
        output_impvol = {}

        for task in external_impvol:
            workbook = client.open_by_key(task["sheet_id"])
            sheet = workbook.worksheet(task["sheet_name"])
            cell_value = sheet.cell(task["row_number"], task["col_number"]).value
            
            logger.debug(f" Startup | grab_impvol | Sheet: {task['sheet_name']} | Row: {task['row_number']}  | Column: {task['col_number']}")
            
            if "ES" in task["sheet_name"]:
                output_impvol['es_impvol'] = cell_value
            elif "NQ" in task["sheet_name"]:
                output_impvol['nq_impvol'] = cell_value
            elif "RTY" in task["sheet_name"]:
                output_impvol['rty_impvol'] = cell_value
            elif "CL" in task["sheet_name"]:
                output_impvol['cl_impvol'] = cell_value
        
        es_impvol = float(output_impvol['es_impvol'].strip('%'))
        nq_impvol = float(output_impvol['nq_impvol'].strip('%'))
        rty_impvol = float(output_impvol['rty_impvol'].strip('%'))
        cl_impvol = float(output_impvol['cl_impvol'].strip('%'))
        
        logger.debug(f" Startup | grab_impvol | ES_IMP: {es_impvol*100} | NQ_IMP: {nq_impvol*100} | RTY_IMP: {rty_impvol*100} | CL_IMP: {cl_impvol*100}")
        return es_impvol*100, nq_impvol*100, rty_impvol*100, cl_impvol*100
    
    def grab_bias(self, external_bias):
        output_bias = {}
        for task in external_bias:
            workbook = client.open_by_key(task["sheet_id"])
            sheet = workbook.worksheet(task["sheet_name"])
            cell_value = sheet.cell(task["row_number"], task["col_number"]).value
            logger.debug(f" Startup | grab_bias | Sheet: {task['sheet_name']} | Row: {task['row_number']}  | Column: {task['col_number']}")
            if "ES" in task["sheet_name"]:
                output_bias['es_bias'] = cell_value
            elif "NQ" in task["sheet_name"]:
                output_bias['nq_bias'] = cell_value
            elif "RTY" in task["sheet_name"]:
                output_bias['rty_bias'] = cell_value
            elif "CL" in task["sheet_name"]:
                output_bias['cl_bias'] = cell_value
        es_bias = output_bias['es_bias']
        nq_bias = output_bias['nq_bias']
        rty_bias = output_bias['rty_bias']
        cl_bias = output_bias['cl_bias']
        logger.debug(f" Startup | grab_bias | ES_Bias: {es_bias} | NQ_Bias: {nq_bias} | RTY_Bias: {rty_bias} | CL_Bias: {cl_bias}")
        return es_bias, nq_bias, rty_bias, cl_bias
    
    def publish_prep(self):
        preps = {
            'ES': {
                'drive_folder_id': '1FjvgLwW4I7lLZmv33IeDcsL1X2urOOSy', 
                'icon': '🔵',
            },
            'NQ': {
                'drive_folder_id': '10RPtoqSu5okb2g8628avMFj6dNhJztEi', 
                'icon': '🟢',
            },
            'RTY': {
                'drive_folder_id': '1PHlBBlnawCpkzEAr_L3Rg5m4wFnpEeyJ', 
                'icon': '🟠',
            },
            'CL': {
                'drive_folder_id': '164e7-8yvec_EoAdG0T4Px36xL2sFxAcz', 
                'icon': '🟣',
            },
            'QuickSheet': {
                'drive_folder_id': '1_3bDtMevegvk9M8W2LPXq8_vT1v2wom5', 
                'icon': '🔴',
            }            
        }
        try:
            creds = Credentials.from_service_account_file(
                r"alertbot\utils\credentials.json",
                scopes=['https://www.googleapis.com/auth/drive']
            )
            drive_service = build('drive', 'v3', credentials=creds)
            logger.debug("Startup | publish_prep | Google Drive API client initialized.")
        except Exception as e:
            logger.error(f"Startup | publish_prep | Failed to initialize Google Drive API client: {e}")
            return
        for product, config in preps.items():
            drive_folder_id = config['drive_folder_id']
            icon = config['icon']
            now = datetime.now()
            date_str = f"{now.month}-{now.day}-{now.year}"
            filename = f"{product}_PREP_{date_str}.pdf"
            logger.debug(f"Startup | publish_prep | Processing {product} prep.")
            logger.debug(f"Startup | publish_prep | Expected filename: {filename}")
            query = f"name='{filename}' and '{drive_folder_id}' in parents and trashed=false"
            try:
                results = drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name, webViewLink)',
                    pageSize=1
                ).execute()
                files = results.get('files', [])
                if not files:
                    logger.error(f"Startup | publish_prep | File {filename} not found in Drive folder {drive_folder_id}.")
                    continue
                file = files[0]
                file_id = file['id']
                web_view_link = file.get('webViewLink')
                logger.debug(f"Startup | publish_prep | Retrived webViewLink for {filename}: {web_view_link}.")
            except HttpError as e:
                logger.error(f"Startup | publish_prep | Failed to retrieve webViewLink for {filename}: {e}")
                continue
            try:
                permission = {
                    'type': 'anyone',
                    'role': 'reader'    
                }
                drive_service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    fields='id'
                ).execute()
                logger.debug(f"Startup | publish_prep | Set permissions for {filename} to 'anyone with the link can view'.")
            except HttpError as e:
                logger.error(f"Startup | publish_prep | Failed to create permission for {filename}: {e}")
            try:
                # Retrieve the updated webViewLink after setting permissions
                file = drive_service.files().get(
                    fileId=file_id,
                    fields='webViewLink'
                ).execute()
                web_view_link = file.get('webViewLink')
                logger.debug(f"Startup | publish_prep | Retrieved webViewLink for {filename}: {web_view_link}")
            except HttpError as e:
                logger.error(f"Startup | publish_prep | Failed to retrieve webViewLink for {filename}: {e}")
                continue
            try:
                embed_title = f"{product} Prep For **{date_str}**"
                embed = DiscordEmbed(
                    title=embed_title,
                    color=self.product_color.get(product, 0x000000)
                )
                embed.set_timestamp()
                # Add a field with the link to view the PDF
                if web_view_link:
                    embed.add_embed_field(
                        name="📄 Auction Prep PDF",
                        value=f"View Prep [Here]({web_view_link})",
                        inline=False
                    )
                else:
                    logger.warning(f"Startup | publish_prep | No webViewLink available for {filename}.")
                webhook_url = self.discord_webhooks_preps.get(product)
                if not webhook_url:
                    logger.error(f"Startup | publish_prep | No Discord webhook URL configured for product '{product}'.")
                    continue
                self.send_discord_embed(
                    webhook_url=webhook_url,
                    embed=embed,
                    username=None, 
                    avatar_url=None 
                )
                logger.info(f"Startup | publish_prep | Sent Discord embed with link for {filename} to webhook for {product}.")
            except Exception as e:
                logger.error(f"Startup | publish_prep | Failed to create or send Discord embed for {product}: {e}")
                continue
        logger.info("Startup | publish_prep | Completed publish_prep function.")
    def prep_data(files):
        def safe_read_csv(filepath, **kwargs):
            max_retries = 5
            delay = 0.5
            last_size = -1
            for attempt in range(max_retries):
                try:
                    current_size = os.path.getsize(filepath)
                except OSError as e:
                    logger.error(f"Error getting file size for {filepath}: {e}")
                    time_module.sleep(delay)
                    continue
                if current_size == last_size and current_size > 0:
                    try:
                        df = pd.read_csv(filepath, **kwargs)
                        if not df.empty:
                            return df
                    except pd.errors.EmptyDataError:
                        logger.debug(f"File {filepath} is empty. Retrying...")
                    except Exception as e:
                        logger.error(f"Error reading {filepath}: {e}")
                else:
                    last_size = current_size
                time_module.sleep(delay)
            raise ValueError(f"Failed to read stable data from {filepath} after {max_retries} attempts.")
        all_variables = {}
        period_equity = {
            'A': time(9, 30),
            'B': time(10, 0),
            'C': time(10, 30),
            'D': time(11, 0),
            'E': time(11, 30),
            'F': time(12, 0),
            'G': time(12, 30),
            'H': time(13, 0),
            'I': time(13, 30),
            'J': time(14, 0),
            'K': time(14, 30),
            'L': time(15, 0),
            'M': time(15, 30),                                                                                                                        
        }
        period_crude = {
            'A': time(9, 0),
            'B': time(9, 30),
            'C': time(10, 0),
            'D': time(10, 30),
            'E': time(11, 0),
            'F': time(11, 30),
            'G': time(12, 0),
            'H': time(12, 30),
            'I': time(13, 0),
            'J': time(13, 30),
            'K': time(14, 0),        
        }        
        for task in files:  
            est = ZoneInfo('America/New_York')
            now = datetime.now(est).time()
            process_task = False
            if "CL" in task["name"]:
                start_time = time(9, 0)
                end_time = time(14, 30)
                if start_time <= now <= end_time:
                    process_task = True 
                    #logger.debug(f" Startup | prep_data | Task: {task["name"]} | In Product Time Range: {process_task}")
            elif any(name in task["name"] for name in ["ES", "NQ", "RTY"]):
                start_time = time(9, 30)
                end_time = time(16, 0)
                if start_time <= now <= end_time:
                    process_task = True 
                    #logger.debug(f" Startup | prep_data | Task: {task["name"]} | In Product Time Range: {process_task}")
            else:
                process_task = False
                #logger.debug(f" Startup | prep_data | Task: {task["name"]} | Process: {process_task} | Note: Out of Time Range For Product")
            if not process_task:
                continue
            if task["header_row"] == 1:
                data = safe_read_csv(task["filepath"], delimiter='\t', header=None)
            elif task["header_row"] == 0:
                data = safe_read_csv(task["filepath"], delimiter='\t')
                data = data.reset_index()
            else:
                raise ValueError("header_row should be either 0 or 1")
            # Set Header and Configure DF
            pd.options.mode.copy_on_write = True
            data.columns = data.iloc[task["iloc1"]]
            data = data[task["iloc2"]:]
            # Drop Unwanted Columns and N/A
            existing_columns_to_drop = [col for col in columns_to_drop if col in data.columns]
            data = data.drop(columns=existing_columns_to_drop)
            df_cleaned = data.loc[:, data.columns.notna()]
            data = df_cleaned
            data = data.dropna()
            # Set Date-Time As Index
            if 'Date Time' in data.columns:
                data['Date Time'] = pd.to_datetime(data['Date Time'], errors='coerce')
                data.set_index('Date Time', inplace=True)
            # Converting Columns to float
            for columns in task["columns"]:
                data[columns] = data[columns].str.replace(',', '.').astype(float)
            #logger.debug(f" Startup | prep_data | Task: {task["name"]} | Data-Frame: \n{data.head()}")
            variables = {}
            match task["name"]:
                case "ES_1":
                    # ------------------- Use Integer Based iLoc ----------------------- #
                    variables['ES_RTH_VWAP'] = float(data.iloc[0]['[ID24.SG1] RTH_VWAP'])
                    variables['ES_VWAP_SLOPE'] = float(data.iloc[0]['[ID23.SG2] Vwap_Slope'])
                    variables['ES_DAY_OPEN'] = float(data.iloc[0]['[ID2.SG1] Day_Open'])
                    variables['ES_DAY_HIGH'] = float(data.iloc[0]['[ID2.SG2] Day_High'])
                    variables['ES_DAY_LOW'] = float(data.iloc[0]['[ID2.SG3] Day_Low'])
                    variables['ES_DAY_CLOSE'] = float(data.iloc[0]['[ID2.SG4] Day_Close'])
                    variables['ES_DAY_VPOC'] = float(data.iloc[0]['[ID1.SG1] Day_Vpoc'])
                    variables['ES_PRIOR_VPOC'] = float(data.iloc[0]['[ID9.SG1] Prior_Vpoc'])
                    variables['ES_PRIOR_HIGH'] = float(data.iloc[0]['[ID8.SG2] Prior_High'])
                    variables['ES_PRIOR_PRIOR_HIGH'] = float(data.iloc[12]['[ID8.SG2] Prior_High'])
                    variables['ES_PRIOR_LOW'] = float(data.iloc[0]['[ID8.SG3] Prior_Low'])
                    variables['ES_PRIOR_PRIOR_LOW'] = float(data.iloc[12]['[ID8.SG3] Prior_Low'])
                    variables['ES_PRIOR_CLOSE'] = float(data.iloc[0]['[ID8.SG4] Prior_Close'])
                    variables['ES_RVOL'] = float(data.iloc[0]['[ID6.SG1] R_Vol'])
                    variables['ES_CUMULATIVE_RVOL'] = float(data.iloc[0]['[ID6.SG2] R_Vol_Cumulative'])
                    variables['ES_TOTAL_RTH_DELTA'] = float(data.iloc[0]['[ID4.SG4] Total_Delta'])
                    # ---------------------- Use Date Date Time Loc ------------------------- #
                    latest_date = data.index.max().date()
                    
                    # ----- Current Session ---- #
                    current_period_datetimes = {
                        label: datetime.combine(latest_date, period_time)
                        for label, period_time in period_equity.items()
                    }
                    for period_label, specific_datetime in current_period_datetimes.items():    
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['ES_A_HIGH'] = float(data.loc[specific_datetime]['[ID10.SG1] A_High'])
                                    variables['ES_A_LOW'] = float(data.loc[specific_datetime]['[ID10.SG2] A_Low'])    
                                case 'B':
                                    variables['ES_B_HIGH'] = float(data.loc[specific_datetime]['[ID11.SG1] B_High'])
                                    variables['ES_B_LOW'] = float(data.loc[specific_datetime]['[ID11.SG2] B_Low'])
                                case 'C':
                                    variables['ES_C_HIGH'] = float(data.loc[specific_datetime]['[ID12.SG1] C_High'])
                                    variables['ES_C_LOW'] = float(data.loc[specific_datetime]['[ID12.SG2] C_Low'])
                                case 'D':
                                    variables['ES_D_HIGH'] = float(data.loc[specific_datetime]['[ID13.SG1] D_High'])
                                    variables['ES_D_LOW'] = float(data.loc[specific_datetime]['[ID13.SG2] D_Low'])
                                case 'E':
                                    variables['ES_E_HIGH'] = float(data.loc[specific_datetime]['[ID14.SG1] E_High'])
                                    variables['ES_E_LOW'] = float(data.loc[specific_datetime]['[ID14.SG2] E_Low'])
                                case 'F':
                                    variables['ES_F_HIGH'] = float(data.loc[specific_datetime]['[ID15.SG1] F_High'])
                                    variables['ES_F_LOW'] = float(data.loc[specific_datetime]['[ID15.SG2] F_Low'])
                                case 'G':
                                    variables['ES_G_HIGH'] = float(data.loc[specific_datetime]['[ID16.SG1] G_High'])
                                    variables['ES_G_LOW'] = float(data.loc[specific_datetime]['[ID16.SG2] G_Low'])
                                case 'H':
                                    variables['ES_H_HIGH'] = float(data.loc[specific_datetime]['[ID17.SG1] H_High'])
                                    variables['ES_H_LOW'] = float(data.loc[specific_datetime]['[ID17.SG2] H_Low'])
                                case 'I':
                                    variables['ES_I_HIGH'] = float(data.loc[specific_datetime]['[ID18.SG1] I_High'])
                                    variables['ES_I_LOW'] = float(data.loc[specific_datetime]['[ID18.SG2] I_Low'])
                                case 'J':
                                    variables['ES_J_HIGH'] = float(data.loc[specific_datetime]['[ID19.SG1] J_High'])
                                    variables['ES_J_LOW'] = float(data.loc[specific_datetime]['[ID19.SG2] J_Low'])
                                case 'K':
                                    variables['ES_K_HIGH'] = float(data.loc[specific_datetime]['[ID20.SG1] K_High'])
                                    variables['ES_K_LOW'] = float(data.loc[specific_datetime]['[ID20.SG2] K_Low'])
                                case 'L':
                                    variables['ES_L_HIGH'] = float(data.loc[specific_datetime]['[ID21.SG1] L_High'])
                                    variables['ES_L_LOW'] = float(data.loc[specific_datetime]['[ID21.SG2] L_Low'])
                                case 'M':
                                    variables['ES_M_HIGH'] = float(data.loc[specific_datetime]['[ID22.SG1] M_High'])
                                    variables['ES_M_LOW'] = float(data.loc[specific_datetime]['[ID22.SG2] M_Low'])
                        else:
                            pass
                    # ---- Prior Session ---- #
                    previous_date = latest_date - timedelta(days=1)
                    prior_period_datetimes = {
                        label: datetime.combine(previous_date, period_time)
                        for label, period_time in period_equity.items()
                    }    
                    for period_label, specific_datetime in prior_period_datetimes.items():
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['ES_PRIOR_A_HIGH'] = float(data.loc[specific_datetime]['[ID10.SG1] A_High'])
                                    variables['ES_PRIOR_A_LOW'] = float(data.loc[specific_datetime]['[ID10.SG2] A_Low'])    
                                case 'B':
                                    variables['ES_PRIOR_B_HIGH'] = float(data.loc[specific_datetime]['[ID11.SG1] B_High'])
                                    variables['ES_PRIOR_B_LOW'] = float(data.loc[specific_datetime]['[ID11.SG2] B_Low'])
                                case 'C':
                                    variables['ES_PRIOR_C_HIGH'] = float(data.loc[specific_datetime]['[ID12.SG1] C_High'])
                                    variables['ES_PRIOR_C_LOW'] = float(data.loc[specific_datetime]['[ID12.SG2] C_Low'])
                                case 'D':
                                    variables['ES_PRIOR_D_HIGH'] = float(data.loc[specific_datetime]['[ID13.SG1] D_High'])
                                    variables['ES_PRIOR_D_LOW'] = float(data.loc[specific_datetime]['[ID13.SG2] D_Low'])
                                case 'E':
                                    variables['ES_PRIOR_E_HIGH'] = float(data.loc[specific_datetime]['[ID14.SG1] E_High'])
                                    variables['ES_PRIOR_E_LOW'] = float(data.loc[specific_datetime]['[ID14.SG2] E_Low'])
                                case 'F':
                                    variables['ES_PRIOR_F_HIGH'] = float(data.loc[specific_datetime]['[ID15.SG1] F_High'])
                                    variables['ES_PRIOR_F_LOW'] = float(data.loc[specific_datetime]['[ID15.SG2] F_Low'])
                                case 'G':
                                    variables['ES_PRIOR_G_HIGH'] = float(data.loc[specific_datetime]['[ID16.SG1] G_High'])
                                    variables['ES_PRIOR_G_LOW'] = float(data.loc[specific_datetime]['[ID16.SG2] G_Low'])
                                case 'H':
                                    variables['ES_PRIOR_H_HIGH'] = float(data.loc[specific_datetime]['[ID17.SG1] H_High'])
                                    variables['ES_PRIOR_H_LOW'] = float(data.loc[specific_datetime]['[ID17.SG2] H_Low'])
                                case 'I':
                                    variables['ES_PRIOR_I_HIGH'] = float(data.loc[specific_datetime]['[ID18.SG1] I_High'])
                                    variables['ES_PRIOR_I_LOW'] = float(data.loc[specific_datetime]['[ID18.SG2] I_Low'])
                                case 'J':
                                    variables['ES_PRIOR_J_HIGH'] = float(data.loc[specific_datetime]['[ID19.SG1] J_High'])
                                    variables['ES_PRIOR_J_LOW'] = float(data.loc[specific_datetime]['[ID19.SG2] J_Low'])
                                case 'K':
                                    variables['ES_PRIOR_K_HIGH'] = float(data.loc[specific_datetime]['[ID20.SG1] K_High'])
                                    variables['ES_PRIOR_K_LOW'] = float(data.loc[specific_datetime]['[ID20.SG2] K_Low'])
                                case 'L':
                                    variables['ES_PRIOR_L_HIGH'] = float(data.loc[specific_datetime]['[ID21.SG1] L_High'])
                                    variables['ES_PRIOR_L_LOW'] = float(data.loc[specific_datetime]['[ID21.SG2] L_Low'])
                                case 'M':
                                    variables['ES_PRIOR_M_HIGH'] = float(data.loc[specific_datetime]['[ID22.SG1] M_High'])
                                    variables['ES_PRIOR_M_LOW'] = float(data.loc[specific_datetime]['[ID22.SG2] M_Low'])
                        else:
                            pass      
                case "ES_2":
                    # ------------------- Use Integer Based Loc ----------------------- #
                    variables['ES_ETH_VWAP'] = float(data.iloc[0]['[ID7.SG1] ETH_VWAP'])
                    variables['ES_ETH_TOP_1'] = float(data.iloc[0]['[ID7.SG2] Top_1'])
                    variables['ES_ETH_BOTTOM_1'] = float(data.iloc[0]['[ID7.SG3] Bottom_1'])
                    variables['ES_ETH_TOP_2'] = float(data.iloc[0]['[ID7.SG4] Top_2'])
                    variables['ES_ETH_BOTTOM_2'] = float(data.iloc[0]['[ID7.SG5] Bottom_2'])
                    variables['ES_CPL'] = float(data.iloc[0]['[ID2.SG1] CPL'])
                    variables['ES_5D_VPOC'] = float(data.iloc[0]['[ID4.SG2] 5DVPOC'])
                    variables['ES_20D_VPOC'] = float(data.iloc[0]['[ID3.SG2] 20DVPOC'])
                    variables['ES_P_WOPEN'] = float(data.iloc[0]['[ID5.SG1] P_WOPEN'])
                    variables['ES_P_WHIGH'] = float(data.iloc[0]['[ID5.SG2] P_WHIGH'])
                    variables['ES_P_WLO'] = float(data.iloc[0]['[ID5.SG3] P_WLO'])
                    variables['ES_P_WCLOSE'] = float(data.iloc[0]['[ID5.SG4] P_WCLOSE'])
                    variables['ES_P_WVPOC'] = float(data.iloc[0]['[ID11.SG1] P_WVPOC'])
                    variables['ES_WVWAP'] = float(data.iloc[0]['[ID10.SG1] WVWAP'])
                    variables['ES_P_MOPEN'] = float(data.iloc[0]['[ID8.SG1] P_MOPEN'])
                    variables['ES_P_MHIGH'] = float(data.iloc[0]['[ID8.SG2] P_MHIGH'])
                    variables['ES_P_MLO'] = float(data.iloc[0]['[ID8.SG3] P_MLO'])
                    variables['ES_P_MCLOSE'] = float(data.iloc[0]['[ID8.SG4] P_MCLOSE'])
                    variables['ES_P_MVPOC'] = float(data.iloc[0]['[ID12.SG1] P_MVPOC'])
                    variables['ES_MVWAP'] = float(data.iloc[0]['[ID1.SG1] MVWAP'])
                    # ----------------- Period-based ETH VWAP Extraction ----------------- #
                    latest_date = data.index.max().date()
                    
                    for period_label, period_time in period_equity.items():
                        specific_datetime = datetime.combine(latest_date, period_time)
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['ES_ETH_VWAP_A'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_A'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_A'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                    
                                case 'B':
                                    variables['ES_ETH_VWAP_B'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_B'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_B'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'C':
                                    variables['ES_ETH_VWAP_C'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_C'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_C'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'D':
                                    variables['ES_ETH_VWAP_C'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_C'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_C'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'E':
                                    variables['ES_ETH_VWAP_E'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_E'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_E'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'F':
                                    variables['ES_ETH_VWAP_F'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_F'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_F'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'G':
                                    variables['ES_ETH_VWAP_G'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_G'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_G'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'H':
                                    variables['ES_ETH_VWAP_H'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_H'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_H'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'I':
                                    variables['ES_ETH_VWAP_I'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_I'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_I'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'J':
                                    variables['ES_ETH_VWAP_J'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_J'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_J'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'K':
                                    variables['ES_ETH_VWAP_K'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_K'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_K'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'L':
                                    variables['ES_ETH_VWAP_L'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_L'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_L'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'M':
                                    variables['ES_ETH_VWAP_M'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['ES_ETH_TOP_1_M'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['ES_ETH_BOTTOM_1_M'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                        else:
                            pass
                case "ES_3":
                    variables['ES_IB_ATR'] = float(data.iloc[1]['[ID2.SG1] IB ATR'])
                    variables['ES_IB_HIGH'] = float(data.iloc[0]['[ID1.SG2] IBH'])
                    variables['ES_IB_LOW'] = float(data.iloc[0]['[ID1.SG3] IBL'])
                    variables['ES_PRIOR_IB_HIGH'] = float(data.iloc[1]['[ID1.SG2] IBH'])
                    variables['ES_PRIOR_IB_LOW'] = float(data.iloc[1]['[ID1.SG3] IBL'])                    
                case "ES_4":
                    variables['ES_OVNH'] = float(data.iloc[0]['[ID1.SG2] OVN H'])
                    variables['ES_OVNL'] = float(data.iloc[0]['[ID1.SG3] OVN L'])
                    variables['ES_TOTAL_OVN_DELTA'] = float(data.iloc[0]['[ID3.SG4] OVN Total'])
                case "ES_5":
                    variables['ES_OVNTOIB_HI'] = float(data.iloc[0]['[ID1.SG2] OVNTOIB_HI'])
                    variables['ES_OVNTOIB_LO'] = float(data.iloc[0]['[ID1.SG3] OVNTOIB_LO'])
                case "ES_6":
                    variables['ES_EURO_IBH'] = float(data.iloc[0]['[ID1.SG2] EURO IBH'])
                    variables['ES_EURO_IBL'] = float(data.iloc[0]['[ID1.SG3] EURO IBL'])
                case "ES_7":
                    variables['ES_ORH'] = float(data.iloc[0]['[ID1.SG2] ORH'])
                    variables['ES_ORL'] = float(data.iloc[0]['[ID1.SG3] ORL'])
                case "NQ_1":
                    # ------------------- Use Integer Based iLoc ----------------------- #
                    variables['NQ_RTH_VWAP'] = float(data.iloc[0]['[ID24.SG1] RTH_VWAP'])
                    variables['NQ_VWAP_SLOPE'] = float(data.iloc[0]['[ID23.SG2] Vwap_Slope'])
                    variables['NQ_DAY_OPEN'] = float(data.iloc[0]['[ID2.SG1] Day_Open'])
                    variables['NQ_DAY_HIGH'] = float(data.iloc[0]['[ID2.SG2] Day_High'])
                    variables['NQ_DAY_LOW'] = float(data.iloc[0]['[ID2.SG3] Day_Low'])
                    variables['NQ_DAY_CLOSE'] = float(data.iloc[0]['[ID2.SG4] Day_Close'])
                    variables['NQ_DAY_VPOC'] = float(data.iloc[0]['[ID1.SG1] Day_Vpoc'])
                    variables['NQ_PRIOR_VPOC'] = float(data.iloc[0]['[ID9.SG1] Prior_Vpoc'])
                    variables['NQ_PRIOR_HIGH'] = float(data.iloc[0]['[ID8.SG2] Prior_High'])
                    variables['NQ_PRIOR_LOW'] = float(data.iloc[0]['[ID8.SG3] Prior_Low'])
                    variables['NQ_PRIOR_CLOSE'] = float(data.iloc[0]['[ID8.SG4] Prior_Close'])
                    variables['NQ_RVOL'] = float(data.iloc[0]['[ID6.SG1] R_Vol'])
                    variables['NQ_CUMULATIVE_RVOL'] = float(data.iloc[0]['[ID6.SG2] R_Vol_Cumulative'])
                    variables['NQ_TOTAL_RTH_DELTA'] = float(data.iloc[0]['[ID4.SG4] Total_Delta'])
                    # ---------------------- Use Date Date Time Loc ------------------------- #
                    latest_date = data.index.max().date()
                    
                    # ----- Current Session ---- #
                    current_period_datetimes = {
                        label: datetime.combine(latest_date, period_time)
                        for label, period_time in period_equity.items()
                    }
                    for period_label, specific_datetime in current_period_datetimes.items():    
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['NQ_A_HIGH'] = float(data.loc[specific_datetime]['[ID10.SG1] A_High'])
                                    variables['NQ_A_LOW'] = float(data.loc[specific_datetime]['[ID10.SG2] A_Low'])    
                                case 'B':
                                    variables['NQ_B_HIGH'] = float(data.loc[specific_datetime]['[ID11.SG1] B_High'])
                                    variables['NQ_B_LOW'] = float(data.loc[specific_datetime]['[ID11.SG2] B_Low'])
                                case 'C':
                                    variables['NQ_C_HIGH'] = float(data.loc[specific_datetime]['[ID12.SG1] C_High'])
                                    variables['NQ_C_LOW'] = float(data.loc[specific_datetime]['[ID12.SG2] C_Low'])
                                case 'D':
                                    variables['NQ_D_HIGH'] = float(data.loc[specific_datetime]['[ID13.SG1] D_High'])
                                    variables['NQ_D_LOW'] = float(data.loc[specific_datetime]['[ID13.SG2] D_Low'])
                                case 'E':
                                    variables['NQ_E_HIGH'] = float(data.loc[specific_datetime]['[ID14.SG1] E_High'])
                                    variables['NQ_E_LOW'] = float(data.loc[specific_datetime]['[ID14.SG2] E_Low'])
                                case 'F':
                                    variables['NQ_F_HIGH'] = float(data.loc[specific_datetime]['[ID15.SG1] F_High'])
                                    variables['NQ_F_LOW'] = float(data.loc[specific_datetime]['[ID15.SG2] F_Low'])
                                case 'G':
                                    variables['NQ_G_HIGH'] = float(data.loc[specific_datetime]['[ID16.SG1] G_High'])
                                    variables['NQ_G_LOW'] = float(data.loc[specific_datetime]['[ID16.SG2] G_Low'])
                                case 'H':
                                    variables['NQ_H_HIGH'] = float(data.loc[specific_datetime]['[ID17.SG1] H_High'])
                                    variables['NQ_H_LOW'] = float(data.loc[specific_datetime]['[ID17.SG2] H_Low'])
                                case 'I':
                                    variables['NQ_I_HIGH'] = float(data.loc[specific_datetime]['[ID18.SG1] I_High'])
                                    variables['NQ_I_LOW'] = float(data.loc[specific_datetime]['[ID18.SG2] I_Low'])
                                case 'J':
                                    variables['NQ_J_HIGH'] = float(data.loc[specific_datetime]['[ID19.SG1] J_High'])
                                    variables['NQ_J_LOW'] = float(data.loc[specific_datetime]['[ID19.SG2] J_Low'])
                                case 'K':
                                    variables['NQ_K_HIGH'] = float(data.loc[specific_datetime]['[ID20.SG1] K_High'])
                                    variables['NQ_K_LOW'] = float(data.loc[specific_datetime]['[ID20.SG2] K_Low'])
                                case 'L':
                                    variables['NQ_L_HIGH'] = float(data.loc[specific_datetime]['[ID21.SG1] L_High'])
                                    variables['NQ_L_LOW'] = float(data.loc[specific_datetime]['[ID21.SG2] L_Low'])
                                case 'M':
                                    variables['NQ_M_HIGH'] = float(data.loc[specific_datetime]['[ID22.SG1] M_High'])
                                    variables['NQ_M_LOW'] = float(data.loc[specific_datetime]['[ID22.SG2] M_Low'])
                        else:
                            pass
                    # ---- Prior Session ---- #
                    previous_date = latest_date - timedelta(days=1)
                    prior_period_datetimes = {
                        label: datetime.combine(previous_date, period_time)
                        for label, period_time in period_equity.items()
                    }    
                    for period_label, specific_datetime in prior_period_datetimes.items():
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['NQ_PRIOR_A_HIGH'] = float(data.loc[specific_datetime]['[ID10.SG1] A_High'])
                                    variables['NQ_PRIOR_A_LOW'] = float(data.loc[specific_datetime]['[ID10.SG2] A_Low'])    
                                case 'B':
                                    variables['NQ_PRIOR_B_HIGH'] = float(data.loc[specific_datetime]['[ID11.SG1] B_High'])
                                    variables['NQ_PRIOR_B_LOW'] = float(data.loc[specific_datetime]['[ID11.SG2] B_Low'])
                                case 'C':
                                    variables['NQ_PRIOR_C_HIGH'] = float(data.loc[specific_datetime]['[ID12.SG1] C_High'])
                                    variables['NQ_PRIOR_C_LOW'] = float(data.loc[specific_datetime]['[ID12.SG2] C_Low'])
                                case 'D':
                                    variables['NQ_PRIOR_D_HIGH'] = float(data.loc[specific_datetime]['[ID13.SG1] D_High'])
                                    variables['NQ_PRIOR_D_LOW'] = float(data.loc[specific_datetime]['[ID13.SG2] D_Low'])
                                case 'E':
                                    variables['NQ_PRIOR_E_HIGH'] = float(data.loc[specific_datetime]['[ID14.SG1] E_High'])
                                    variables['NQ_PRIOR_E_LOW'] = float(data.loc[specific_datetime]['[ID14.SG2] E_Low'])
                                case 'F':
                                    variables['NQ_PRIOR_F_HIGH'] = float(data.loc[specific_datetime]['[ID15.SG1] F_High'])
                                    variables['NQ_PRIOR_F_LOW'] = float(data.loc[specific_datetime]['[ID15.SG2] F_Low'])
                                case 'G':
                                    variables['NQ_PRIOR_G_HIGH'] = float(data.loc[specific_datetime]['[ID16.SG1] G_High'])
                                    variables['NQ_PRIOR_G_LOW'] = float(data.loc[specific_datetime]['[ID16.SG2] G_Low'])
                                case 'H':
                                    variables['NQ_PRIOR_H_HIGH'] = float(data.loc[specific_datetime]['[ID17.SG1] H_High'])
                                    variables['NQ_PRIOR_H_LOW'] = float(data.loc[specific_datetime]['[ID17.SG2] H_Low'])
                                case 'I':
                                    variables['NQ_PRIOR_I_HIGH'] = float(data.loc[specific_datetime]['[ID18.SG1] I_High'])
                                    variables['NQ_PRIOR_I_LOW'] = float(data.loc[specific_datetime]['[ID18.SG2] I_Low'])
                                case 'J':
                                    variables['NQ_PRIOR_J_HIGH'] = float(data.loc[specific_datetime]['[ID19.SG1] J_High'])
                                    variables['NQ_PRIOR_J_LOW'] = float(data.loc[specific_datetime]['[ID19.SG2] J_Low'])
                                case 'K':
                                    variables['NQ_PRIOR_K_HIGH'] = float(data.loc[specific_datetime]['[ID20.SG1] K_High'])
                                    variables['NQ_PRIOR_K_LOW'] = float(data.loc[specific_datetime]['[ID20.SG2] K_Low'])
                                case 'L':
                                    variables['NQ_PRIOR_L_HIGH'] = float(data.loc[specific_datetime]['[ID21.SG1] L_High'])
                                    variables['NQ_PRIOR_L_LOW'] = float(data.loc[specific_datetime]['[ID21.SG2] L_Low'])
                                case 'M':
                                    variables['NQ_PRIOR_M_HIGH'] = float(data.loc[specific_datetime]['[ID22.SG1] M_High'])
                                    variables['NQ_PRIOR_M_LOW'] = float(data.loc[specific_datetime]['[ID22.SG2] M_Low'])
                        else:
                            pass 
                case "NQ_2":
                    variables['NQ_ETH_VWAP'] = float(data.iloc[0]['[ID7.SG1] ETH_VWAP'])
                    variables['NQ_ETH_TOP_1'] = float(data.iloc[0]['[ID7.SG2] Top_1'])
                    variables['NQ_ETH_BOTTOM_1'] = float(data.iloc[0]['[ID7.SG3] Bottom_1'])
                    variables['NQ_ETH_TOP_2'] = float(data.iloc[0]['[ID7.SG4] Top_2'])
                    variables['NQ_ETH_BOTTOM_2'] = float(data.iloc[0]['[ID7.SG5] Bottom_2'])
                    variables['NQ_CPL'] = float(data.iloc[0]['[ID2.SG1] CPL'])
                    variables['NQ_5D_VPOC'] = float(data.iloc[0]['[ID4.SG2] 5DVPOC'])
                    variables['NQ_20D_VPOC'] = float(data.iloc[0]['[ID3.SG2] 20DVPOC'])
                    variables['NQ_P_WOPEN'] = float(data.iloc[0]['[ID5.SG1] P_WOPEN'])
                    variables['NQ_P_WHIGH'] = float(data.iloc[0]['[ID5.SG2] P_WHIGH'])
                    variables['NQ_P_WLO'] = float(data.iloc[0]['[ID5.SG3] P_WLO'])
                    variables['NQ_P_WCLOSE'] = float(data.iloc[0]['[ID5.SG4] P_WCLOSE'])
                    variables['NQ_P_WVPOC'] = float(data.iloc[0]['[ID11.SG1] P_WVPOC'])
                    variables['NQ_WVWAP'] = float(data.iloc[0]['[ID10.SG1] WVWAP'])
                    variables['NQ_P_MOPEN'] = float(data.iloc[0]['[ID8.SG1] P_MOPEN'])
                    variables['NQ_P_MHIGH'] = float(data.iloc[0]['[ID8.SG2] P_MHIGH'])
                    variables['NQ_P_MLO'] = float(data.iloc[0]['[ID8.SG3] P_MLO'])
                    variables['NQ_P_MCLOSE'] = float(data.iloc[0]['[ID8.SG4] P_MCLOSE'])
                    variables['NQ_P_MVPOC'] = float(data.iloc[0]['[ID12.SG1] P_MVPOC'])
                    variables['NQ_MVWAP'] = float(data.iloc[0]['[ID1.SG1] MVWAP'])
                    # ----------------- Period-based ETH VWAP Extraction ----------------- #
                    latest_date = data.index.max().date()
                    
                    for period_label, period_time in period_equity.items():
                        specific_datetime = datetime.combine(latest_date, period_time)
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['NQ_ETH_VWAP_A'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_A'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_A'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                    
                                case 'B':
                                    variables['NQ_ETH_VWAP_B'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_B'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_B'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'C':
                                    variables['NQ_ETH_VWAP_C'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_C'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_C'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'D':
                                    variables['NQ_ETH_VWAP_C'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_C'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_C'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'E':
                                    variables['NQ_ETH_VWAP_E'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_E'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_E'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'F':
                                    variables['NQ_ETH_VWAP_F'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_F'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_F'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'G':
                                    variables['NQ_ETH_VWAP_G'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_G'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_G'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'H':
                                    variables['NQ_ETH_VWAP_H'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_H'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_H'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'I':
                                    variables['NQ_ETH_VWAP_I'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_I'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_I'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'J':
                                    variables['NQ_ETH_VWAP_J'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_J'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_J'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'K':
                                    variables['NQ_ETH_VWAP_K'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_K'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_K'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'L':
                                    variables['NQ_ETH_VWAP_L'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_L'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_L'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'M':
                                    variables['NQ_ETH_VWAP_M'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['NQ_ETH_TOP_1_M'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['NQ_ETH_BOTTOM_1_M'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])   
                        else:
                            pass
                case "NQ_3":
                    variables['NQ_IB_ATR'] = float(data.iloc[1]['[ID2.SG1] IB ATR'])
                    variables['NQ_IB_HIGH'] = float(data.iloc[0]['[ID1.SG2] IBH'])
                    variables['NQ_IB_LOW'] = float(data.iloc[0]['[ID1.SG3] IBL'])
                    variables['NQ_PRIOR_IB_HIGH'] = float(data.iloc[1]['[ID1.SG2] IBH'])
                    variables['NQ_PRIOR_IB_LOW'] = float(data.iloc[1]['[ID1.SG3] IBL'])
                case "NQ_4":
                    variables['NQ_OVNH'] = float(data.iloc[0]['[ID1.SG2] OVN H'])
                    variables['NQ_OVNL'] = float(data.iloc[0]['[ID1.SG3] OVN L'])
                    variables['NQ_TOTAL_OVN_DELTA'] = float(data.iloc[0]['[ID3.SG4] OVN Total'])
                case "NQ_5":
                    variables['NQ_OVNTOIB_HI'] = float(data.iloc[0]['[ID1.SG2] OVNTOIB_HI'])
                    variables['NQ_OVNTOIB_LO'] = float(data.iloc[0]['[ID1.SG3] OVNTOIB_LO'])
                case "NQ_6":
                    variables['NQ_EURO_IBH'] = float(data.iloc[0]['[ID1.SG2] EURO IBH'])
                    variables['NQ_EURO_IBL'] = float(data.iloc[0]['[ID1.SG3] EURO IBL'])
                case "NQ_7":
                    variables['NQ_ORH'] = float(data.iloc[0]['[ID1.SG2] ORH'])
                    variables['NQ_ORL'] = float(data.iloc[0]['[ID1.SG3] ORL'])
                case "RTY_1":
                    # ------------------- Use Integer Based iLoc ----------------------- #
                    variables['RTY_RTH_VWAP'] = float(data.iloc[0]['[ID24.SG1] RTH_VWAP'])
                    variables['RTY_VWAP_SLOPE'] = float(data.iloc[0]['[ID23.SG2] Vwap_Slope'])
                    variables['RTY_DAY_OPEN'] = float(data.iloc[0]['[ID2.SG1] Day_Open'])
                    variables['RTY_DAY_HIGH'] = float(data.iloc[0]['[ID2.SG2] Day_High'])
                    variables['RTY_DAY_LOW'] = float(data.iloc[0]['[ID2.SG3] Day_Low'])
                    variables['RTY_DAY_CLOSE'] = float(data.iloc[0]['[ID2.SG4] Day_Close'])
                    variables['RTY_DAY_VPOC'] = float(data.iloc[0]['[ID1.SG1] Day_Vpoc'])
                    variables['RTY_PRIOR_VPOC'] = float(data.iloc[0]['[ID9.SG1] Prior_Vpoc'])
                    variables['RTY_PRIOR_HIGH'] = float(data.iloc[0]['[ID8.SG2] Prior_High'])
                    variables['RTY_PRIOR_LOW'] = float(data.iloc[0]['[ID8.SG3] Prior_Low'])
                    variables['RTY_PRIOR_CLOSE'] = float(data.iloc[0]['[ID8.SG4] Prior_Close'])
                    variables['RTY_RVOL'] = float(data.iloc[0]['[ID6.SG1] R_Vol'])
                    variables['RTY_CUMULATIVE_RVOL'] = float(data.iloc[0]['[ID6.SG2] R_Vol_Cumulative'])
                    variables['RTY_TOTAL_RTH_DELTA'] = float(data.iloc[0]['[ID4.SG4] Total_Delta'])
                    # ---------------------- Use Date Date Time Loc ------------------------- #
                    latest_date = data.index.max().date()
                    
                    # ----- Current Session ---- #
                    current_period_datetimes = {
                        label: datetime.combine(latest_date, period_time)
                        for label, period_time in period_equity.items()
                    }
                    for period_label, specific_datetime in current_period_datetimes.items():    
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['RTY_A_HIGH'] = float(data.loc[specific_datetime]['[ID10.SG1] A_High'])
                                    variables['RTY_A_LOW'] = float(data.loc[specific_datetime]['[ID10.SG2] A_Low'])    
                                case 'B':
                                    variables['RTY_B_HIGH'] = float(data.loc[specific_datetime]['[ID11.SG1] B_High'])
                                    variables['RTY_B_LOW'] = float(data.loc[specific_datetime]['[ID11.SG2] B_Low'])
                                case 'C':
                                    variables['RTY_C_HIGH'] = float(data.loc[specific_datetime]['[ID12.SG1] C_High'])
                                    variables['RTY_C_LOW'] = float(data.loc[specific_datetime]['[ID12.SG2] C_Low'])
                                case 'D':
                                    variables['RTY_D_HIGH'] = float(data.loc[specific_datetime]['[ID13.SG1] D_High'])
                                    variables['RTY_D_LOW'] = float(data.loc[specific_datetime]['[ID13.SG2] D_Low'])
                                case 'E':
                                    variables['RTY_E_HIGH'] = float(data.loc[specific_datetime]['[ID14.SG1] E_High'])
                                    variables['RTY_E_LOW'] = float(data.loc[specific_datetime]['[ID14.SG2] E_Low'])
                                case 'F':
                                    variables['RTY_F_HIGH'] = float(data.loc[specific_datetime]['[ID15.SG1] F_High'])
                                    variables['RTY_F_LOW'] = float(data.loc[specific_datetime]['[ID15.SG2] F_Low'])
                                case 'G':
                                    variables['RTY_G_HIGH'] = float(data.loc[specific_datetime]['[ID16.SG1] G_High'])
                                    variables['RTY_G_LOW'] = float(data.loc[specific_datetime]['[ID16.SG2] G_Low'])
                                case 'H':
                                    variables['RTY_H_HIGH'] = float(data.loc[specific_datetime]['[ID17.SG1] H_High'])
                                    variables['RTY_H_LOW'] = float(data.loc[specific_datetime]['[ID17.SG2] H_Low'])
                                case 'I':
                                    variables['RTY_I_HIGH'] = float(data.loc[specific_datetime]['[ID18.SG1] I_High'])
                                    variables['RTY_I_LOW'] = float(data.loc[specific_datetime]['[ID18.SG2] I_Low'])
                                case 'J':
                                    variables['RTY_J_HIGH'] = float(data.loc[specific_datetime]['[ID19.SG1] J_High'])
                                    variables['RTY_J_LOW'] = float(data.loc[specific_datetime]['[ID19.SG2] J_Low'])
                                case 'K':
                                    variables['RTY_K_HIGH'] = float(data.loc[specific_datetime]['[ID20.SG1] K_High'])
                                    variables['RTY_K_LOW'] = float(data.loc[specific_datetime]['[ID20.SG2] K_Low'])
                                case 'L':
                                    variables['RTY_L_HIGH'] = float(data.loc[specific_datetime]['[ID21.SG1] L_High'])
                                    variables['RTY_L_LOW'] = float(data.loc[specific_datetime]['[ID21.SG2] L_Low'])
                                case 'M':
                                    variables['RTY_M_HIGH'] = float(data.loc[specific_datetime]['[ID22.SG1] M_High'])
                                    variables['RTY_M_LOW'] = float(data.loc[specific_datetime]['[ID22.SG2] M_Low'])
                        else:
                            pass
                    # ---- Prior Session ---- #
                    previous_date = latest_date - timedelta(days=1)
                    prior_period_datetimes = {
                        label: datetime.combine(previous_date, period_time)
                        for label, period_time in period_equity.items()
                    }    
                    for period_label, specific_datetime in prior_period_datetimes.items():
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['RTY_PRIOR_A_HIGH'] = float(data.loc[specific_datetime]['[ID10.SG1] A_High'])
                                    variables['RTY_PRIOR_A_LOW'] = float(data.loc[specific_datetime]['[ID10.SG2] A_Low'])    
                                case 'B':
                                    variables['RTY_PRIOR_B_HIGH'] = float(data.loc[specific_datetime]['[ID11.SG1] B_High'])
                                    variables['RTY_PRIOR_B_LOW'] = float(data.loc[specific_datetime]['[ID11.SG2] B_Low'])
                                case 'C':
                                    variables['RTY_PRIOR_C_HIGH'] = float(data.loc[specific_datetime]['[ID12.SG1] C_High'])
                                    variables['RTY_PRIOR_C_LOW'] = float(data.loc[specific_datetime]['[ID12.SG2] C_Low'])
                                case 'D':
                                    variables['RTY_PRIOR_D_HIGH'] = float(data.loc[specific_datetime]['[ID13.SG1] D_High'])
                                    variables['RTY_PRIOR_D_LOW'] = float(data.loc[specific_datetime]['[ID13.SG2] D_Low'])
                                case 'E':
                                    variables['RTY_PRIOR_E_HIGH'] = float(data.loc[specific_datetime]['[ID14.SG1] E_High'])
                                    variables['RTY_PRIOR_E_LOW'] = float(data.loc[specific_datetime]['[ID14.SG2] E_Low'])
                                case 'F':
                                    variables['RTY_PRIOR_F_HIGH'] = float(data.loc[specific_datetime]['[ID15.SG1] F_High'])
                                    variables['RTY_PRIOR_F_LOW'] = float(data.loc[specific_datetime]['[ID15.SG2] F_Low'])
                                case 'G':
                                    variables['RTY_PRIOR_G_HIGH'] = float(data.loc[specific_datetime]['[ID16.SG1] G_High'])
                                    variables['RTY_PRIOR_G_LOW'] = float(data.loc[specific_datetime]['[ID16.SG2] G_Low'])
                                case 'H':
                                    variables['RTY_PRIOR_H_HIGH'] = float(data.loc[specific_datetime]['[ID17.SG1] H_High'])
                                    variables['RTY_PRIOR_H_LOW'] = float(data.loc[specific_datetime]['[ID17.SG2] H_Low'])
                                case 'I':
                                    variables['RTY_PRIOR_I_HIGH'] = float(data.loc[specific_datetime]['[ID18.SG1] I_High'])
                                    variables['RTY_PRIOR_I_LOW'] = float(data.loc[specific_datetime]['[ID18.SG2] I_Low'])
                                case 'J':
                                    variables['RTY_PRIOR_J_HIGH'] = float(data.loc[specific_datetime]['[ID19.SG1] J_High'])
                                    variables['RTY_PRIOR_J_LOW'] = float(data.loc[specific_datetime]['[ID19.SG2] J_Low'])
                                case 'K':
                                    variables['RTY_PRIOR_K_HIGH'] = float(data.loc[specific_datetime]['[ID20.SG1] K_High'])
                                    variables['RTY_PRIOR_K_LOW'] = float(data.loc[specific_datetime]['[ID20.SG2] K_Low'])
                                case 'L':
                                    variables['RTY_PRIOR_L_HIGH'] = float(data.loc[specific_datetime]['[ID21.SG1] L_High'])
                                    variables['RTY_PRIOR_L_LOW'] = float(data.loc[specific_datetime]['[ID21.SG2] L_Low'])
                                case 'M':
                                    variables['RTY_PRIOR_M_HIGH'] = float(data.loc[specific_datetime]['[ID22.SG1] M_High'])
                                    variables['RTY_PRIOR_M_LOW'] = float(data.loc[specific_datetime]['[ID22.SG2] M_Low'])
                        else:
                            pass 
                case "RTY_2":
                    variables['RTY_ETH_VWAP'] = float(data.iloc[0]['[ID7.SG1] ETH_VWAP'])
                    variables['RTY_ETH_TOP_1'] = float(data.iloc[0]['[ID7.SG2] Top_1'])
                    variables['RTY_ETH_BOTTOM_1'] = float(data.iloc[0]['[ID7.SG3] Bottom_1'])
                    variables['RTY_ETH_TOP_2'] = float(data.iloc[0]['[ID7.SG4] Top_2'])
                    variables['RTY_ETH_BOTTOM_2'] = float(data.iloc[0]['[ID7.SG5] Bottom_2'])
                    variables['RTY_CPL'] = float(data.iloc[0]['[ID2.SG1] CPL'])
                    variables['RTY_5D_VPOC'] = float(data.iloc[0]['[ID4.SG2] 5DVPOC'])
                    variables['RTY_20D_VPOC'] = float(data.iloc[0]['[ID3.SG2] 20DVPOC'])
                    variables['RTY_P_WOPEN'] = float(data.iloc[0]['[ID5.SG1] P_WOPEN'])
                    variables['RTY_P_WHIGH'] = float(data.iloc[0]['[ID5.SG2] P_WHIGH'])
                    variables['RTY_P_WLO'] = float(data.iloc[0]['[ID5.SG3] P_WLO'])
                    variables['RTY_P_WCLOSE'] = float(data.iloc[0]['[ID5.SG4] P_WCLOSE'])
                    variables['RTY_P_WVPOC'] = float(data.iloc[0]['[ID11.SG1] P_WVPOC'])
                    variables['RTY_WVWAP'] = float(data.iloc[0]['[ID10.SG1] WVWAP'])
                    variables['RTY_P_MOPEN'] = float(data.iloc[0]['[ID8.SG1] P_MOPEN'])
                    variables['RTY_P_MHIGH'] = float(data.iloc[0]['[ID8.SG2] P_MHIGH'])
                    variables['RTY_P_MLO'] = float(data.iloc[0]['[ID8.SG3] P_MLO'])
                    variables['RTY_P_MCLOSE'] = float(data.iloc[0]['[ID8.SG4] P_MCLOSE'])
                    variables['RTY_P_MVPOC'] = float(data.iloc[0]['[ID12.SG1] P_MVPOC'])
                    variables['RTY_MVWAP'] = float(data.iloc[0]['[ID1.SG1] MVWAP'])
                    # ----------------- Period-based ETH VWAP Extraction ----------------- #
                    latest_date = data.index.max().date()
                    
                    for period_label, period_time in period_equity.items():
                        specific_datetime = datetime.combine(latest_date, period_time)
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['RTY_ETH_VWAP_A'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_A'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_A'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                    
                                case 'B':
                                    variables['RTY_ETH_VWAP_B'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_B'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_B'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'C':
                                    variables['RTY_ETH_VWAP_C'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_C'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_C'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'D':
                                    variables['RTY_ETH_VWAP_C'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_C'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_C'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'E':
                                    variables['RTY_ETH_VWAP_E'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_E'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_E'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'F':
                                    variables['RTY_ETH_VWAP_F'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_F'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_F'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'G':
                                    variables['RTY_ETH_VWAP_G'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_G'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_G'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'H':
                                    variables['RTY_ETH_VWAP_H'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_H'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_H'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'I':
                                    variables['RTY_ETH_VWAP_I'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_I'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_I'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'J':
                                    variables['RTY_ETH_VWAP_J'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_J'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_J'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'K':
                                    variables['RTY_ETH_VWAP_K'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_K'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_K'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'L':
                                    variables['RTY_ETH_VWAP_L'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_L'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_L'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'M':
                                    variables['RTY_ETH_VWAP_M'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['RTY_ETH_TOP_1_M'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['RTY_ETH_BOTTOM_1_M'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])   
                        else:
                            pass
                case "RTY_3":
                    variables['RTY_IB_ATR'] = float(data.iloc[1]['[ID2.SG1] IB ATR'])
                    variables['RTY_IB_HIGH'] = float(data.iloc[0]['[ID1.SG2] IBH'])
                    variables['RTY_IB_LOW'] = float(data.iloc[0]['[ID1.SG3] IBL'])
                    variables['RTY_PRIOR_IB_HIGH'] = float(data.iloc[1]['[ID1.SG2] IBH'])
                    variables['RTY_PRIOR_IB_LOW'] = float(data.iloc[1]['[ID1.SG3] IBL'])
                case "RTY_4":
                    variables['RTY_OVNH'] = float(data.iloc[0]['[ID1.SG2] OVN H'])
                    variables['RTY_OVNL'] = float(data.iloc[0]['[ID1.SG3] OVN L'])
                    variables['RTY_TOTAL_OVN_DELTA'] = float(data.iloc[0]['[ID3.SG4] OVN Total'])
                case "RTY_5":
                    variables['RTY_OVNTOIB_HI'] = float(data.iloc[0]['[ID1.SG2] OVNTOIB_HI'])
                    variables['RTY_OVNTOIB_LO'] = float(data.iloc[0]['[ID1.SG3] OVNTOIB_LO'])
                case "RTY_6":
                    variables['RTY_EURO_IBH'] = float(data.iloc[0]['[ID1.SG2] EURO IBH'])
                    variables['RTY_EURO_IBL'] = float(data.iloc[0]['[ID1.SG3] EURO IBL'])
                case "RTY_7":
                    variables['RTY_ORH'] = float(data.iloc[0]['[ID1.SG2] ORH'])
                    variables['RTY_ORL'] = float(data.iloc[0]['[ID1.SG3] ORL'])
                case "CL_1":
                    # ------------------- Use Integer Based iLoc ----------------------- #
                    variables['CL_RTH_VWAP'] = float(data.iloc[0]['[ID22.SG1] RTH_VWAP'])
                    variables['CL_VWAP_SLOPE'] = float(data.iloc[0]['[ID21.SG2] Vwap_Slope'])
                    variables['CL_DAY_OPEN'] = float(data.iloc[0]['[ID2.SG1] Day_Open'])
                    variables['CL_DAY_HIGH'] = float(data.iloc[0]['[ID2.SG2] Day_High'])
                    variables['CL_DAY_LOW'] = float(data.iloc[0]['[ID2.SG3] Day_Low'])
                    variables['CL_DAY_CLOSE'] = float(data.iloc[0]['[ID2.SG4] Day_Close'])
                    variables['CL_DAY_VPOC'] = float(data.iloc[0]['[ID1.SG1] Day_Vpoc'])
                    variables['CL_PRIOR_VPOC'] = float(data.iloc[0]['[ID9.SG1] Prior_Vpoc'])
                    variables['CL_PRIOR_HIGH'] = float(data.iloc[0]['[ID8.SG2] Prior_High'])
                    variables['CL_PRIOR_LOW'] = float(data.iloc[0]['[ID8.SG3] Prior_Low'])
                    variables['CL_PRIOR_CLOSE'] = float(data.iloc[0]['[ID8.SG4] Prior_Close'])
                    variables['CL_RVOL'] = float(data.iloc[0]['[ID6.SG1] R_Vol'])
                    variables['CL_CUMULATIVE_RVOL'] = float(data.iloc[0]['[ID6.SG2] R_Vol_Cumulative'])
                    variables['CL_TOTAL_RTH_DELTA'] = float(data.iloc[0]['[ID4.SG4] Total_Delta'])
                    # ---------------------- Use Date Date Time Loc ------------------------- #
                    latest_date = data.index.max().date()
                    
                    # ----- Current Session ---- #
                    current_period_datetimes = {
                        label: datetime.combine(latest_date, period_time)
                        for label, period_time in period_crude.items()
                    }
                    for period_label, specific_datetime in current_period_datetimes.items():    
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['CL_A_HIGH'] = float(data.loc[specific_datetime]['[ID10.SG1] A_High'])
                                    variables['CL_A_LOW'] = float(data.loc[specific_datetime]['[ID10.SG2] A_Low'])    
                                case 'B':
                                    variables['CL_B_HIGH'] = float(data.loc[specific_datetime]['[ID11.SG1] B_High'])
                                    variables['CL_B_LOW'] = float(data.loc[specific_datetime]['[ID11.SG2] B_Low'])
                                case 'C':
                                    variables['CL_C_HIGH'] = float(data.loc[specific_datetime]['[ID12.SG1] C_High'])
                                    variables['CL_C_LOW'] = float(data.loc[specific_datetime]['[ID12.SG2] C_Low'])
                                case 'D':
                                    variables['CL_D_HIGH'] = float(data.loc[specific_datetime]['[ID13.SG1] D_High'])
                                    variables['CL_D_LOW'] = float(data.loc[specific_datetime]['[ID13.SG2] D_Low'])
                                case 'E':
                                    variables['CL_E_HIGH'] = float(data.loc[specific_datetime]['[ID14.SG1] E_High'])
                                    variables['CL_E_LOW'] = float(data.loc[specific_datetime]['[ID14.SG2] E_Low'])
                                case 'F':
                                    variables['CL_F_HIGH'] = float(data.loc[specific_datetime]['[ID15.SG1] F_High'])
                                    variables['CL_F_LOW'] = float(data.loc[specific_datetime]['[ID15.SG2] F_Low'])
                                case 'G':
                                    variables['CL_G_HIGH'] = float(data.loc[specific_datetime]['[ID16.SG1] G_High'])
                                    variables['CL_G_LOW'] = float(data.loc[specific_datetime]['[ID16.SG2] G_Low'])
                                case 'H':
                                    variables['CL_H_HIGH'] = float(data.loc[specific_datetime]['[ID17.SG1] H_High'])
                                    variables['CL_H_LOW'] = float(data.loc[specific_datetime]['[ID17.SG2] H_Low'])
                                case 'I':
                                    variables['CL_I_HIGH'] = float(data.loc[specific_datetime]['[ID18.SG1] I_High'])
                                    variables['CL_I_LOW'] = float(data.loc[specific_datetime]['[ID18.SG2] I_Low'])
                                case 'J':
                                    variables['CL_J_HIGH'] = float(data.loc[specific_datetime]['[ID19.SG1] J_High'])
                                    variables['CL_J_LOW'] = float(data.loc[specific_datetime]['[ID19.SG2] J_Low'])
                                case 'K':
                                    variables['CL_K_HIGH'] = float(data.loc[specific_datetime]['[ID20.SG1] K_High'])
                                    variables['CL_K_LOW'] = float(data.loc[specific_datetime]['[ID20.SG2] K_Low'])
                        else:
                            pass
                    # ---- Prior Session ---- #
                    previous_date = latest_date - timedelta(days=1)
                    prior_period_datetimes = {
                        label: datetime.combine(previous_date, period_time)
                        for label, period_time in period_crude.items()
                    }    
                    for period_label, specific_datetime in prior_period_datetimes.items():
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['CL_PRIOR_A_HIGH'] = float(data.loc[specific_datetime]['[ID10.SG1] A_High'])
                                    variables['CL_PRIOR_A_LOW'] = float(data.loc[specific_datetime]['[ID10.SG2] A_Low'])    
                                case 'B':
                                    variables['CL_PRIOR_B_HIGH'] = float(data.loc[specific_datetime]['[ID11.SG1] B_High'])
                                    variables['CL_PRIOR_B_LOW'] = float(data.loc[specific_datetime]['[ID11.SG2] B_Low'])
                                case 'C':
                                    variables['CL_PRIOR_C_HIGH'] = float(data.loc[specific_datetime]['[ID12.SG1] C_High'])
                                    variables['CL_PRIOR_C_LOW'] = float(data.loc[specific_datetime]['[ID12.SG2] C_Low'])
                                case 'D':
                                    variables['CL_PRIOR_D_HIGH'] = float(data.loc[specific_datetime]['[ID13.SG1] D_High'])
                                    variables['CL_PRIOR_D_LOW'] = float(data.loc[specific_datetime]['[ID13.SG2] D_Low'])
                                case 'E':
                                    variables['CL_PRIOR_E_HIGH'] = float(data.loc[specific_datetime]['[ID14.SG1] E_High'])
                                    variables['CL_PRIOR_E_LOW'] = float(data.loc[specific_datetime]['[ID14.SG2] E_Low'])
                                case 'F':
                                    variables['CL_PRIOR_F_HIGH'] = float(data.loc[specific_datetime]['[ID15.SG1] F_High'])
                                    variables['CL_PRIOR_F_LOW'] = float(data.loc[specific_datetime]['[ID15.SG2] F_Low'])
                                case 'G':
                                    variables['CL_PRIOR_G_HIGH'] = float(data.loc[specific_datetime]['[ID16.SG1] G_High'])
                                    variables['CL_PRIOR_G_LOW'] = float(data.loc[specific_datetime]['[ID16.SG2] G_Low'])
                                case 'H':
                                    variables['CL_PRIOR_H_HIGH'] = float(data.loc[specific_datetime]['[ID17.SG1] H_High'])
                                    variables['CL_PRIOR_H_LOW'] = float(data.loc[specific_datetime]['[ID17.SG2] H_Low'])
                                case 'I':
                                    variables['CL_PRIOR_I_HIGH'] = float(data.loc[specific_datetime]['[ID18.SG1] I_High'])
                                    variables['CL_PRIOR_I_LOW'] = float(data.loc[specific_datetime]['[ID18.SG2] I_Low'])
                                case 'J':
                                    variables['CL_PRIOR_J_HIGH'] = float(data.loc[specific_datetime]['[ID19.SG1] J_High'])
                                    variables['CL_PRIOR_J_LOW'] = float(data.loc[specific_datetime]['[ID19.SG2] J_Low'])
                                case 'K':
                                    variables['CL_PRIOR_K_HIGH'] = float(data.loc[specific_datetime]['[ID20.SG1] K_High'])
                                    variables['CL_PRIOR_K_LOW'] = float(data.loc[specific_datetime]['[ID20.SG2] K_Low'])
                        else:
                            pass 
                case "CL_2":
                    variables['CL_ETH_VWAP'] = float(data.iloc[0]['[ID7.SG1] ETH_VWAP'])
                    variables['CL_ETH_TOP_1'] = float(data.iloc[0]['[ID7.SG2] Top_1'])
                    variables['CL_ETH_BOTTOM_1'] = float(data.iloc[0]['[ID7.SG3] Bottom_1'])
                    variables['CL_ETH_TOP_2'] = float(data.iloc[0]['[ID7.SG4] Top_2'])
                    variables['CL_ETH_BOTTOM_2'] = float(data.iloc[0]['[ID7.SG5] Bottom_2'])
                    variables['CL_CPL'] = float(data.iloc[0]['[ID2.SG1] CPL'])
                    variables['CL_5D_VPOC'] = float(data.iloc[0]['[ID4.SG2] 5DVPOC'])
                    variables['CL_20D_VPOC'] = float(data.iloc[0]['[ID3.SG2] 20DVPOC'])
                    variables['CL_P_WOPEN'] = float(data.iloc[0]['[ID5.SG1] P_WOPEN'])
                    variables['CL_P_WHIGH'] = float(data.iloc[0]['[ID5.SG2] P_WHIGH'])
                    variables['CL_P_WLO'] = float(data.iloc[0]['[ID5.SG3] P_WLO'])
                    variables['CL_P_WCLOSE'] = float(data.iloc[0]['[ID5.SG4] P_WCLOSE'])
                    variables['CL_P_WVPOC'] = float(data.iloc[0]['[ID11.SG1] P_WVPOC'])
                    variables['CL_WVWAP'] = float(data.iloc[0]['[ID10.SG1] WVWAP'])
                    variables['CL_P_MOPEN'] = float(data.iloc[0]['[ID8.SG1] P_MOPEN'])
                    variables['CL_P_MHIGH'] = float(data.iloc[0]['[ID8.SG2] P_MHIGH'])
                    variables['CL_P_MLO'] = float(data.iloc[0]['[ID8.SG3] P_MLO'])
                    variables['CL_P_MCLOSE'] = float(data.iloc[0]['[ID8.SG4] P_MCLOSE'])
                    variables['CL_P_MVPOC'] = float(data.iloc[0]['[ID12.SG1] P_MVPOC'])
                    variables['CL_MVWAP'] = float(data.iloc[0]['[ID1.SG1] MVWAP'])
                    # ----------------- Period-based ETH VWAP Extraction ----------------- #
                    latest_date = data.index.max().date()
                    
                    for period_label, period_time in period_crude.items():
                        specific_datetime = datetime.combine(latest_date, period_time)
                        if specific_datetime in data.index:
                            match period_label:
                                case 'A':
                                    variables['CL_ETH_VWAP_A'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_A'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_A'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                    
                                case 'B':
                                    variables['CL_ETH_VWAP_B'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_B'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_B'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'C':
                                    variables['CL_ETH_VWAP_C'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_C'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_C'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'D':
                                    variables['CL_ETH_VWAP_C'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_C'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_C'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'E':
                                    variables['CL_ETH_VWAP_E'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_E'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_E'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'F':
                                    variables['CL_ETH_VWAP_F'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_F'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_F'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'G':
                                    variables['CL_ETH_VWAP_G'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_G'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_G'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'H':
                                    variables['CL_ETH_VWAP_H'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_H'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_H'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'I':
                                    variables['CL_ETH_VWAP_I'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_I'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_I'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'J':
                                    variables['CL_ETH_VWAP_J'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_J'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_J'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                                case 'K':
                                    variables['CL_ETH_VWAP_K'] = float(data.loc[specific_datetime]['[ID7.SG1] ETH_VWAP'])
                                    variables['CL_ETH_TOP_1_K'] = float(data.loc[specific_datetime]['[ID7.SG2] Top_1'])
                                    variables['CL_ETH_BOTTOM_1_K'] = float(data.loc[specific_datetime]['[ID7.SG3] Bottom_1'])                                       
                        else:
                            pass
                case "CL_3":
                    variables['CL_IB_ATR'] = float(data.iloc[1]['[ID2.SG1] IB ATR'])
                    variables['CL_IB_HIGH'] = float(data.iloc[0]['[ID1.SG2] IBH'])
                    variables['CL_IB_LOW'] = float(data.iloc[0]['[ID1.SG3] IBL'])
                    variables['CL_PRIOR_IB_HIGH'] = float(data.iloc[1]['[ID1.SG2] IBH'])
                    variables['CL_PRIOR_IB_LOW'] = float(data.iloc[1]['[ID1.SG3] IBL'])                
                case "CL_4":
                    variables['CL_OVNH'] = float(data.iloc[0]['[ID1.SG2] OVN H'])
                    variables['CL_OVNL'] = float(data.iloc[0]['[ID1.SG3] OVN L'])
                    variables['CL_TOTAL_OVN_DELTA'] = float(data.iloc[0]['[ID3.SG4] OVN Total'])
                
                case "CL_5":
                    variables['CL_OVNTOIB_HI'] = float(data.iloc[0]['[ID1.SG2] OVNTOIB_HI'])
                    variables['CL_OVNTOIB_LO'] = float(data.iloc[0]['[ID1.SG3] OVNTOIB_LO'])
                
                case "CL_6":
                    variables['CL_EURO_IBH'] = float(data.iloc[0]['[ID1.SG2] EURO IBH'])
                    variables['CL_EURO_IBL'] = float(data.iloc[0]['[ID1.SG3] EURO IBL'])

                case "CL_7":
                    variables['CL_ORH'] = float(data.iloc[0]['[ID1.SG2] ORH'])
                    variables['CL_ORL'] = float(data.iloc[0]['[ID1.SG3] ORL'])
                
                case other:
                    logger.error(" Startup | prep_data | Note: No Such Switch Location")
                   
            product_name = task["name"].split('_')[0]
            if product_name not in all_variables:
                all_variables[product_name] = {}

            all_variables[product_name].update(variables)  
        logger.debug(f" Startup | prep_data | Product: {product_name} | Variables: {all_variables}")
        return all_variables 