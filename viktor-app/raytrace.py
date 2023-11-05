"""
raytrace.py
----------------

A very simple example of using scene cameras to generate
rays for image reasons.

Install `pyembree` for a speedup (600k+ rays per second)
"""
from io import BytesIO
from pathlib import Path

import numpy as np
import PIL.Image

import trimesh
from viktor import File


def gltf_raytrace(gltf_file: File=None, return_image=False):
    if gltf_file:
        gltf = BytesIO(gltf_file.getvalue_binary())
    else:
        # test on a simple mesh
        gltf = Path(__file__).parent / 'files' / 'geometry.gltf'
    mesh = trimesh.load(gltf, force='mesh')

    # scene will have automatically generated camera and lights
    scene = mesh.scene()
    min, max = scene.bounding_box.bounds

    # any of the automatically generated values can be overridden
    # set resolution, in pixels
    RESOLUTION = [640, 480]
    scene.camera.resolution = RESOLUTION
    # set field of view, in degrees
    # make it relative to resolution so pixels per degree is same
    scene.camera.fov = 60 * (scene.camera.resolution / scene.camera.resolution.max())

    # convert the camera to rays with one ray per pixel
    origin_x = np.linspace(min[0], max[0], RESOLUTION[0])
    origin_y = np.linspace(min[1], max[1], RESOLUTION[1])
    origins, vectors, pixels = scene.camera_rays()

    for idx, pixel in enumerate(pixels):
        origins[idx] = np.array([origin_x[pixel[0]], origin_y[pixel[1]], origins[idx][2]])
        vectors[idx] = np.array([0, 0, -1])

    # do the actual ray- mesh queries
    points, index_ray, index_tri = mesh.ray.intersects_location(
        ray_origins=origins, ray_directions=vectors, multiple_hits=False
    )

    # for each hit, find the distance along its vector
    depth = trimesh.util.diagonal_dot(points - origins[0], vectors[index_ray])
    # find pixel locations of actual hits
    pixel_ray = pixels[index_ray]

    # create a numpy array we can turn into an image
    # doing it with uint8 creates an `L` mode greyscale image
    a = np.zeros(scene.camera.resolution, dtype=np.uint8)

    # scale depth against range (0.0 - 1.0)
    depth_float = (depth - depth.min()) / depth.ptp()

    # convert depth into 0 - 255 uint8
    depth_int = (depth_float * 255).round().astype(np.uint8)
    # assign depth to correct pixel locations
    a[pixel_ray[:, 0], pixel_ray[:, 1]] = depth_int
    # create a PIL image from the depth queries
    if return_image:
        return PIL.Image.fromarray(a)
    return a


if __name__ == '__main__':
    pil_image = gltf_raytrace(None, return_image=True)
    pil_image.save('test-image.png', format='png')
