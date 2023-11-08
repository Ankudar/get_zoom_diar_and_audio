import whisper
import glob
from faster_whisper import WhisperModel

import requests
import json
import os
import csv
import re
from datetime import datetime
from base64 import b64encode

client_id = "your_client_id"
client_secret = "your_client_secret"
account_id = "your_account_id"
meets_idents = "meet_ident"

MODEL_NAME = "large-v2"
model = WhisperModel(MODEL_NAME, device="cuda", compute_type="float16")

def check_meets_id(meets_idents):
    if re.match("^[0-9 ]*$", meets_idents) is None:
        return "Incorrect meet_ident"
    cleaned_id = re.sub("[^0-9]", "", meets_idents)
    return cleaned_id

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

def time_to_seconds(time_str):
    h, m, s = map(float, time_str.split(':'))
    return h * 3600 + m * 60 + s

def combine_txt(directory_path):
    try:
        directory_path = directory_path + "/"
        audio_file = next(file for file in os.listdir(directory_path) if file.endswith(('.mp3', '.wav', '.M4A')))
        audio_file_name = os.path.splitext(audio_file)[0]
        txt_files = glob.glob(os.path.join(directory_path, '*.txt'))
        lines = []
        for txt_file in txt_files:
            with open(txt_file, 'r', encoding="UTF-8") as file:
                lines.extend(file.readlines())
        lines.sort(key=lambda x: time_to_seconds(re.search(r'\[(.*?)\]', x).group(1).split(' -> ')[0]))
        with open(os.path.join(directory_path, audio_file_name + '.txt'), 'w', encoding="UTF-8") as file:
            file.writelines(lines)
        for txt_file in txt_files:
            os.remove(txt_file)
    except Exception as e:
        print(f"An error occurred: {e}")

def get_recordings(access_token, meets_idents):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(f'https://api.zoom.us/v2/meetings/{meets_idents}/recordings', headers=headers).json()
        download_access_token = requests.get(f"https://api.zoom.us/v2/meetings/{meets_idents}/recordings?include_fields=download_access_token", headers=headers).json()["download_access_token"]
    except KeyError:
        access_token = get_access_token(client_id, client_secret)
        headers["Authorization"] = f"Bearer {access_token}"
        pass

    # with open('zoom.json', 'w', encoding='utf-8') as f:
    #     json.dump(response, f, ensure_ascii=False, indent=4)

    current_date = datetime.now()
    directory_path = os.path.join("./result", str(current_date.year), str(current_date.month), str(current_date.day), meets_idents).replace("\\", "/")
    os.makedirs(directory_path, exist_ok=True)

    if "recording_files" in response:
        for recording in response["recording_files"]:
            if recording["recording_type"] == "audio_only" and recording["file_extension"] == "M4A":
                num_files = len([f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))])
                file_name = response['topic'].replace("\\", "_")
                file_name = f"{file_name}_meetid_{meets_idents}.{recording['file_extension']}"
                download_url = recording["download_url"] + f"?access_token={download_access_token}"
                file_path = os.path.join(directory_path, file_name)
                resp = requests.get(download_url, stream=True)
                if resp.status_code == 200:
                    with open(file_path, 'wb') as f:
                        for chunk in resp:
                            f.write(chunk)
                else:
                    print(f"Не удалось скачать файл {file_name}. Статус ответа: {response.status_code}")

    if "participant_audio_files" in response:
        response = response["participant_audio_files"]
        for recording in response:
            participant_name = recording["file_name"].replace("Audio only - ", "")
        
            num_files = len([f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))])
            file_name = f"{recording['file_name']}.{recording['file_extension']}".replace("Audio only - ", "")
            download_url = recording["download_url"] + f"?access_token={download_access_token}"

            file_path = os.path.join(directory_path, file_name)
            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response:
                        f.write(chunk)
                whisper.diar_file(file_path, model)
            else:
                print(f"Не удалось скачать файл {file_name}. Статус ответа: {response.status_code}")

    combine_txt(directory_path)

try:
    meets_idents = check_meets_id(meets_idents)
    access_token = get_access_token(client_id, client_secret)
    get_recordings(access_token, meets_idents)
except requests.exceptions.HTTPError as err:
    print(f"Запрос не удался: {err}")