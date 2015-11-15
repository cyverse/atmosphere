from rest_framework import renderers


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

    By setting 'display_edit_forms' to False in the context,
    you can display the API without forms.
    """

    def get_context(self, *args, **kwargs):
        ctx = super(BrowsableAPIRenderer, self).get_context(*args, **kwargs)
        # ctx['display_edit_forms'] = False
        return ctx
