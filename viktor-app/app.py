import datetime
from io import BytesIO
from pathlib import Path

import requests
from viktor import ViktorController, UserError, progress_message
from viktor.external.word import render_word_file, WordFileImage, WordFileTag
from viktor.parametrization import ViktorParametrization, ActionButton, DateField, TextField, Page, Text, \
    Image, OptionField, NumberField, Table, DownloadButton
from viktor.result import DownloadResult
from viktor.utils import convert_word_to_pdf
from viktor.views import GeometryView, GeometryResult, PDFView, PDFResult, ImageView, \
    ImageResult
from raytrace import gltf_raytrace
from forma_storage import get_surroundings, get_terrain
from viktor_subdomain.helper_functions import set_environment_variables
from generation import generate


set_environment_variables()

DESIGN_OPTIONS_DEFAULT = [
    {"x": 0, "y": 0, "height": 100, "depth": 30, "width": 30}
]


class Parametrization(ViktorParametrization):
    introduction = Page('Introduction')
    introduction.intro_text = Text(""" # Welcome to the Collaboration app
Using different platforms, the goal is to demonstrate how different groups and expertise can collaborate.
    """)
    introduction.viktor_and_forma_logo = Image('viktor-and-forma.png', max_width=900)
    introduction.stable_diffusion_logo = Image('Stable-Diffusion-Logo.png', max_width=400)
    analysis = Page('Analysis', views=['get_geometry_view', 'create_result'])
    analysis.select_geometry = OptionField('Select geometry for previews', options=['Surroundings', 'Terrain'], default='Terrain')
    analysis.design_options = Table('Design options', default=DESIGN_OPTIONS_DEFAULT)
    analysis.design_options.x = NumberField('x')
    analysis.design_options.y = NumberField('y')
    analysis.design_options.height = NumberField('Height')
    analysis.design_options.depth = NumberField('Depth')
    analysis.design_options.width = NumberField('Width')
    analysis.run_analysis_btn = ActionButton('Run analysis', method='run_analysis')

    reporting = Page('Reporting', views=['pdf_view'])
    reporting.client_name = TextField('Client name', "John Doe")
    reporting.company = TextField('Company', "AECTech inc.")
    reporting.date = DateField('Date', default=datetime.date.today())
    reporting.download_word_document_btn = DownloadButton('Download report as docx', 'download_word_file')


class Controller(ViktorController):
    label = 'Generative Collaboration'
    parametrization = Parametrization

    def run_analysis(self, params, **kwargs):
        progress_message('Start generation')
        generate(params)

    def generate_word_document(self, params):
        # Create emtpy components list to be filled later
        components = []

        # Fill components list with data
        components.append(WordFileTag("client_name", params.analysis.client_name))
        components.append(WordFileTag("company", params.analysis.company))
        components.append(WordFileTag("date", str(params.analysis.date)))

        # Place image
        gltf = self._get_gltf(params)
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

    @PDFView("Report", duration_guess=5)
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

    @staticmethod
    def _get_gltf(params):
        if params.analysis.select_geometry == 'Surroundings':
            return get_surroundings()
        if params.analysis.select_geometry == 'Terrain':
            return get_terrain()
        raise UserError('Select a geometry to visualize')

    @GeometryView('Forma Geometry view', duration_guess=10)
    def get_geometry_view(self, params, **kwargs):
        geometry = self._get_gltf(params)
        return GeometryResult(geometry)

    @ImageView("Ray-tracing", duration_guess=10)
    def create_result(self, params, **kwargs):
        geometry = self._get_gltf(params)
        pil_image = gltf_raytrace(glb=geometry, return_image=True)
        image = BytesIO()
        pil_image.save(image, format='png')
        return ImageResult(image)

    def download_word_file(self, params, **kwargs):
        word_file = self.generate_word_document(params)
        return DownloadResult(word_file, "document.docx")
