from django.http import StreamingHttpResponse

from rest_framework import renderers
from rest_framework_csv.renderers import CSVRenderer

from StringIO import StringIO
import pandas as pd


class PandasExcelRenderer(CSVRenderer):
    """
    Renderer which serializes to XLS
    """

    media_type = 'application/vnd.ms-excel'
    format = 'xlsx'

    def render(self, data, media_type=None, renderer_context={}):
        filename = renderer_context.get('filename', 'workbook.xlsx')
        # Hard-coded headers_ordering required to force an explicit ordering, otherwise headers are sorted by key-name
        headers_ordering = renderer_context.get('headers_ordering', None)
        table = self.tablize(data, header=headers_ordering)

        headers = table.pop(0)
        raw_dataframe = pd.DataFrame(table, columns=headers)
        #Save to StringIO
        sio = StringIO()
        writer = pd.ExcelWriter(sio, engine='xlsxwriter')
        if 'excel_writer_hook' not in renderer_context:
            raise Exception("Implementation error -- Using PandasExcelRenderer without including 'excel_writer_hook' in renderer_context")

        callback = renderer_context.get('excel_writer_hook')
        writer = callback(raw_dataframe, writer)
        # ASSERT: Writer should be saved by now
        # StringIO to response:
        sio.seek(0)
        workbook = sio.getvalue()
        response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
        #FIXME: This doesn't... actually.. work. Filename == pathname.
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response


class PNGRenderer(renderers.BaseRenderer):
    media_type = "image/png"
    format = "png"
    charset = None
    render_style = "binary"

    def render(self, data, media_type=None, renderer_context=None):
        return data


class JPEGRenderer(renderers.BaseRenderer):
    media_type = "image/jpeg"
    format = "jpg"
    charset = None
    render_style = "binary"

    def render(self, data, media_type=None, renderer_context=None):
        return data


class BrowsableAPIRenderer(renderers.BrowsableAPIRenderer):
    """
    'Custom' Browsable API Renderer

    By returning an empty rendered HTML form
    you can display the API quickly, without
    having to deal with "select" queryset slow-downs.
    """

    def get_rendered_html_form(self, data, view, method, request):
        if method in ['PUT', 'POST']:
            return ""
        return super(BrowsableAPIRenderer, self).get_rendered_html_form(
            data, view, method, request)

    def get_context(self, *args, **kwargs):
        ctx = super(BrowsableAPIRenderer, self).get_context(*args, **kwargs)
        # ctx['display_edit_forms'] = False
        return ctx
