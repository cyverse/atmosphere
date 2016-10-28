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
from api.renderers import PandasExcelRenderer
from api.v2.views.base import AuthViewSet
from api.v2.exceptions import failure_response
from api.v2.serializers.details import InstanceReportingSerializer

from core.models import Instance
from rest_framework.settings import api_settings

import pandas
import pytz


class ReportingViewSet(AuthViewSet):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [PandasExcelRenderer, ]
    pagination_class = None
    serializer_class = InstanceReportingSerializer
    ordering_fields = ('id', 'start_date')
    http_method_names = ['get', 'head', 'options', 'trace']

    class Meta:
        model = Instance

    def write_excel(self, raw_dataframe, writer, sheetname):
        if len(raw_dataframe.index) <= 1:
            return (raw_dataframe, writer)
        raw_dataframe['start_date'] = raw_dataframe['start_date'].apply(pandas.to_datetime)
        raw_dataframe['end_date'] = raw_dataframe['end_date'].apply(pandas.to_datetime)

        user_summary_data = raw_dataframe.set_index(['start_date', 'username'])
        user_summary_data = user_summary_data.groupby([pandas.Grouper(freq='MS', level=0), user_summary_data.index.get_level_values(1)]).sum()
        user_summary_data = user_summary_data.query('is_featured_image == 1')
        user_summary_data = user_summary_data.drop(['is_featured_image', 'hit_error', 'id', 'size.active', 'size.cpu', 'size.disk', 'size.id', 'size.mem'], axis=1)
        user_summary_data.index.rename(['Start Date', 'Username'], inplace=True)
        user_summary_data.columns = ['Sum of Active', 'Sum of Aborted', 'Sum of Deploy Error', 'Sum of Active/Aborted', 'Sum of Active/Aborted/Error']

        image_summary_data = raw_dataframe.set_index(['start_date', 'image_name'])
        image_summary_data = image_summary_data.groupby([pandas.Grouper(freq='MS', level=0), image_summary_data.index.get_level_values(1)]).mean()
        image_summary_data = image_summary_data.query('is_featured_image == 1')
        image_summary_data = image_summary_data.drop(['is_featured_image', 'hit_active', 'hit_aborted', 'hit_deploy_error', 'hit_error', 'id', 'size.active', 'size.cpu', 'size.disk', 'size.id', 'size.mem'], axis=1)
        image_summary_data.index.rename(['Start Date', 'Image Name'], inplace=True)
        image_summary_data.columns = ['Average of Active/Aborted', 'Average of Active/Aborted/Error']
        raw_dataframe = raw_dataframe.drop(['size.id', 'size.uuid', 'size.alias', 'size.active', 'size.start_date', 'size.end_date','size.url'], axis=1)
        #Write to excel.
        writer.datetime_format = 'mmm yyyy'
        image_summary_data.to_excel(writer, 'Image Summary')
        user_summary_data.to_excel(writer, 'User Summary')

        writer.datetime_format = 'mmm d yyyy hh:mm:ss'
        raw_dataframe.to_excel(writer, sheet_name=sheetname)

        # Set workbook formatting after writing
        workbook = writer.book
        pct_format = workbook.add_format({'num_format': '0.00%'})
        name_format = workbook.add_format()
        name_format.set_align('left')

        raw_ws = writer.sheets[sheetname]
        image_summary_ws = writer.sheets['Image Summary']
        user_summary_ws = writer.sheets['User Summary']

        # Set worksheet formatting
        raw_ws.autofilter(0, 0, len(raw_dataframe.values), len(raw_dataframe.columns))
        raw_ws.set_column('C:C', 32)
        raw_ws.set_column('D:D', 13)
        raw_ws.set_column('F:F', 23)
        raw_ws.set_column('G:G', 17)
        raw_ws.set_column('H:H', 17)
        raw_ws.set_column('I:I', 34)
        raw_ws.set_column('J:J', 17)
        raw_ws.set_column('K:K', 14)
        raw_ws.set_column('L:L', 14)
        raw_ws.set_column('M:M', 14)
        raw_ws.set_column('N:N', 14)
        raw_ws.set_column('O:O', 14)
        
        image_summary_ws.set_column('A2:A', 34)
        image_summary_ws.set_column('B:B', 36, name_format)
        image_summary_ws.set_column('C:C', 21, pct_format)
        image_summary_ws.set_column('D:D', 26, pct_format)

        user_summary_ws.set_column('A2:A', 34)
        user_summary_ws.set_column('B:B', 13, name_format)
        user_summary_ws.set_column('C:C', 17)
        user_summary_ws.set_column('D:D', 17)
        user_summary_ws.set_column('E:E', 17)
        user_summary_ws.set_column('F:F', 21)
        user_summary_ws.set_column('G:G', 21)

        return (image_summary_data, writer)

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
        request_user = self.request.user
        if request_user.is_staff or request_user.is_superuser:
            instances_qs = Instance.objects.all()
        else:
            instances_qs = Instance.for_user(request_user)
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

