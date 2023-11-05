import json
from io import BytesIO
from pathlib import Path

import PIL
import requests
import numpy as np
from matplotlib import pyplot as plt
from viktor import ViktorController, File
from viktor.external.word import render_word_file, WordFileImage, WordFileTag
from viktor.parametrization import ViktorParametrization, ActionButton, FileField, DateField, TextField
from viktor.result import DownloadResult
from viktor.utils import convert_word_to_pdf
from viktor.views import GeoJSONView, GeoJSONResult, GeometryView, GeometryResult, PDFView, PDFResult, ImageView, \
    ImageResult
from raytrace import gltf_raytrace

class Parametrization(ViktorParametrization):
    client_name = TextField('Client name')
    company = TextField('Company')
    date = DateField('Date')
    import_from_forma_btn = ActionButton('Import input from Forma', 'import_from_forma')
    geojson_file = FileField('Upload Geojson file', file_types=['.geojson'])
    gltf_file = FileField('Upload GLTF file', file_types=['.gltf'])
    aps_base64_auth = TextField('APS Base 64')


class Controller(ViktorController):
    label = 'Generative Collaboration'
    parametrization = Parametrization

    def import_from_forma(self, params, **kwargs):
        return

    @GeoJSONView('GeoJSON view', duration_guess=1)
    def get_geojson_view(self, params, **kwargs):
        if params.geojson_file:
            geojson = json.loads(params.geojson_file.file.getvalue())
        else:
            geojson = {
              "type": "FeatureCollection",
              "features": [
                {
                  "type": "Feature",
                  "properties": {},
                  "geometry": {
                    "type": "Point",
                    "coordinates": []
                  }
                }
              ]
            }
        return GeoJSONResult(geojson)

    @GeometryView('Geometry view', duration_guess=1)
    def get_geometry_view(self, params, **kwargs):
        geometry = geometry = File.from_url("https://github.com/KhronosGroup/glTF-Sample-Models/raw/master/2.0/CesiumMilkTruck/glTF-Binary/CesiumMilkTruck.glb")
        if params.gltf_file:
            geometry = params.gltf_file.file
        return GeometryResult(geometry)

    def generate_word_document(self, params):
        # Create emtpy components list to be filled later
        components = []

        # Fill components list with data
        components.append(WordFileTag("client_name", params.client_name))
        components.append(WordFileTag("company", params.company))
        components.append(WordFileTag("date", str(params.date)))

        # Place image
        figure = self.create_figure(params)
        word_file_figure = WordFileImage(figure, "figure", width=500)
        components.append(word_file_figure)

        # Get path to template and render word file
        template_path = Path(__file__).parent / "files" / "template.docx"
        with open(template_path, 'rb') as template:
            word_file = render_word_file(template, components)

        return word_file

    @PDFView("PDF viewer", duration_guess=5)
    def pdf_view(self, params, **kwargs):
        word_file = self.generate_word_document(params)

        with word_file.open_binary() as f1:
            pdf_file = convert_word_to_pdf(f1)

        return PDFResult(file=pdf_file)
    
    @staticmethod
    def get_two_legged_aps_token(base64_auth: str) -> str:
        two_legged_res = requests.post("https://developer.api.autodesk.com/authentication/v2/token", 
                                    data={'grant_type': 'client_credentials', 'scope': "data:write"}, 
                                    headers={
                                        'Content-Type': 'application/x-www-form-urlencoded', 
                                        'Accept': "application/json", 
                                        'Authorization': f"Basic {base64_auth}"})
        two_legged_res.raise_for_status()
        access_token = two_legged_res.json()["access_token"]
        return access_token
    
    @GeometryView('Forma Geometry view', duration_guess=1)
    def get_geometry_view(self, params, **kwargs):
        if params.aps_base64_auth:
            aps_token = self.get_two_legged_aps_token(params.aps_base64_auth)
            object_res = requests.get("https://app.autodeskforma.eu/api/extension-service/installations/8ad1d7f9-4e17-4485-aa14-f2217475b5e0/storage-objects/export.gltf?authcontext=pro_nz1xbbzv0p",allow_redirects=False, headers={"Authorization": f"Bearer {aps_token}"})
            object_res.raise_for_status()
            redirect_url = object_res.headers['Location']
            geometry = File.from_url(redirect_url)
            return GeometryResult(geometry)

    @ImageView("Ray-tracing", duration_guess=10)
    def create_result(self, params, **kwargs):
        pil_image = gltf_raytrace(params.gltf_file, return_image=True)
        image = BytesIO()
        pil_image.save(image, format='png')
        return ImageResult(image)

    @staticmethod
    def create_figure(params):
        def func3(x, y):
            return (1 - x / 2 + x ** 5 + y ** 3) * np.exp(-(x ** 2 + y ** 2))

        # make these smaller to increase the resolution
        dx, dy = 0.05, 0.05

        x = np.arange(-3.0, 3.0, dx)
        y = np.arange(-3.0, 3.0, dy)
        X, Y = np.meshgrid(x, y)

        # when layering multiple images, the images need to have the same
        # extent.  This does not mean they need to have the same shape, but
        # they both need to render to the same coordinate system determined by
        # xmin, xmax, ymin, ymax.  Note if you use different interpolations
        # for the images their apparent extent could be different due to
        # interpolation edge effects

        extent = np.min(x), np.max(x), np.min(y), np.max(y)
        fig = plt.figure(frameon=False)

        Z1 = np.add.outer(range(8), range(8)) % 2  # chessboard
        im1 = plt.imshow(Z1, cmap=plt.cm.gray, interpolation='nearest',
                         extent=extent)

        Z2 = func3(X, Y)

        im2 = plt.imshow(Z2, cmap=plt.cm.viridis, alpha=.9, interpolation='bilinear',
                         extent=extent)
        png_data = BytesIO()
        fig.savefig(png_data, format='png')
        plt.close()

        return png_data

    def download_word_file(self, params, **kwargs):
        word_file = self.generate_word_document(params)

        return DownloadResult(word_file, "document.docx")
