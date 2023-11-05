import time
import requests
import numpy as np
import os

from viktor import File, progress_message
from viktor.utils import memoize

from generate_model import generate_model
from height_map_utils import crop_map, merge_maps
from raytrace import gltf_raytrace, get_trimesh_object
from forma_storage import get_terrain, get_surroundings, store_alternatives_forma, store_alternatives_viktor
from viktor_subdomain.helper_functions import set_environment_variables

set_environment_variables()
forma_base_url = "https://app.autodeskforma.eu"
FORMA_PROJECT_ID = os.getenv("FORMA_PROJECT_ID", "pro_nz1xbbzv0p")
FORMA_TOKEN = os.getenv("FORMA_TOKEN", "bkhFR0hMeDk4OTJUaXFsTFZaQmJjbEdjYUVwMUcya2Q6aXJMTDZrOXJ4elRGaTlnWA==")

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

    return np.ma.masked_array(np.array([[1]*200]*200), mask=terrain_height_map == 0)

    min_height = min(terrain_and_buildings_height_map.min(), terrain_height_map.min())
    max_height = max(terrain_and_buildings_height_map.max(), terrain_height_map.max())

    normalized_terrain_and_buildings_height_map = [
        round((x - min_height) / (max_height - min_height))
        for x in terrain_and_buildings_height_map.flatten().tolist()
    ]
    normalized_terrain_height_map = [
        round((x - min_height) / (max_height - min_height)) for x in terrain_height_map.flatten().tolist()
    ]

    start = time.time()
    res = requests.post(
        f"{forma_base_url}/api/surrogate/forma-wind-core/experimental?authcontext={FORMA_PROJECT_ID}&direction=0&analysisType=comfort&comfortScale=lawson_lddc",
        headers={"Authorization": "Bearer " + FORMA_TOKEN},
        json={
            "heightMaps": {
                "terrainHeightArray": normalized_terrain_height_map,
                "buildingAndTerrainHeightArray": normalized_terrain_and_buildings_height_map,
                "minHeight": int(min_height),
                "maxHeight": int(max_height),
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


@memoize
def create_geometry(options) -> bytes:
    return generate_model(options["width"], options["depth"], options["height"])


def create_height_map(glb):
    return 


def generate(params):
    alternatives = []

    progress_message('Retrieve terrain...')
    terrain_glb = get_terrain()
    progress_message('Retrieve surroundings')
    surrounding_glb = get_surroundings()

    progress_message('Ray-tracing terrain...')
    terrain_mesh = get_trimesh_object(glb=terrain_glb)
    scene = terrain_mesh.scene()
    bounds = scene.bounding_box.bounds
    terrain_height_map = gltf_raytrace(glb=terrain_glb, bounding_box=bounds)
    progress_message('Ray-tracing surroundings...')
    surrounding_height_map = gltf_raytrace(glb=surrounding_glb, bounding_box=bounds)

    for idx, options in enumerate(params.analysis.design_options, start=1):
        progress_message(f"Design option {idx}: Create geometry...")
        alternative_glb: bytes = create_geometry(options)

        progress_message(f"Design option {idx}: Ray-tracing...")
        alternative_height_map = gltf_raytrace(glb=File.from_data(alternative_glb), bounding_box=bounds)

        progress_message(f"Design option {idx}: Processing...")
        terrain_height_map_cropped = crop_map(terrain_height_map["map"])
        merged_height_map = merge_maps(
            terrain_height_map, surrounding_height_map, alternative_height_map
        )
        merged_height_map_cropped = crop_map(merged_height_map)

        progress_message(f"Design option {idx}: Analyzing...")
        analyze_result = analyze(terrain_height_map_cropped, merged_height_map_cropped)

        score = evaluate(analyze_result)

        alternatives.append({"alternative": alternative_glb, "score": score})

    progress_message(f"Saving results to Forma and VIKTOR...")
    store_alternatives_forma(alternatives[0:5])
    store_alternatives_viktor(alternatives)


def evaluate(analysis_result):
    return analysis_result.mean()
