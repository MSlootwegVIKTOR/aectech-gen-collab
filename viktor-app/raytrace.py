from io import BytesIO
from pathlib import Path

import numpy as np
import PIL.Image

import trimesh
from viktor import File


def get_trimesh_object(gltf_file: File = None, glb: File = None, test=False):
    if test:
        gltf = Path(__file__).parent / 'files' / 'geometry.stl'
        file_type = 'stl'
    elif gltf_file:
        gltf = BytesIO(gltf_file.getvalue_binary())
        file_type = 'gltf'
    elif glb:
        gltf = BytesIO(glb.getvalue_binary())
        file_type = 'glb'
    else:
        # test on a simple mesh
        gltf = Path(__file__).parent / 'files' / 'surroundings.gltf'
        file_type = 'glb'
    return trimesh.load(gltf, file_type=file_type, force='mesh')


def gltf_raytrace(gltf_file: File = None, glb: File = None, return_image=False, test=False, discretization_value=1.5, bounding_box=None):
    mesh = get_trimesh_object(gltf_file, glb, test)

    # scene will have automatically generated camera and lights
    scene = mesh.scene()
    if bounding_box is not None:
        min, max = bounding_box
    else:
        min, max = scene.bounding_box.bounds
    resolution_x = int((max[0] - min[0]) / discretization_value)
    resolution_y = int((max[1] - min[1]) / discretization_value)

    [_, y_min, _] = min
    [x_max, _, _] = max

    # any of the automatically generated values can be overridden
    # set resolution, in pixels
    RESOLUTION = [resolution_x, resolution_y]
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
    return {"x": x_max, "y": y_min, "map": a}


if __name__ == '__main__':
    pil_image = gltf_raytrace(return_image=True, test=True)
    pil_image.save('test-image.png', format='png')
