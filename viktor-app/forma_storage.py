import os
import requests
from viktor import File
from viktor_subdomain.helper_functions import set_environment_variables

set_environment_variables()
FORMA_PROJECT_ID = os.getenv("FORMA_PROJECT_ID", "pro_sk5xhdofb7")
FORMA_SECRET = os.getenv("FORMA_SECRET", "")

def get_two_legged_aps_token() -> str:
    two_legged_res = requests.post("https://developer.api.autodesk.com/authentication/v2/token",
                                data={'grant_type': 'client_credentials', 'scope': "data:write"},
                                headers={
                                    'Content-Type': 'application/x-www-form-urlencoded',
                                    'Accept': "application/json",
                                    'Authorization': f"Basic {FORMA_SECRET}"})
    two_legged_res.raise_for_status()
    access_token = two_legged_res.json()["access_token"]
    return access_token


def get_terrain():
    aps_token = get_two_legged_aps_token()
    object_res = requests.get(f"https://app.autodeskforma.eu/api/extension-service/installations/8ad1d7f9-4e17-4485-aa14-f2217475b5e0/storage-objects/terrain.glb?authcontext={FORMA_PROJECT_ID}",allow_redirects=False, headers={"Authorization": f"Bearer {aps_token}"})
    object_res.raise_for_status()
    redirect_url = object_res.headers['Location']
    return File.from_url(redirect_url)


def get_surroundings():
    aps_token = get_two_legged_aps_token()
    object_res = requests.get(f"https://app.autodeskforma.eu/api/extension-service/installations/8ad1d7f9-4e17-4485-aa14-f2217475b5e0/storage-objects/surroundings.glb?authcontext={FORMA_PROJECT_ID}",allow_redirects=False, headers={"Authorization": f"Bearer {aps_token}"})
    object_res.raise_for_status()
    redirect_url = object_res.headers['Location']
    return File.from_url(redirect_url)


def store_alternatives(alternatives):
    aps_token = get_two_legged_aps_token()
    for i in range(len(alternatives)):
        alternative = alternatives[i]
        object_res = requests.get(f"https://app.autodeskforma.eu/api/extension-service/installations/8ad1d7f9-4e17-4485-aa14-f2217475b5e0/storage-objects/alternatives-{i}.glb/upload-url?authcontext={FORMA_PROJECT_ID}",allow_redirects=False, headers={"Authorization": f"Bearer {aps_token}"})
        object_res.raise_for_status()
        url = object_res.json()["url"]

        res = requests.post(url, data=alternative, headers={"Content-Type": "model/gltf-binary"})
        res.raise_for_status()
