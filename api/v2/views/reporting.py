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
from django.http import StreamingHttpResponse

import xlwt, pandas, numpy
from datetime import datetime, date
from StringIO import StringIO

class ExcelRenderer(CSVRenderer):
    """
    Renderer which serializes to XLS
    """

    media_type = 'application/vnd.ms-excel'
    format = 'xlsx'

    def render(self, data, media_type=None, renderer_context={}):
        sheetname = renderer_context.get('sheetname', 'raw_data')
        filename = renderer_context.get('filename', 'workbook.xlsx')

        table = self.tablize(data)
        headers = table.pop(0)
        df = pandas.DataFrame(table, columns=headers)
        #Save to StringIO
        sio = StringIO()
        writer = pandas.ExcelWriter(sio, engine='xlsxwriter')
        df.to_excel(writer, sheet_name=sheetname)
        # Get access to the workbook and sheet
        if 'excel_callback' in renderer_context:
            callback = renderer_context.get('excel_callback')
            callback(df, writer)

        writer.save()

        # StringIO to response:
        sio.seek(0)
        workbook = sio.getvalue()
        response = StreamingHttpResponse(workbook, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response


class ReportingViewSet(AuthViewSet):
    renderer_classes = [ExcelRenderer, ]
    pagination_class = None
    serializer_class = InstanceReportingSerializer
    ordering_fields = ('id', 'start_date')
    http_method_names = ['get', 'head', 'options', 'trace']

    class Meta:
        model = Instance

    def add_to_worksheet(self, df, writer):

        table = pandas.pivot_table(
            df, index=[
                'is_featured_image','staff_user','start_date', 'image_name'],
            aggfunc={
                'hit_active_or_aborted_or_error': [numpy.mean],
                'hit_active_or_aborted': [numpy.mean]}
        )
        table.query('is_featured_image == 1')
        table.query('staff_user == 1')
        table.to_excel(writer, 'pivot')
        # Get access to the workbook and sheet
        # workbook = writer.book
        # worksheet = writer.sheets['raw_data']
        return (df, writer)

    def get_renderer_context(self):
        return {
            'filename': 'reporting.xlsx',
            'excel_callback': self.add_to_worksheet,
        }

    def _filter_by_request(self):
        instances_qs = Instance.objects.all()
        query_params = self.request.query_params

        if 'provider_id' in query_params:
            provider_id_list = query_params.getlist('provider_id')
            provider_ids = [int(pid) for pid in provider_id_list]
            instances_qs &= Instance.objects.filter(created_by_identity__provider__id__in=provider_ids)

        if 'start_date' in query_params:
            start_date = parse(query_params['start_date'])
            instances_qs &= Instance.objects.filter(start_date__gt=start_date)

        if 'end_date' in query_params:
            end_date = parse(query_params['end_date'])
            query = Q(end_date__lt=end_date)
            #FIXME: not sure how to address this, but in some cases,
            # you want to set an 'end-date' for the reporting, but *not*
            # explicitly setting an end-date on the instance.
            # For now, i've recorded this idea as 'include_current'
            # To avoid 'missing' metrtics, we will always include current instances.
            if query_params.get('include_current') != False:
                query |= Q(end_date__isnull=True)
            instances_qs &= Instance.objects.filter(query)

        return instances_qs

    def get_queryset(self):
        return self._filter_by_request()

    def get(self, request, pk=None):
        return self.list(request)

