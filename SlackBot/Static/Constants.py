from datetime import time as datetime_time
from SlackBot.Slack_Alerts.Conditional.Pvat import PVAT
from SlackBot.Slack_Alerts.Conditional.PreIB import PRE_IB_BIAS
from SlackBot.Slack_Alerts.Conditional.Posture import POSTURE
from SlackBot.Slack_Alerts.Conditional.Neutral import NEUTRAL

external_impvol = [
    {"sheet_name": "ES_Data", "sheet_id": "1miVoDpHI40Nff7PZB5QVKAGaB-QaGEJzijo8uf2wtCU", "row_number": 17, "col_number": 130},
    {"sheet_name": "NQ_Data", "sheet_id": "1sypXFWOHl5-wBihCBSLDMv0Z-wYUoU-QoUXXfKfqB7Y", "row_number": 17, "col_number": 130},
    {"sheet_name": "RTY_Data", "sheet_id": "1G-gnb5ZYEnQdd9nJyraguPhlnLYMA09Cpz9EH-_8nkM", "row_number": 17, "col_number": 130},
    {"sheet_name": "CL_Data", "sheet_id": "1SFfvZyBj5XvCuzx8bodqQ29yWtuIoTrPqmmCBaHGRzY", "row_number": 17, "col_number": 130}
] 
external_bias = [
    {"sheet_name": "ES_PREP", "sheet_id": "1miVoDpHI40Nff7PZB5QVKAGaB-QaGEJzijo8uf2wtCU", "row_number": 52, "col_number": 3},
    {"sheet_name": "NQ_PREP", "sheet_id": "1sypXFWOHl5-wBihCBSLDMv0Z-wYUoU-QoUXXfKfqB7Y", "row_number": 52, "col_number": 3},
    {"sheet_name": "RTY_PREP", "sheet_id": "1G-gnb5ZYEnQdd9nJyraguPhlnLYMA09Cpz9EH-_8nkM", "row_number": 52, "col_number": 3},
    {"sheet_name": "CL_PREP", "sheet_id": "1SFfvZyBj5XvCuzx8bodqQ29yWtuIoTrPqmmCBaHGRzY", "row_number": 52, "col_number": 3}
]
conditions = [
    {
        "name": "PVAT_ES",
        "required_files": ["ES_1","ES_2","ES_3","ES_4","ES_6","ES_7"],
        "start_time": datetime_time(9, 32),
        "end_time": datetime_time(10, 30),
    },
    {
        "name": "PVAT_NQ",
        "required_files": ["NQ_1","NQ_2","NQ_3","NQ_4","NQ_6","NQ_7"],
        "start_time": datetime_time(9, 32),
        "end_time": datetime_time(10, 30),
    },
    {
        "name": "PVAT_RTY",
        "required_files": ["RTY_1","RTY_2","RTY_3","RTY_4","RTY_6","RTY_7"],
        "start_time": datetime_time(9, 32),
        "end_time": datetime_time(10, 30),
    },
    {
        "name": "PVAT_CL",
        "required_files": ["CL_1","CL_2","CL_3","CL_4","CL_6","CL_7"],
        "start_time": datetime_time(9, 2),
        "end_time": datetime_time(10, 0),
    },
    {
        "name": "PREIB_ES",
        "required_files": ["ES_2"],
        "start_time": datetime_time(9, 30),
        "end_time": datetime_time(16, 0),
    },
    {
        "name": "PREIB_NQ",
        "required_files": ["NQ_2"],
        "start_time": datetime_time(9, 30),
        "end_time": datetime_time(16, 0),
    },
    {
        "name": "PREIB_RTY",
        "required_files": ["RTY_2"],
        "start_time": datetime_time(9, 30),
        "end_time": datetime_time(16, 0),
    },
    {
        "name": "PREIB_CL",
        "required_files": ["CL_2"],
        "start_time": datetime_time(9, 0), 
        "end_time": datetime_time(14, 30),
    },  
    {
        "name": "POSTURE_ES",
        "required_files": ["ES_1","ES_2"],
        "start_time": datetime_time(9, 30),
        "end_time": datetime_time(16, 0),
    },
    {
        "name": "POSTURE_NQ",
        "required_files": ["NQ_1","NQ_2"],
        "start_time": datetime_time(9, 30),
        "end_time": datetime_time(16, 0),
    },
    {
        "name": "POSTURE_RTY",
        "required_files": ["RTY_1","RTY_2"],
        "start_time": datetime_time(9, 30),
        "end_time": datetime_time(16, 0),
    },
    {
        "name": "POSTURE_CL",
        "required_files": ["CL_1","CL_2"],
        "start_time": datetime_time(9, 0), 
        "end_time": datetime_time(14, 30),
    },   
    {
        "name": "NEUTRAL_ES",
        "required_files": ["CL_1","CL_2"],
        "start_time": datetime_time(10, 30), 
        "end_time": datetime_time(16, 0),
    },   
    {
        "name": "NEUTRAL_NQ",
        "required_files": ["CL_1","CL_2"],
        "start_time": datetime_time(10, 30), 
        "end_time": datetime_time(16, 0),
    },   
    {
        "name": "NEUTRAL_RTY",
        "required_files": ["CL_1","CL_2"],
        "start_time": datetime_time(10, 30), 
        "end_time": datetime_time(16, 0),
    },   
    {
        "name": "NEUTRAL_CL",
        "required_files": ["CL_1","CL_2"],
        "start_time": datetime_time(10, 0), 
        "end_time": datetime_time(14, 30),
    }, 
    {
        "name": "OVERNIGHT_ES",
        "required_files": ["CL_1","CL_2"],
        "start_time": datetime_time(10, 30), 
        "end_time": datetime_time(16, 0),
    },   
    {
        "name": "OVERNIGHT_NQ",
        "required_files": ["CL_1","CL_2"],
        "start_time": datetime_time(10, 30), 
        "end_time": datetime_time(16, 0),
    },   
    {
        "name": "OVERNIGHT_RTY",
        "required_files": ["CL_1","CL_2"],
        "start_time": datetime_time(10, 30), 
        "end_time": datetime_time(16, 0),
    },   
    {
        "name": "OVERNIGHT_CL",
        "required_files": ["CL_1","CL_2"],
        "start_time": datetime_time(10, 0), 
        "end_time": datetime_time(14, 30),
    },               
]
condition_functions = {
    "PVAT": PVAT,
    "PREIB": PRE_IB_BIAS,
    "POSTURE": POSTURE,
    "NEUTRAL": NEUTRAL,
}
es_1 = [
    '[ID2.SG1] Day_Open', '[ID2.SG2] Day_High', '[ID2.SG3] Day_Low', 
    '[ID2.SG4] Day_Close', '[ID1.SG1] Day_Vpoc', '[ID9.SG1] Prior_Vpoc', '[ID8.SG2] Prior_High', '[ID8.SG3] Prior_Low', '[ID8.SG4] Prior_Close',
    '[ID6.SG1] R_Vol', '[ID6.SG2] R_Vol_Cumulative', '[ID4.SG4] Total_Delta', 
    '[ID3.SG1] IB ATR','[ID10.SG1] A_High','[ID10.SG2] A_Low', '[ID11.SG1] B_High','[ID11.SG2] B_Low',
    '[ID12.SG1] C_High', '[ID12.SG2] C_Low', '[ID13.SG1] D_High', '[ID13.SG2] D_Low', '[ID14.SG1] E_High',
    '[ID14.SG2] E_Low', '[ID15.SG1] F_High', '[ID15.SG2] F_Low', '[ID16.SG1] G_High', '[ID16.SG2] G_Low',
    '[ID17.SG1] H_High', '[ID17.SG2] H_Low', '[ID18.SG1] I_High', '[ID18.SG2] I_Low', '[ID19.SG1] J_High',
    '[ID19.SG2] J_Low', '[ID20.SG1] K_High', '[ID20.SG2] K_Low', '[ID21.SG1] L_High', '[ID21.SG2] L_Low',
    '[ID22.SG1] M_High', '[ID22.SG2] M_Low'
]
es_2 = [
    '[ID2.SG1] CPL', '[ID4.SG2] 5DVPOC', '[ID3.SG2] 20DVPOC', 
    '[ID5.SG1] P_WOPEN','[ID5.SG2] P_WHIGH','[ID5.SG3] P_WLO', '[ID5.SG4] P_WCLOSE', '[ID11.SG1] P_WVPOC', 
    '[ID10.SG1] WVWAP', '[ID8.SG1] P_MOPEN', '[ID8.SG2] P_MHIGH', '[ID8.SG3] P_MLO', 
    '[ID8.SG4] P_MCLOSE', '[ID12.SG1] P_MVPOC', '[ID1.SG1] MVWAP', '[ID7.SG1] ETH_VWAP', 
    '[ID7.SG2] Top_1','[ID7.SG3] Bottom_1','[ID7.SG4] Top_2','[ID7.SG5] Bottom_2'
]
es_3 = [
    '[ID2.SG1] IB ATR', 
    '[ID1.SG2] IBH', '[ID1.SG3] IBL'
]
es_4 = [
    '[ID1.SG2] OVN H', 
    '[ID1.SG3] OVN L','[ID3.SG4] OVN Total'
]
es_5 = [
    '[ID1.SG2] OVNTOIB_HI', 
    '[ID1.SG3] OVNTOIB_LO'
]
es_6 = [
    '[ID1.SG2] EURO IBH', 
    '[ID1.SG3] EURO IBL'
]
es_7 = [
    '[ID1.SG2] ORH','[ID1.SG3] ORL',
]
nq_1 = [
    '[ID2.SG1] Day_Open', '[ID2.SG2] Day_High', '[ID2.SG3] Day_Low', 
    '[ID2.SG4] Day_Close', '[ID1.SG1] Day_Vpoc', '[ID9.SG1] Prior_Vpoc', '[ID8.SG2] Prior_High', '[ID8.SG3] Prior_Low', '[ID8.SG4] Prior_Close',
    '[ID6.SG1] R_Vol', '[ID6.SG2] R_Vol_Cumulative', '[ID4.SG4] Total_Delta', 
    '[ID3.SG1] IB ATR','[ID10.SG1] A_High','[ID10.SG2] A_Low', '[ID11.SG1] B_High','[ID11.SG2] B_Low',
    '[ID12.SG1] C_High', '[ID12.SG2] C_Low', '[ID13.SG1] D_High', '[ID13.SG2] D_Low', '[ID14.SG1] E_High',
    '[ID14.SG2] E_Low', '[ID15.SG1] F_High', '[ID15.SG2] F_Low', '[ID16.SG1] G_High', '[ID16.SG2] G_Low',
    '[ID17.SG1] H_High', '[ID17.SG2] H_Low', '[ID18.SG1] I_High', '[ID18.SG2] I_Low', '[ID19.SG1] J_High',
    '[ID19.SG2] J_Low', '[ID20.SG1] K_High', '[ID20.SG2] K_Low', '[ID21.SG1] L_High', '[ID21.SG2] L_Low',
    '[ID22.SG1] M_High', '[ID22.SG2] M_Low'
]
nq_2 = [
    '[ID2.SG1] CPL', '[ID4.SG2] 5DVPOC', '[ID3.SG2] 20DVPOC', 
    '[ID5.SG1] P_WOPEN','[ID5.SG2] P_WHIGH','[ID5.SG3] P_WLO', '[ID5.SG4] P_WCLOSE', '[ID11.SG1] P_WVPOC', 
    '[ID10.SG1] WVWAP', '[ID8.SG1] P_MOPEN', '[ID8.SG2] P_MHIGH', '[ID8.SG3] P_MLO', 
    '[ID8.SG4] P_MCLOSE', '[ID12.SG1] P_MVPOC', '[ID1.SG1] MVWAP', '[ID7.SG1] ETH_VWAP', 
    '[ID7.SG2] Top_1','[ID7.SG3] Bottom_1','[ID7.SG4] Top_2','[ID7.SG5] Bottom_2'
]
nq_3 = [
    '[ID2.SG1] IB ATR', 
    '[ID1.SG2] IBH', '[ID1.SG3] IBL'
]
nq_4 = [
    '[ID1.SG2] OVN H', 
    '[ID1.SG3] OVN L','[ID3.SG4] OVN Total'
]
nq_5 = [
    '[ID1.SG2] OVNTOIB_HI', 
    '[ID1.SG3] OVNTOIB_LO'
]
nq_6 = [
    '[ID1.SG2] EURO IBH', 
    '[ID1.SG3] EURO IBL'
]
nq_7 = [
    '[ID1.SG2] ORH','[ID1.SG3] ORL',
]
rty_1 = [
    '[ID2.SG1] Day_Open', '[ID2.SG2] Day_High', '[ID2.SG3] Day_Low', 
    '[ID2.SG4] Day_Close', '[ID1.SG1] Day_Vpoc', '[ID9.SG1] Prior_Vpoc', '[ID8.SG2] Prior_High', '[ID8.SG3] Prior_Low', '[ID8.SG4] Prior_Close',
    '[ID6.SG1] R_Vol', '[ID6.SG2] R_Vol_Cumulative', '[ID4.SG4] Total_Delta', 
    '[ID3.SG1] IB ATR','[ID10.SG1] A_High','[ID10.SG2] A_Low', '[ID11.SG1] B_High','[ID11.SG2] B_Low',
    '[ID12.SG1] C_High', '[ID12.SG2] C_Low', '[ID13.SG1] D_High', '[ID13.SG2] D_Low', '[ID14.SG1] E_High',
    '[ID14.SG2] E_Low', '[ID15.SG1] F_High', '[ID15.SG2] F_Low', '[ID16.SG1] G_High', '[ID16.SG2] G_Low',
    '[ID17.SG1] H_High', '[ID17.SG2] H_Low', '[ID18.SG1] I_High', '[ID18.SG2] I_Low', '[ID19.SG1] J_High',
    '[ID19.SG2] J_Low', '[ID20.SG1] K_High', '[ID20.SG2] K_Low', '[ID21.SG1] L_High', '[ID21.SG2] L_Low',
    '[ID22.SG1] M_High', '[ID22.SG2] M_Low'
]
rty_2 = [
    '[ID2.SG1] CPL', '[ID4.SG2] 5DVPOC', '[ID3.SG2] 20DVPOC', 
    '[ID5.SG1] P_WOPEN','[ID5.SG2] P_WHIGH','[ID5.SG3] P_WLO', '[ID5.SG4] P_WCLOSE', '[ID11.SG1] P_WVPOC', 
    '[ID10.SG1] WVWAP', '[ID8.SG1] P_MOPEN', '[ID8.SG2] P_MHIGH', '[ID8.SG3] P_MLO', 
    '[ID8.SG4] P_MCLOSE', '[ID12.SG1] P_MVPOC', '[ID1.SG1] MVWAP', '[ID7.SG1] ETH_VWAP', 
    '[ID7.SG2] Top_1','[ID7.SG3] Bottom_1','[ID7.SG4] Top_2','[ID7.SG5] Bottom_2'
]
rty_3 = [
    '[ID2.SG1] IB ATR', 
    '[ID1.SG2] IBH', '[ID1.SG3] IBL'
]
rty_4 = [
    '[ID1.SG2] OVN H', 
    '[ID1.SG3] OVN L', '[ID3.SG4] OVN Total'
]
rty_5 = [
    '[ID1.SG2] OVNTOIB_HI', 
    '[ID1.SG3] OVNTOIB_LO'
]
rty_6 = [
    '[ID1.SG2] EURO IBH', 
    '[ID1.SG3] EURO IBL'
]
rty_7 = [
    '[ID1.SG2] ORH','[ID1.SG3] ORL',
]
cl_1 = [
    '[ID2.SG1] Day_Open', '[ID2.SG2] Day_High', '[ID2.SG3] Day_Low', 
    '[ID2.SG4] Day_Close', '[ID1.SG1] Day_Vpoc', '[ID9.SG1] Prior_Vpoc', '[ID8.SG2] Prior_High', '[ID8.SG3] Prior_Low', '[ID8.SG4] Prior_Close',
    '[ID6.SG1] R_Vol', '[ID6.SG2] R_Vol_Cumulative', '[ID4.SG4] Total_Delta', 
    '[ID3.SG1] IB ATR','[ID10.SG1] A_High','[ID10.SG2] A_Low', '[ID11.SG1] B_High','[ID11.SG2] B_Low',
    '[ID12.SG1] C_High', '[ID12.SG2] C_Low', '[ID13.SG1] D_High', '[ID13.SG2] D_Low', '[ID14.SG1] E_High',
    '[ID14.SG2] E_Low', '[ID15.SG1] F_High', '[ID15.SG2] F_Low', '[ID16.SG1] G_High', '[ID16.SG2] G_Low',
    '[ID17.SG1] H_High', '[ID17.SG2] H_Low', '[ID18.SG1] I_High', '[ID18.SG2] I_Low', '[ID19.SG1] J_High',
    '[ID19.SG2] J_Low', '[ID20.SG1] K_High', '[ID20.SG2] K_Low'
]
cl_2 = [
    '[ID2.SG1] CPL', '[ID4.SG2] 5DVPOC', '[ID3.SG2] 20DVPOC', 
    '[ID5.SG1] P_WOPEN','[ID5.SG2] P_WHIGH','[ID5.SG3] P_WLO', '[ID5.SG4] P_WCLOSE', '[ID11.SG1] P_WVPOC', 
    '[ID10.SG1] WVWAP', '[ID8.SG1] P_MOPEN', '[ID8.SG2] P_MHIGH', '[ID8.SG3] P_MLO', 
    '[ID8.SG4] P_MCLOSE', '[ID12.SG1] P_MVPOC', '[ID1.SG1] MVWAP', '[ID7.SG1] ETH_VWAP', 
    '[ID7.SG2] Top_1','[ID7.SG3] Bottom_1','[ID7.SG4] Top_2','[ID7.SG5] Bottom_2'
]
cl_3 = [
    '[ID2.SG1] IB ATR', 
    '[ID1.SG2] IBH', '[ID1.SG3] IBL'
]
cl_4 = [
    '[ID1.SG2] OVN H', 
    '[ID1.SG3] OVN L', '[ID3.SG4] OVN Total'
]
cl_5 = [
    '[ID1.SG2] OVNTOIB_HI', 
    '[ID1.SG3] OVNTOIB_LO'
]
cl_6 = [
    '[ID1.SG2] EURO IBH', 
    '[ID1.SG3] EURO IBL'
]
cl_7 = [
    '[ID1.SG2] ORH','[ID1.SG3] ORL',
]
columns_to_drop = [
    "[ID0.SG1] Open", "[ID0.SG2] High", "[ID0.SG3] Low", "[ID0.SG4] Last", 
    "[ID0.SG5] Volume", "[ID0.SG6] # of Trades", "Data_1", "Data_2", 
    "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]

files = [
    {"name": "ES_1", "filepath": "c:/SierraChart/Data/StreamDataES_1.tsv", "columns": es_1, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "ES_2", "filepath": "c:/SierraChart/Data/StreamDataES_2.tsv", "columns": es_2, "iloc1": 1, "iloc2": 2, "header_row": 1},
    {"name": "ES_3", "filepath": "c:/SierraChart/Data/StreamDataES_3.tsv", "columns": es_3, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "ES_4", "filepath": "c:/SierraChart/Data/StreamDataES_4.tsv", "columns": es_4, "iloc1": 1, "iloc2": 2, "header_row": 1},
    {"name": "ES_5", "filepath": "c:/SierraChart/Data/StreamDataES_5.tsv", "columns": es_5, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "ES_6", "filepath": "c:/SierraChart/Data/StreamDataES_6.tsv", "columns": es_6, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "ES_7", "filepath": "c:/SierraChart/Data/StreamDataES_7.tsv", "columns": es_7, "iloc1": 0, "iloc2": 1, "header_row": 0},

    {"name": "NQ_1", "filepath": "c:/SierraChart/Data/StreamDataNQ_1.tsv", "columns": nq_1, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "NQ_2", "filepath": "c:/SierraChart/Data/StreamDataNQ_2.tsv", "columns": nq_2, "iloc1": 1, "iloc2": 2, "header_row": 1},
    {"name": "NQ_3", "filepath": "c:/SierraChart/Data/StreamDataNQ_3.tsv", "columns": nq_3, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "NQ_4", "filepath": "c:/SierraChart/Data/StreamDataNQ_4.tsv", "columns": nq_4, "iloc1": 1, "iloc2": 2, "header_row": 1},
    {"name": "NQ_5", "filepath": "c:/SierraChart/Data/StreamDataNQ_5.tsv", "columns": nq_5, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "NQ_6", "filepath": "c:/SierraChart/Data/StreamDataNQ_6.tsv", "columns": nq_6, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "NQ_7", "filepath": "c:/SierraChart/Data/StreamDataNQ_7.tsv", "columns": nq_7, "iloc1": 0, "iloc2": 1, "header_row": 0},

    {"name": "RTY_1", "filepath": "c:/SierraChart/Data/StreamDataRTY_1.tsv", "columns": rty_1, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "RTY_2", "filepath": "c:/SierraChart/Data/StreamDataRTY_2.tsv", "columns": rty_2, "iloc1": 1, "iloc2": 2, "header_row": 1},
    {"name": "RTY_3", "filepath": "c:/SierraChart/Data/StreamDataRTY_3.tsv", "columns": rty_3, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "RTY_4", "filepath": "c:/SierraChart/Data/StreamDataRTY_4.tsv", "columns": rty_4, "iloc1": 1, "iloc2": 2, "header_row": 1},
    {"name": "RTY_5", "filepath": "c:/SierraChart/Data/StreamDataRTY_5.tsv", "columns": rty_5, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "RTY_6", "filepath": "c:/SierraChart/Data/StreamDataRTY_6.tsv", "columns": rty_6, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "RTY_7", "filepath": "c:/SierraChart/Data/StreamDataRTY_7.tsv", "columns": rty_7, "iloc1": 0, "iloc2": 1, "header_row": 0},

    {"name": "CL_1", "filepath": "c:/SierraChart/Data/StreamDataCL_1.tsv", "columns": cl_1, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "CL_2", "filepath": "c:/SierraChart/Data/StreamDataCL_2.tsv", "columns": cl_2, "iloc1": 1, "iloc2": 2, "header_row": 1},
    {"name": "CL_3", "filepath": "c:/SierraChart/Data/StreamDataCL_3.tsv", "columns": cl_3, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "CL_4", "filepath": "c:/SierraChart/Data/StreamDataCL_4.tsv", "columns": cl_4, "iloc1": 1, "iloc2": 2, "header_row": 1},
    {"name": "CL_5", "filepath": "c:/SierraChart/Data/StreamDataCL_5.tsv", "columns": cl_5, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "CL_6", "filepath": "c:/SierraChart/Data/StreamDataCL_6.tsv", "columns": cl_6, "iloc1": 0, "iloc2": 1, "header_row": 0},
    {"name": "CL_7", "filepath": "c:/SierraChart/Data/StreamDataCL_7.tsv", "columns": cl_7, "iloc1": 0, "iloc2": 1, "header_row": 0},
]