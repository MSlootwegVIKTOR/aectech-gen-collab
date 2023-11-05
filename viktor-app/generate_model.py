from ShapeDiverTinySdk import ShapeDiverTinySessionSdk
import requests
import os

ticket = os.getenv("SD_TOKEN", "")
modelViewUrl = "https://sdr7euc1.eu-central-1.shapediver.com"


def generate_model(width, depth, height):
    parameters = {
        "4fe28102-4ab7-4a35-8c93-9d39652d34c7": depth,
        "3d6526a1-9cac-4f4e-afa1-49661f2eba6a": width,
        "62837813-baca-4051-a934-5fc092319f3b": 0,
        "8944a4d2-573b-46c8-a3d1-237d74fa292d": height,
    }

    shapeDiverSessionSdk = ShapeDiverTinySessionSdk(
        modelViewUrl=modelViewUrl, ticket=ticket
    )

    contentItemsGltf2 = shapeDiverSessionSdk.output(
        paramDict=parameters
    ).outputContentItemsGltf2()

    href = contentItemsGltf2["href"]

    res = requests.get(href)

    return res.content
