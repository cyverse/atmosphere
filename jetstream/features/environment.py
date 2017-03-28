def before_feature(context, feature):
    import pydevd
    pydevd.settrace('127.0.0.1', port=4567, stdoutToServer=True, stderrToServer=True, suspend=False)


def before_scenario(context, scenario):
    pass
