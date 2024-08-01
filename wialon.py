import pandas as pd
import json
import requests
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
import time

load_dotenv()

class Wialon:

    base_url = "https://hst-api.wialon.com/wialon/ajax.html?"

    def __init__(self):
        self.CLIENT_ID = os.getenv('CLIENT_ID')
        # self.USERNAME = os.getenv('USERNAME')
        self.USERNAME = ''
        self.PASSWORD = os.getenv('PASSWORD')
        self.BASE_API_URL = os.getenv('BASE_API_URL')
        self.REDIRECT_URI = os.getenv('REDIRECT_URI')
        self.AUTHORIZATION_URL = f"{self.BASE_API_URL}/login.html?wialon_sdk_url=https%3A%2F%2Fhst%2Dapi%2Ewialon%2Ecom&client_id={self.CLIENT_ID}&access_type=256&activation_time=0&duration=0&lang=en&flags=0"
        self.session_id = None

    @staticmethod
    def remove_keys(d, keys_to_remove):
        if isinstance(d, dict):
            for key in keys_to_remove:
                if key in d:
                    del d[key]
            for key in list(d.keys()):
                Wialon.remove_keys(d[key], keys_to_remove)
        elif isinstance(d, list):
            for item in d:
                Wialon.remove_keys(item, keys_to_remove)

    @staticmethod
    def rename_keys(d, key_map):
        new_data = {}
        for old_key, value in d.items():
            new_value = {}
            for inner_key, inner_value in value.items():
                new_key = key_map.get(inner_key, inner_key)
                new_value[new_key] = inner_value
            new_data[old_key] = new_value
        return new_data

    @staticmethod
    def list_of_units(data):
        unit_groups = []
        unit_group_ids = []
        units = []
        for key, value in data.items():
            unit_group = value['unit_group']
            unit_group_id = value['unit_group_id']
            for unit in value['units']:
                unit_groups.append(unit_group)
                unit_group_ids.append(unit_group_id)
                units.append(unit)
        df = pd.DataFrame({
            'Unit_Group': unit_groups,
            'Unit_Group_ID': unit_group_ids,
            'Unit': units
        })
        return df

    def authenticate(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--incognito")
        options.add_argument("--disable-application-cache")
        options.add_argument("--disk-cache-size=0")
        options.add_argument("--aggressive-cache-discard")
        options.add_argument("--disable-cache") 
        options.add_argument("--disable-browser-side-navigation")
        prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
        options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=options)
        driver.get(self.AUTHORIZATION_URL)
        driver.delete_all_cookies()
        driver.execute_script('window.localStorage.clear();')
        driver.execute_script('window.sessionStorage.clear();')
        
        try:
            username_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "login"))
            )
            username_input.send_keys(self.USERNAME)
            password_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "passw"))
            )
            password_input.send_keys(self.PASSWORD)
            password_input.send_keys(Keys.RETURN)
            time.sleep(5)
            redirected_url = driver.current_url
            parsed_url = urlparse(redirected_url)
            access_token = parse_qs(parsed_url.query).get('access_token', [None])[0]
            return access_token
        finally:
            driver.quit()

    def authenticated(self, access_token):
        url = f"{self.base_url}svc=token/login&params={{\"token\":\"{access_token}\"}}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'error' not in data:
                self.session_id = data['eid']
                return self.session_id
            else:
                raise Exception(f"Error in authentication: {data['error']}")
        else:
            raise Exception(f"Failed to connect to server: {response.status_code}")

    def search_items(self):
        params = {"spec":{"itemsType":"avl_unit_group","propName":"","propValueMask":"","sortType":"","propType":"","or_logic":False},"force":1,"flags":1,"from":0,"to":0}
        url = f"{self.base_url}svc=core/search_items&sid={self.session_id}&params={json.dumps(params)}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")

    def group_unit_items(self):
        params = {"spec":{"itemsType":"avl_unit_group","propName":"","propValueMask":"","sortType":"","propType":"","or_logic":False},"force":1,"flags":1,"from":0,"to":0}
        url = f"{self.base_url}svc=core/search_items&sid={self.session_id}&params={json.dumps(params)}"
        response = requests.get(url)
        if response.status_code == 200:
            response = dict(response.json())
            response = response.get("items")[1:]
            keys_to_remove = ["cls", "mu", "uacl"]
            
            self.remove_keys(response, keys_to_remove)
            response = {i: d for i, d in enumerate(response, start=1)}

            key_map = {"nm": "unit_group", "id": "unit_group_id", "u": "units"}
            return self.rename_keys(response, key_map)
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")
        
    def search_unit_type(self):
        params = {
                    "spec": {
                        "itemsType": "avl_unit",
                        "propName": "rel_hw_type_name,rel_last_msg_date",
                        "propValueMask": "*",
                        "sortType": "rel_creation_time"
                    },
                    "force": 1,
                    "flags": 1,
                    "from": 0,
                    "to": 0
                } 
        url = f"{self.base_url}svc=core/search_items&sid={self.session_id}&params={json.dumps(params)}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")
        
    def search_unit_groups(self):
        params = {
                    "spec": {
                        "itemsType": "avl_unit_group",
                        "propName": "rel_user_creator_name,rel_group_unit_count",
                        "propValueMask": "*",
                        "sortType": "sys_name"
                    },
                    "force": 1,
                    "flags": 133,
                    "from": 0,
                    "to": 0
                } 
        url = f"{self.base_url}svc=core/search_items&sid={self.session_id}&params={json.dumps(params)}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")
        
    def exec_report(self):
        params={
            "reportResourceId":27916207,
            "reportTemplateId":2,
            "reportObjectId":27922767,
            "reportObjectSecId":0,
            "interval":{
                "from": 1717243200,
                "to":1721304000,
                "flags":0
            }
        }
        url = f"{self.base_url}svc=report/exec_report&sid={self.session_id}&params={json.dumps(params)}"
        response = requests.get(url)
        
        params={
            "tableIndex": 0,
            "indexFrom": 0,
            "indexTo": 0
        }
        url = f"{self.base_url}svc=report/get_result_rows&sid={self.session_id}&params={json.dumps(params)}"
        response = requests.get(url)
        return response.json()
        
    def report_tables(self):
        params={

        }
        url = f"{self.base_url}svc=report/get_report_tables&sid={self.session_id}&params={json.dumps(params)}"
        response = requests.get(url)
        if response.status_code == 200:
            response = response.json()
            return response
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")
        
    def report_data(self):
        params={
            "itemId": 27916207,
            "col": [1,2,3,4,5,6,7,8,9,10,11,12,13,14],
            "flags": 0
        }
        url = f"{self.base_url}svc=report/get_report_data&sid={self.session_id}&params={json.dumps(params)}"
        response = requests.get(url)
        if response.status_code == 200:
            response = response.json()
            return response
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")
        
    def result_rows(self):
        params={
            "tableIndex": 0,
            "indexFrom": 0,
            "indexTo": 0
        }
        url = f"{self.base_url}svc=report/get_result_rows&sid={self.session_id}&params={json.dumps(params)}"
        response = requests.get(url)
        return response.json()

    def summary_report(self, time_from, time_to):
    
        # time_from and time_to are unix timestamps for the start and end date
       
        data = self.group_unit_items()
        data = self.list_of_units(data)
        data = list(set(data["Unit"].tolist()))

        result = []

        for d in data:
            # Report execution
            params={
                "reportResourceId":27916207,
                "reportTemplateId":2,
                "reportObjectId":d,
                "reportObjectSecId":0,
                "interval":{
                    "from": time_from,
                    "to":time_to,
                    "flags":0
                }
            }
            url = f"{self.base_url}svc=report/exec_report&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)

            # fetching report data
            params={
                "tableIndex": 0,
                "indexFrom": 0,
                "indexTo": 0
            }
            url = f"{self.base_url}svc=report/get_result_rows&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            result.append(response.json())
            
            file_path = 'summary_report.json'
        with open(file_path, 'w') as json_file:
            json.dump(result, json_file, indent=4)

        print(f"Summary_report JSON data has been successfully written to {file_path}")
       
        cleaned_data = []
        for entry in result:
            vehicle_info = {
                'Grouping': entry[0]['c'][0],
                'Km/l': entry[0]['c'][1],
                'Mileage': entry[0]['c'][2],
                'Max_Speed': entry[0]['c'][3]['t'],
                'Latitude': entry[0]['c'][3]['y'],
                'Longitude': entry[0]['c'][3]['x'],
                'Unit': entry[0]['c'][3]['u'],
                'Engine_Hours': entry[0]['c'][4],
                'Fuel_Consumption': entry[0]['c'][5],
                'Initial_Fuel_Level': entry[0]['c'][6],
                'Final_Fuel_Level': entry[0]['c'][7],
                'Total_Fillings': entry[0]['c'][8],
                'Total_Drains': entry[0]['c'][9],
                'Fuel_Filled': entry[0]['c'][10],
                'Fuel_Drained': entry[0]['c'][11]
            }
            cleaned_data.append(vehicle_info)
         # Save cleaned data as CSV
        csv_file_path = 'summary_report.csv'
        pd.DataFrame(cleaned_data).to_csv(csv_file_path, index=False)

        print(f"Summary_report cleaned data has been successfully written to {csv_file_path}")

    def trips(self, time_from, time_to):

        # time_from and time_to are unix timestamps for the start and end date

        data = self.group_unit_items()
        data = self.list_of_units(data)
        data = list(set(data["Unit"].tolist()))

        result = []

        for d in data:
            # Report execution
            params={
                "reportResourceId":27916207,
                "reportTemplateId":1,
                "reportObjectId":d,
                "reportObjectSecId":0,
                "interval":{
                    "from": time_from,
                    "to":time_to,
                    "flags":0
                }
            }
            url = f"{self.base_url}svc=report/exec_report&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            
            # fetching report data
            params={
                "tableIndex": 0,
                "rowIndex": 0
            }
            url = f"{self.base_url}svc=report/get_result_subrows&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            result.append(response.json())
       
        file_path = 'trips_report.json'
        with open(file_path, 'w') as json_file:
            json.dump(result, json_file, indent=4)

        print(f"Trips_report JSON data has been successfully written to {file_path}")

        cleaned_data = []
        for entry in result:
            vehicle_info = {
                'Grouping': entry[0]['c'][0],
                'Beginning_Date_Time': entry[0]['c'][1]['t'],
                'Initial_Location': entry[0]['c'][2]['t'],
                'End_Date_Time': entry[0]['c'][3]['t'],
                'Final_Location': entry[0]['c'][4]['t'],
                'Duration': entry[0]['c'][5],
                'Mileage': entry[0]['c'][6],
                'Avg Speed': entry[0]['c'][7]
            }
            cleaned_data.append(vehicle_info)
        # Save cleaned data as CSV
        csv_file_path = 'trips_report.csv'
        pd.DataFrame(cleaned_data).to_csv(csv_file_path, index=False)

        print(f"Trips_report cleaned data has been successfully written to {csv_file_path}")

    def refueling_and_drops(self, time_from, time_to):

    # time_from and time_to are unix timestamps for the start and end date

        data = self.group_unit_items()
        data = self.list_of_units(data)
        data = list(set(data["Unit"].tolist()))
        # print(data)
        # print(len(data))

        result = []

        for d in data:
            # Report execution
            params={
                "reportResourceId":27916207,
                "reportTemplateId":3,
                "reportObjectId":d,
                "reportObjectSecId":0,
                "interval":{
                    "from": time_from,
                    "to":time_to,
                    "flags":0
                }
            }
            url = f"{self.base_url}svc=report/exec_report&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            
            # fetching report data
            params={
                "tableIndex": 0,
                "rowIndex": 0
            }
            url = f"{self.base_url}svc=report/get_result_subrows&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            result.append(response.json())
        
        file_path = 'refuel_and_drops.json'
        with open(file_path, 'w') as json_file:
            json.dump(result, json_file, indent=4)

        print(f"Refuel_and_drops JSON data has been successfully written to {file_path}")

        cleaned_data = []
        for entry in result:
            for e in entry:
                vehicle_info = {
                    'Grouping': "" if e['c'][0] is None else e['c'][0],
                    'Time': e['c'][1]['t'] if isinstance(e['c'][1], dict) else "",
                    'Location': e['c'][2]['t'] if isinstance(e['c'][2], dict) else "",
                    'Initial_Fuel_Level':  e['c'][3] if e['c'][3] != "-----" else "",
                    'Filled':  e['c'][4] if e['c'][4] != "-----" else "",
                    'Final_Fuel_Level':  e['c'][5] if e['c'][5] != "-----" else "",
                    'Sensor_Name':  e['c'][6]['t'] if isinstance(e['c'][6], dict) else ""
                }
                cleaned_data.append(vehicle_info)
        
            # Save cleaned data as CSV
                csv_file_path = 'refuel_and_drops.csv'
                pd.DataFrame(cleaned_data).to_csv(csv_file_path, index=False)

                print(f"Refuel_and_drops cleaned data has been successfully written to {csv_file_path}")

    def geofence(self, time_from, time_to):
      
    # time_from and time_to are unix timestamps for the start and end date

        data = self.group_unit_items()
        data = self.list_of_units(data)
        data = list(set(data["Unit"].tolist()))
        # print(data)
        # print(len(data))

        result = []

        for d in data:
            # Report execution
            params={
                "reportResourceId":27916207,
                "reportTemplateId":6,
                "reportObjectId":d,
                "reportObjectSecId":0,
                "interval":{
                    "from": time_from,
                    "to":time_to,
                    "flags":0
                }
            }
            url = f"{self.base_url}svc=report/exec_report&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            
            # fetching report data
            params={
                "tableIndex": 0,
                "rowIndex": 0
            }
            url = f"{self.base_url}svc=report/get_result_subrows&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            result.append(response.json())
      
        file_path = 'geofence_report.json'
        with open(file_path, 'w') as json_file:
            json.dump(result, json_file, indent=4)

        print(f"Geofence JSON data has been successfully written to {file_path}")

        cleaned_data = []
        for entry in result:
            for e in entry:
                vehicle_info = {
                    'Grouping': e['c'][0],
                    'Geofence': e['c'][1],
                    'Time_In': e['c'][2]['t'],
                    'Time_Out': e['c'][3]['t'],
                    'Duration_In': e['c'][4],
                    'Total_Time': e['c'][5],
                    'Driver': e['c'][6]

                }
                cleaned_data.append(vehicle_info)
         # Save cleaned data as CSV
        csv_file_path = 'geofence_report.csv'
        pd.DataFrame(cleaned_data).to_csv(csv_file_path, index=False)

        print(f"Geofence cleaned data has been successfully written to {csv_file_path}")

    def eco_driving(self, time_from, time_to):
       
    # time_from and time_to are unix timestamps for the start and end date

        data = self.group_unit_items()
        data = self.list_of_units(data)
        data = list(set(data["Unit"].tolist()))
        
        result = []

        for d in data:
            # Report execution
            params={
                "reportResourceId":27916207,
                "reportTemplateId":8,
                "reportObjectId":d,
                "reportObjectSecId":0,
                "interval":{
                    "from": time_from,
                    "to":time_to,
                    "flags":0
                }
            }
            url = f"{self.base_url}svc=report/exec_report&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            
            # fetching report data
            params={
                "tableIndex": 0,
                "rowIndex": 0
            }
            url = f"{self.base_url}svc=report/get_result_subrows&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            result.append(response.json())
      
        file_path = 'ecodriving_report.json'
        with open(file_path, 'w') as json_file:
            json.dump(result, json_file, indent=4)

        print(f"Eco_driving JSON data has been successfully written to {file_path}")

        cleaned_data = []
        for entry in result:
            for e in entry:
                vehicle_info = {
                    'Grouping': e['c'][0],
                    'Beginning': e['c'][1]['t'],
                    'Initial_Location': e['c'][2]['t'],
                    'Rating_By_Violations': e['c'][3],
                    'Driver': e['c'][4],
                    'Violation': e['c'][5],
                    'Value': e['c'][6],
                    'Penalties': e['c'][7],
                    'Rank': e['c'][8]
                }
                cleaned_data.append(vehicle_info)
         # Save cleaned data as CSV
        csv_file_path = 'ecodriving_report.csv'
        pd.DataFrame(cleaned_data).to_csv(csv_file_path, index=False)

        print(f"Eco_driving cleaned data has been successfully written to {csv_file_path}")

    def events(self, time_from, time_to):
       
    # time_from and time_to are unix timestamps for the start and end date

        data = self.group_unit_items()
        data = self.list_of_units(data)
        data = list(set(data["Unit"].tolist()))
        
        result = []

        for d in data:
            # Report execution
            params={
                "reportResourceId":27916207,
                "reportTemplateId":2,
                "reportObjectId":d,
                "reportObjectSecId":0,
                "interval":{
                    "from": time_from,
                    "to":time_to,
                    "flags":0
                }
            }
            url = f"{self.base_url}svc=report/exec_report&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)

            # fetching report data
            params={
                "tableIndex": 0,
                "indexFrom": 0,
                "indexTo": 0
            }
            url = f"{self.base_url}svc=report/get_result_rows&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            result.append(response.json())
        
        file_path = 'events_report.json'
        with open(file_path, 'w') as json_file:
            json.dump(result, json_file, indent=4)
    
    def group_events(self, time_from, time_to):

     # time_from and time_to are unix timestamps for the start and end date

        data = self.group_unit_items()
        data = self.list_of_units(data)
        data = list(set(data["Unit"].tolist()))
        
        result = []

        for d in data:
            # Report execution
            params={
                "reportResourceId":27916207,
                "reportTemplateId":13,
                "reportObjectId":d,
                "reportObjectSecId":0,
                "interval":{
                    "from": time_from,
                    "to":time_to,
                    "flags":0
                }
            }
            url = f"{self.base_url}svc=report/exec_report&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            
            # fetching report data
            params={
                "tableIndex": 0,
                "rowIndex": 0
            }
            url = f"{self.base_url}svc=report/get_result_subrows&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            result.append(response.json())
      
        file_path = 'groupevents_report.json'
        with open(file_path, 'w') as json_file:
            json.dump(result, json_file, indent=4)

        print(f"JSON data has been successfully written to {file_path}")

        cleaned_data = []
        for entry in result:
            for e in entry:
                vehicle_info = {
                    'Grouping': e['c'][0],
                    'Event_Time': e['c'][1]['t'],
                    'Time_Received': e['c'][2],
                    'Event_Text': e['c'][3]['t'],
                    'Event_Type': e['c'][4],
                    'Driver': e['c'][5],
                    'Location': e['c'][6]['t']
                }
                cleaned_data.append(vehicle_info)
                
        # Save cleaned data as CSV
        csv_file_path = 'groupevents_report.csv'
        pd.DataFrame(cleaned_data).to_csv(csv_file_path, index=False)

        print(f"Cleaned data has been successfully written to {csv_file_path}")

    def eco_driving_v2(self, time_from, time_to):
    
    # time_from and time_to are unix timestamps for the start and end date

        data = self.group_unit_items()
        data = self.list_of_units(data)
        data = list(set(data["Unit"].tolist()))
        # print(data)
        # print(len(data))

        result = []

        for d in data:
            # Report execution
            params={
                "reportResourceId":27916207,
                "reportTemplateId":14,
                "reportObjectId":d,
                "reportObjectSecId":0,
                "interval":{
                    "from": time_from,
                    "to":time_to,
                    "flags":0
                },
                "tzOffset": 10800
            }
            url = f"{self.base_url}svc=report/exec_report&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            
            # fetching report data
            params={
                "tableIndex": 0,
                "rowIndex": 0
            }
            url = f"{self.base_url}svc=report/get_result_subrows&sid={self.session_id}&params={json.dumps(params)}"
            response = requests.get(url)
            result.append(response.json())
            
        file_path = 'ecodrivingv2_report.json'
        with open(file_path, 'w') as json_file:
            json.dump(result, json_file, indent=4)

        print(f"JSON data has been successfully written to {file_path}")

        cleaned_data = []
        for entry in result:
            try:
                for e in entry:
                    vehicle_info = {
                        'Grouping': e['c'][0],
                        'Violation': e['c'][1],
                        'Beginning': e['c'][2]['t'],
                        'Initial_Location': e['c'][3]['t'],
                        'End': e['c'][4]['t'],
                        'Final_Location': e['c'][5]['t'],
                        'Rating_by_Violations': e['c'][6] if e['c'][6] != "-----" else "",
                        'Driver': e['c'][7]
                    }
                    cleaned_data.append(vehicle_info)
            except:
                pass
        # Save cleaned data as CSV
        csv_file_path = 'ecodrivingv2_report.csv'
        pd.DataFrame(cleaned_data).to_csv(csv_file_path, index=False)

        print(f"Cleaned data has been successfully written to {csv_file_path}")


if __name__ == "__main__":
    wialon = Wialon()
    try:
        access_token = wialon.authenticate()
        if access_token:
            print(f"Access token: {access_token}")
            session_id = wialon.authenticated(access_token)
            print(f"Authenticated successfully. Session ID: {session_id}")

            #data = wialon.group_unit_items()
            data = wialon.eco_driving_v2(1717243200, 1721304000)
            data = wialon.group_events(1717243200, 1721304000)
            data = wialon.events(1717243200, 1721304000)
            data = wialon.eco_driving(1717243200, 1721304000)
            data = wialon.geofence(1717243200, 1721304000)
            data = wialon.refueling_and_drops(1717243200, 1721304000)
            data = wialon.trips(1717243200, 1721304000)
            data = wialon.summary_report(1717243200, 1721304000)
            
            print(data)
    except Exception as e:
        print(f"Error: {e}")
