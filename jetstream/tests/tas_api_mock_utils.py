from jetstream import exceptions as jetstream_exceptions


def _make_mock_tacc_api_post(context, is_tas_up=True):
    def _mock_tacc_api_post(*args, **kwargs):
        raise NotImplementedError

    return _mock_tacc_api_post


def _get_tas_projects(context):
    data = {}
    data['status'] = 'success'
    data['result'] = context.tas_projects
    return data


def _get_xsede_to_tacc_username(context, url):
    xsede_username = url.split('/v1/users/xsede/')[-1]
    if xsede_username not in context.xsede_to_tacc_username_mapping:
        data = {'status': 'error', 'message': 'No user found for XSEDE username {}'.format(xsede_username),
                'result': None}
    else:
        data = {'status': 'success', 'message': None, 'result': context.xsede_to_tacc_username_mapping[xsede_username]}
    return data


def _get_user_projects(context, url):
    tacc_username = url.split('/v1/projects/username/')[-1]
    project_names = list(context.tacc_username_to_tas_project_mapping.get(tacc_username, []))
    user_projects = [project for project in context.tas_projects if project['chargeCode'] in project_names]
    data = {'status': 'success', 'message': None, 'result': user_projects}
    return data


def _make_mock_tacc_api_get(context, is_tas_up=True):
    def _mock_tacc_api_get_down(*args, **kwargs):
        raise jetstream_exceptions.TASAPIException('503 Service Unavailable')

    if not is_tas_up:
        return _mock_tacc_api_get_down

    def _mock_tacc_api_get(*args, **kwargs):
        url = args[0]
        assert isinstance(url, basestring)
        if url.endswith('/v1/projects/resource/Jetstream'):
            data = _get_tas_projects(context)
        elif '/v1/users/xsede/' in url:
            data = _get_xsede_to_tacc_username(context, url)
        elif '/v1/projects/username/' in url:  # This can return 'Inactive', 'Active', and 'Approved' allocations. Maybe more.
            data = _get_user_projects(context, url)
        else:
            raise ValueError('Unknown URL: {}'.format(url))
        if not data:
            raise jetstream_exceptions.TASAPIException('Invalid Response')
        return None, data

    return _mock_tacc_api_get


def reset_mock_tas_fixtures(context):
    context.xsede_to_tacc_username_mapping = {}
    context.tacc_username_to_tas_project_mapping = {}
    context.tas_projects = []