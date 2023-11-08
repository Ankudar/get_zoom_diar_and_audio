import requests
import json
import os
import csv
from base64 import b64encode
from tqdm import tqdm

client_id = "client_id"
client_secret = "client_secret"
account_id = "account_id"
meets_id = "./meets_id/"

def get_access_token(client_id, client_secret):
    credentials = b64encode(bytes(f'{client_id}:{client_secret}', 'utf-8')).decode('utf-8')
    headers = {
        'Authorization': f'Basic {credentials}',
        'Host': 'zoom.us'
    }
    data = {
        'grant_type': 'account_credentials',
        'account_id': account_id
    }
    response = requests.post('https://zoom.us/oauth/token', headers=headers, data=data)
    access_token = response.json()['access_token']
    return access_token

def read_meetings_from_csv(meets_id):
    files = os.listdir(meets_id)
    filename = [f for f in files if f.endswith('.csv')]
    if not filename:
        raise Exception("No CSV file found in the directory.")
    meetings = []
    for f in filename:
        with open(meets_id + f, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                id = row[2].replace(" ", "")
                if id.isdigit():
                    meetings.append(id)
    return meetings

def get_recordings(access_token, meets_idents):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    for meet_ident in tqdm(meets_idents, desc="Processing meetings", unit="meeting"):
        try:
            response = requests.get(f'https://api.zoom.us/v2/meetings/{meet_ident}/recordings', headers=headers).json()
            download_access_token = requests.get(f"https://api.zoom.us/v2/meetings/{meet_ident}/recordings?include_fields=download_access_token", headers=headers).json()["download_access_token"]
        except KeyError:
            access_token = get_access_token(client_id, client_secret)
            headers["Authorization"] = f"Bearer {access_token}"
            continue

        if "participant_audio_files" in response:
            response = response["participant_audio_files"]

            for recording in response:
                participant_name = recording["file_name"].replace("Audio only - ", "")
                directory_path = f"./zoom_recording/{participant_name}"
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)
                num_files = len([f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))])
                file_name = f"{recording['file_name']}_{num_files + 1}_meetid_{meet_ident}.{recording['file_extension']}"
                download_url = recording["download_url"] + f"?access_token={download_access_token}"

                file_path = os.path.join(directory_path, file_name)
                response = requests.get(download_url, stream=True)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        for chunk in response:
                            f.write(chunk)
                else:
                    print(f"Не удалось скачать файл {file_name}. Статус ответа: {response.status_code}")

try:
    meets_idents = read_meetings_from_csv(meets_id)
    access_token = get_access_token(client_id, client_secret)
    get_recordings(access_token, meets_idents)
except requests.exceptions.HTTPError as err:
    print(f"Запрос не удался: {err}")