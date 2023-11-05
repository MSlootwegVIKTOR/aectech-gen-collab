import json
from io import BytesIO
from pathlib import Path

import requests
from viktor import ViktorController, UserError
from viktor.external.word import render_word_file, WordFileImage, WordFileTag
from viktor.parametrization import ViktorParametrization, ActionButton, FileField, DateField, TextField, Page, Text, \
    Image, OptionField
from viktor.result import DownloadResult
from viktor.utils import convert_word_to_pdf
from viktor.views import GeoJSONView, GeoJSONResult, GeometryView, GeometryResult, PDFView, PDFResult, ImageView, \
    ImageResult
from raytrace import gltf_raytrace
from forma_storage import get_surroundings, get_terrain
from viktor_subdomain.helper_functions import set_environment_variables


set_environment_variables()


class Parametrization(ViktorParametrization):
    introduction = Page('Introduction')
    introduction.intro_text = Text(""" # Welcome to the Collaboration app
Using different platforms, the goal is to demonstrate how different groups and expertise can collaborate.
    """)
    introduction.viktor_and_forma_logo = Image('viktor-and-forma.png', max_width=900)
    introduction.stable_diffusion_logo = Image('Stable-Diffusion-Logo.png', max_width=400)
    analysis = Page('Analysis', views=['get_geojson_view', 'get_geometry_view', 'pdf_view', 'create_result'])
    analysis.client_name = TextField('Client name')
    analysis.company = TextField('Company')
    analysis.date = DateField('Date')
    analysis.import_from_forma_btn = ActionButton('Import input from Forma', 'import_from_forma')
    analysis.geojson_file = FileField('Upload Geojson file', file_types=['.geojson'])
    analysis.gltf_file = FileField('Upload GLTF file', file_types=['.gltf'])
    analysis.select_geometry = OptionField('Select geometry', options=['Surroundings', 'Terrain'], default='Terrain')


class Controller(ViktorController):
    label = 'Generative Collaboration'
    parametrization = Parametrization

    def import_from_forma(self, params, **kwargs):
        return

    @GeoJSONView('GeoJSON view', duration_guess=1)
    def get_geojson_view(self, params, **kwargs):
        if params.analysis.geojson_file:
            geojson = json.loads(params.analysis.geojson_file.file.getvalue())
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

    def generate_word_document(self, params):
        # Create emtpy components list to be filled later
        components = []

        # Fill components list with data
        components.append(WordFileTag("client_name", params.analysis.client_name))
        components.append(WordFileTag("company", params.analysis.company))
        components.append(WordFileTag("date", str(params.analysis.date)))

        # Place image
        if params.analysis.gltf_file:
            gltf = params.analysis.gltf_file.file
        else:
            gltf = None
        figure = gltf_raytrace(gltf, return_image=True)
        image = BytesIO()
        figure.save(image, format='png')
        word_file_figure = WordFileImage(image, "figure", width=500)
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

    @GeometryView('Forma Geometry view', duration_guess=10)
    def get_geometry_view(self, params, **kwargs):
        if params.analysis.select_geometry == 'Surroundings':
            geometry = get_surroundings()
        elif params.analysis.select_geometry == 'Terrain':
            geometry = get_terrain()
        else:
            raise UserError('Select a geometry to visualize')
        return GeometryResult(geometry)

    @ImageView("Ray-tracing", duration_guess=10)
    def create_result(self, params, **kwargs):
        geometry = get_surroundings()
        pil_image = gltf_raytrace(glb=geometry, return_image=True)
        image = BytesIO()
        pil_image.save(image, format='png')
        return ImageResult(image)

    def download_word_file(self, params, **kwargs):
        word_file = self.generate_word_document(params)
        return DownloadResult(word_file, "document.docx")
