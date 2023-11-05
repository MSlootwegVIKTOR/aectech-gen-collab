import time
import requests
import numpy as np
import os

from generate_model import generate_model


forma_base_url = "https://app.autodeskforma.eu"
projectId = os.getenv("FORMA_PROJECT_ID", "pro_sk5xhdofb7")
token = os.getenv("FORMA_TOKEN", "")


def get_wind_parameters():
    # res = requests.get(
    #    f"{forma_base_url}/api/surrogate/forma-wind-core/wind-parameters?authcontext={projectId}",
    #    headers={"Authorization": "Bearer " + token},
    # )

    # res.raise_for_status()

    # print(res.json())

    return {
        "data": [
            {
                "direction": 0,
                "probability": 0.09129138313326708,
                "weibull_scale_parameter": 8.13,
                "weibull_shape_parameter": 2.639,
            },
            {
                "direction": 45,
                "probability": 0.0984784769477789,
                "weibull_scale_parameter": 7.295,
                "weibull_shape_parameter": 1.8824999999999998,
            },
            {
                "direction": 90,
                "probability": 0.10994724367306372,
                "weibull_scale_parameter": 5.39,
                "weibull_shape_parameter": 1.662,
            },
            {
                "direction": 135,
                "probability": 0.051150699594770255,
                "weibull_scale_parameter": 5.625,
                "weibull_shape_parameter": 1.861,
            },
            {
                "direction": 180,
                "probability": 0.09771389249942658,
                "weibull_scale_parameter": 7.67,
                "weibull_shape_parameter": 2.127,
            },
            {
                "direction": 225,
                "probability": 0.16285648749904427,
                "weibull_scale_parameter": 9.125,
                "weibull_shape_parameter": 2.9745,
            },
            {
                "direction": 270,
                "probability": 0.17187858398960168,
                "weibull_scale_parameter": 9.01,
                "weibull_shape_parameter": 2.404,
            },
            {
                "direction": 315,
                "probability": 0.21668323266304768,
                "weibull_scale_parameter": 9.155000000000001,
                "weibull_shape_parameter": 2.5410000000000004,
            },
        ],
        "height": 100,
        "roughness": 0.4978,
    }


def analyze(terrain_height_map, terrain_and_buildings_height_map):
    min_height = min(min(terrain_and_buildings_height_map), min(terrain_height_map))
    max_height = max(max(terrain_and_buildings_height_map), max(terrain_height_map))

    normalized_terrain_and_buildings_height_map = [
        round((x - min_height) / (max_height - min_height))
        for x in terrain_and_buildings_height_map
    ]
    normalized_terrain_height_map = [
        round((x - min_height) / (max_height - min_height)) for x in terrain_height_map
    ]

    start = time.time()
    res = requests.post(
        f"{forma_base_url}/api/surrogate/forma-wind-core/experimental?authcontext={projectId}&direction=0&analysisType=comfort&comfortScale=lawson_lddc",
        headers={"Authorization": "Bearer " + token},
        json={
            "heightMaps": {
                "terrainHeightArray": normalized_terrain_height_map,
                "buildingAndTerrainHeightArray": normalized_terrain_and_buildings_height_map,
                "minHeight": min_height,
                "maxHeight": max_height,
            },
            "windRose": get_wind_parameters(),
            "type": "comfort",
            "roughness": 0.4978,
            "comfortScale": "lawson_lddc",
        },
    )
    end = time.time()
    print(end - start)

    res.raise_for_status()

    data = res.json()

    arr = np.array(data["heatmap_data"])
    masked = np.ma.masked_array(arr, mask=data["heatmap_mask"])

    return masked


def generation_options(site):
    return [{"x": 0, "y": 0, "height": 100, "depth": 30, "width": 30}]


def create_geometry(options):
    return generate_model(options["width"], options["depth"], options["height"])


def create_height_map(glb):
    return [0] * 500 * 500


def merge_height_maps(terrain, surrounding, alternative):
    return [0] * 500 * 500


def generate(terrain_glb, surrounding_glb, site):
    alternatives = []

    terrain_height_map = create_height_map(terrain_glb)
    surrounding_height_map = create_height_map(surrounding_glb)

    for options in generation_options(site):
        alternative_glb = create_geometry(options)

        alternative_height_map = create_height_map(alternative_glb)

        analyze_result = analyze(
            terrain_height_map,
            merge_height_maps(
                terrain_height_map, surrounding_height_map, alternative_height_map
            ),
        )

        score = evaluate(analyze_result)

        alternatives.append({"alternative": alternative_glb, "score": score})

    print(alternatives)


def evaluate(analysis_result):
    return analysis_result.mean()


generate({}, {})
