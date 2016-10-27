"""
 RESTful Reporting API
"""
from dateutil.parser import parse

from django.conf import settings
from django.template.loader import render_to_string
from django.template import Context
from django.db.models import Q

from rest_framework.response import Response
from rest_framework import status

from api import permissions
from api.pagination import StandardResultsSetPagination
from api.v2.views.base import AuthViewSet
from api.v2.exceptions import failure_response
from api.v2.serializers.details import InstanceReportingSerializer

from core.models import AtmosphereUser as User
from core.models import Instance, Volume
from rest_framework_csv.renderers import CSVRenderer
from rest_framework.settings import api_settings
from django.http import StreamingHttpResponse

import xlwt, pandas, numpy, pytz
from datetime import datetime, date
from StringIO import StringIO

class PandasExcelRenderer(CSVRenderer):
    """
    Renderer which serializes to XLS
    """

    media_type = 'application/vnd.ms-excel'
    format = 'xlsx'

    def render(self, data, media_type=None, renderer_context={}):
        sheetname = renderer_context.get('sheetname', 'raw_data')
        filename = renderer_context.get('filename', 'workbook.xlsx')
        header_list = ["id", "instance_id", "username", "staff_user", "provider", "start_date", "end_date", "image_name", "version_name", "size.active", "size.start_date", "size.end_date", "size.name", "size.id", "size.uuid", "size.url", "size.alias", "size.cpu", "size.mem", "size.disk", "is_featured_image", "hit_active", "hit_deploy_error", "hit_error", "hit_aborted", "hit_active_or_aborted", "hit_active_or_aborted_or_error"]
        table = self.tablize(data, header=header_list)
        #table = self.tablize(data)
        headers = table.pop(0)
        df = pandas.DataFrame(table, columns=headers)
        #Save to StringIO
        sio = StringIO()
        writer = pandas.ExcelWriter(sio, engine='xlsxwriter')
        if 'writer_callback' in renderer_context:
            callback = renderer_context.get('writer_callback')
            df, writer = callback(df, writer, sheetname)
        # Get access to the workbook and sheet

        writer.save()

        # StringIO to response:
        sio.seek(0)
        workbook = sio.getvalue()
        response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response


class ReportingViewSet(AuthViewSet):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [PandasExcelRenderer, ]
    pagination_class = None
    serializer_class = InstanceReportingSerializer
    ordering_fields = ('id', 'start_date')
    http_method_names = ['get', 'head', 'options', 'trace']

    class Meta:
        model = Instance

    def write_excel(self, df, writer, sheetname):
        if len(df.index) <= 1:
            return (df, writer)
        df['start_date'] = df['start_date'].apply(pandas.to_datetime)
        df['end_date'] = df['end_date'].apply(pandas.to_datetime)
        new_df = df.set_index(['start_date', 'image_name'])
        new_df = new_df.groupby([pandas.Grouper(freq='MS', level=0), new_df.index.get_level_values(1)]).mean()
        new_df = new_df.query('is_featured_image == 1')
        new_df = new_df.drop(['is_featured_image', 'hit_active', 'hit_aborted', 'hit_deploy_error', 'hit_error', 'id', 'size.active', 'size.cpu', 'size.disk', 'size.id', 'size.mem'], axis=1)
        new_df.index.rename(['Start Date', 'Image Name'], inplace=True)
        new_df.columns = ['Average of Active/Aborted', 'Average of Active/Aborted/Error']

        #Write to excel.
        writer.datetime_format = 'mmm yyyy'
        new_df.to_excel(writer, 'Summary')

        writer.datetime_format = 'mmm d yyyy hh:mm:ss'
        df.to_excel(writer, sheet_name=sheetname)

        import ipdb;ipdb.set_trace()

        # Set workbook formatting after writing
        workbook  = writer.book
        pct_format = workbook.add_format({'num_format': '0.00%'})
        name_format = workbook.add_format({'align': 'left'})

        raw_ws = writer.sheets[sheetname]
        summary_ws = writer.sheets['Summary']

        # Set worksheet formatting
        raw_ws.autofilter(0,0,len(df.values),len(df.columns))

        summary_ws.set_column('A2:A', 34)
        summary_ws.set_column('B:B', 36, name_format)
        summary_ws.set_column('C:C', 21, pct_format)
        summary_ws.set_column('D:D', 26, pct_format)
        return (new_df, writer)

    def list(self, request, *args, **kwargs):
        """
        """
        query_params = self.request.query_params
        if not query_params.items():
            return failure_response(status.HTTP_400_BAD_REQUEST, "The reporting API should be accessed via the query parameters: ['start_date', 'end_date', 'provider_id']")
        return super(ReportingViewSet, self).list(request, *args, **kwargs)

    def get_renderer_context(self):
        """
        Returns a dict that is passed through to Renderer.render(),
        as the `renderer_context` keyword argument.
        """
        # Note: Additionally 'response' will also be added to the context,
        #       by the Response object.
        return {
            'view': self,
            'args': getattr(self, 'args', ()),
            'kwargs': getattr(self, 'kwargs', {}),
            'request': getattr(self, 'request', None),
            'filename': 'reporting.xlsx',
            'writer_callback': self.write_excel,
        }

    def _filter_by_request(self):
        instances_qs = Instance.objects.all()
        query_params = self.request.query_params
        query = Q()

        if 'provider_id' in query_params:
            provider_id_list = query_params.getlist('provider_id')
            provider_ids = [int(pid) for pid in provider_id_list]
            query &= Q(created_by_identity__provider__id__in=provider_ids)
        #NOTE: All times assumed UTC.. Trust me on this one.
        if 'start_date' in query_params:
            start_date = parse(query_params['start_date']).replace(tzinfo=pytz.utc)
            query &= Q(start_date__gt=start_date)

        if 'end_date' in query_params:
            end_date = parse(query_params['end_date']).replace(tzinfo=pytz.utc)
            query &= Q(start_date__lt=end_date)

        instances_qs = Instance.objects.filter(query)
        return instances_qs

    def get_queryset(self):
        return self._filter_by_request()

    def get(self, request, pk=None):
        return self.list(request)

