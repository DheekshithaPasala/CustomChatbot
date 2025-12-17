import requests

def stream_file_from_onedrive(file_id: str, drive_id: str, token: str):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"File stream failed | Status: {response.status_code} | Body: {response.text}"
        )

    return response.content
