"""
 RESTful Reporting API
"""
import numpy as np
import pandas as pd
import pytz
from dateutil.parser import parse
from django.db.models import Q
from rest_framework import exceptions
from rest_framework import status
from rest_framework.settings import api_settings

from api.renderers import PandasExcelRenderer
from api.v2.exceptions import failure_response
from api.v2.serializers.details import InstanceReportingSerializer
from api.v2.views.base import AuthViewSet
from core.models import Instance


class ReportingViewSet(AuthViewSet):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [PandasExcelRenderer, ]
    pagination_class = None
    serializer_class = InstanceReportingSerializer
    ordering_fields = ('id', 'start_date')
    http_method_names = ['get', 'head', 'options', 'trace']

    class Meta:
        model = Instance

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
            'excel_writer_hook': self.create_excel_file,
            'headers_ordering': ["id", "instance_id", "username", "staff_user", "provider", "start_date", "end_date",
                                 "image_name", "version_name", "size.active", "size.start_date", "size.end_date",
                                 "size.name", "size.id", "size.uuid", "size.url", "size.alias", "size.cpu", "size.mem",
                                 "size.disk", "is_featured_image", "hit_active", "hit_deploy_error", "hit_error",
                                 "hit_aborted", "hit_active_or_aborted", "hit_active_or_aborted_or_error"],
        }

    def set_frequency(self):
        freq = self.request.query_params.get('frequency', 'MS').lower()
        if freq in ['as', 'yearly']:
            return 'AS'
        elif freq in ['qs', 'quarterly']:
            return 'QS'
        elif freq in ['ms', 'monthly']:
            return 'MS'
        elif freq in ['w', 'weekly']:
            return 'W'
        elif freq in ['d', 'daily']:
            return 'D'
        elif freq in ['h', 'hourly']:
            return 'H'
        else:  # Invalid defaults: Monthly
            return 'MS'

    def create_excel_file(self, raw_dataframe, writer):
        # Return if dataframe is empty
        if len(raw_dataframe.index) <= 1:
            return None
        frequency = self.set_frequency()
        new_datasets = self._create_datasets(raw_dataframe, frequency)
        writer = self._format_and_print_workbook(writer, new_datasets, frequency)
        return writer

    @staticmethod
    def _create_datasets(raw_dataframe, frequency):
        raw_dataframe['start_date'] = raw_dataframe['start_date'].apply(pd.to_datetime)
        raw_dataframe['end_date'] = raw_dataframe['end_date'].apply(pd.to_datetime)

        # Create some new tables
        global_summary_data = raw_dataframe.set_index('start_date').query('is_featured_image == 1').resample(
            frequency).aggregate([np.mean, np.sum])
        user_summary_data = raw_dataframe.query('is_featured_image == 1').set_index(['start_date', 'username'])
        image_summary_data = raw_dataframe.query('is_featured_image == 1').set_index(['start_date', 'image_name'])

        # Group things, filter things, drop unneeded columns, rename things
        global_summary_data = global_summary_data.drop(
            ['is_featured_image', 'hit_active', 'hit_aborted', 'hit_deploy_error', 'hit_error', 'id', 'size.active',
             'size.cpu', 'size.disk', 'size.id', 'size.mem'], axis=1)
        global_summary_data.index.rename('Start Date', inplace=True)
        global_summary_data.columns = [
            'Average of Active/Aborted', 'Sum of Active/Aborted',
            'Average of Active/Aborted/Error', 'Sum of Active/Aborted/Error'
        ]

        user_summary_data = user_summary_data.groupby(
            [pd.Grouper(freq=frequency, level=0), user_summary_data.index.get_level_values(1)]).aggregate(
            [np.mean, np.sum])
        user_summary_data = user_summary_data.drop(
            ['is_featured_image', 'hit_error', 'id', 'size.active', 'size.cpu', 'size.disk', 'size.id', 'size.mem'],
            axis=1)
        user_summary_data.index.rename(['Start Date', 'Username'], inplace=True)
        user_summary_data.columns = [
            'Average of Active', 'Sum of Active',
            'Average of Deploy Error', 'Sum of Deploy Error',
            'Average of Aborted', 'Sum of Aborted',
            'Average of Active/Aborted', 'Sum of Active/Aborted',
            'Average of Active/Aborted/Error', 'Sum of Active/Aborted/Error'
        ]

        image_summary_data = image_summary_data.groupby(
            [pd.Grouper(freq=frequency, level=0), image_summary_data.index.get_level_values(1)]).aggregate(
            [np.mean, np.sum])
        image_summary_data = image_summary_data.drop(
            ['is_featured_image', 'hit_active', 'hit_aborted', 'hit_deploy_error', 'hit_error', 'id', 'size.active',
             'size.cpu', 'size.disk', 'size.id', 'size.mem'], axis=1)
        image_summary_data.index.rename(['Start Date', 'Image Name'], inplace=True)
        image_summary_data.columns = [
            'Average of Active/Aborted', 'Sum of Active/Aborted',
            'Average of Active/Aborted/Error', 'Sum of Active/Aborted/Error'
        ]
        raw_dataframe = raw_dataframe.drop(
            ['size.id', 'size.uuid', 'size.alias', 'size.active', 'size.start_date', 'size.end_date', 'size.url'],
            axis=1)

        return {
            'User Summary': user_summary_data,
            'Image Summary': image_summary_data,
            'Global Summary': global_summary_data,
            'Raw Data': raw_dataframe
        }

    @staticmethod
    def _format_and_print_workbook(writer, new_datasets, frequency):
        raw_dataframe = new_datasets['Raw Data']
        user_summary_data = new_datasets['User Summary']
        image_summary_data = new_datasets['Image Summary']
        global_summary_data = new_datasets['Global Summary']

        # Write summary data to the writer
        if frequency in ['AS']:
            summary_format = 'yyyy'
        elif frequency in ['MS', 'QS']:
            summary_format = 'mmmm yyyy'
        elif frequency in ['W', 'D']:
            summary_format = 'mmm d yyyy'
        else:
            summary_format = 'mmm d yyyy hh:mm:ss'

        writer.datetime_format = summary_format
        global_summary_data.to_excel(writer, 'Monthly Summary')
        image_summary_data.to_excel(writer, 'Image Summary')
        user_summary_data.to_excel(writer, 'User Summary')

        writer.datetime_format = 'mmm d yyyy hh:mm:ss'
        raw_dataframe.to_excel(writer, sheet_name='Raw Data')

        # FORMAT content:
        workbook = writer.book
        pct_format = workbook.add_format({'num_format': '0.00%'})
        name_format = workbook.add_format()
        name_format.set_align('left')

        raw_ws = writer.sheets['Raw Data']
        global_summary_ws = writer.sheets['Monthly Summary']
        image_summary_ws = writer.sheets['Image Summary']
        user_summary_ws = writer.sheets['User Summary']

        # Add sort/filter around the raw data
        row_total = len(raw_dataframe.values)
        col_total = len(raw_dataframe.columns)
        raw_ws.autofilter(
            0, 0,
            row_total, col_total)

        # Format column widths on the worksheets
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

        global_summary_ws.set_column('A:A', 34)
        global_summary_ws.set_column('B:B', 21, pct_format)
        global_summary_ws.set_column('D:D', 26, pct_format)

        image_summary_ws.set_column('A:A', 34)
        image_summary_ws.set_column('B:B', 36, name_format)
        image_summary_ws.set_column('C:C', 21, pct_format)
        image_summary_ws.set_column('E:E', 26, pct_format)

        user_summary_ws.set_column('A:A', 34)
        user_summary_ws.set_column('B:B', 13, name_format)
        user_summary_ws.set_column('C:C', 17, pct_format)
        user_summary_ws.set_column('E:E', 17, pct_format)
        user_summary_ws.set_column('G:G', 21, pct_format)
        user_summary_ws.set_column('I:I', 21, pct_format)
        user_summary_ws.set_column('K:K', 26, pct_format)

        # "Print" the writer to complete the StringIO Buffer
        writer.save()

        return writer

    def get_queryset(self):
        request_user = self.request.user
        if request_user.is_staff or request_user.is_superuser:
            instances_qs = Instance.objects.all()
        elif request_user.is_authenticated():
            instances_qs = Instance.for_user(request_user)
        else:
            raise exceptions.NotAuthenticated()
        query_params = self.request.query_params
        query = self.get_filter_query(query_params)

        queryset = instances_qs.filter(query)
        return queryset

    @staticmethod
    def get_filter_query(query_params):
        query = Q()

        if 'provider_id' in query_params:
            provider_id_list = query_params.getlist('provider_id')
            provider_ids = [int(pid) for pid in provider_id_list]
            query &= Q(created_by_identity__provider__id__in=provider_ids)
        # NOTE: All times assumed UTC.. Trust me on this one.
        if 'start_date' in query_params:
            start_date = parse(query_params['start_date']).replace(tzinfo=pytz.utc)
            query &= Q(start_date__gt=start_date)

        if 'end_date' in query_params:
            end_date = parse(query_params['end_date']).replace(tzinfo=pytz.utc)
            query &= Q(start_date__lt=end_date)
        if 'username' in query_params:
            query &= Q(created_by__username=query_params['username'])

        return query

    def get(self, request, pk=None):
        """
        Force an abnormal behavior for 'details' calls (force a list call)
        """
        return self.list(request)

    def list(self, request, *args, **kwargs):
        """
        Force an abnormal behavior when no query_params are passed
        """
        query_params = self.request.query_params
        if not query_params.items():
            return failure_response(status.HTTP_400_BAD_REQUEST,
                                    "The reporting API should be accessed via the query parameters:"
                                    " ['start_date', 'end_date', 'provider_id']")
        try:
            results = super(ReportingViewSet, self).list(request, *args, **kwargs)
        except ValueError:
            return failure_response(status.HTTP_400_BAD_REQUEST, 'Invalid filter parameters')
        return results
