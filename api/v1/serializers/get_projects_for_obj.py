def get_projects_for_obj(serializer, related_obj):
    """
    Using <>Serializer.request_user, find the projects
    the related object is a member of
    """
    if not serializer.request_user:
        return None
    projects = related_obj.get_projects(serializer.request_user)
    return [p.uuid for p in projects]
