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
