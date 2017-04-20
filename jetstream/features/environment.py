import freezegun


def before_feature(context, feature):
    pass


def before_scenario(context, scenario):
    pass


def after_scenario(context, scenario):
    pass


def before_step(context, step):
    if hasattr(context, 'frozen_current_time'):
        if not hasattr(context, 'freezer'):
            context.freezer = freezegun.freeze_time(context.frozen_current_time, tick=True)
        context.freezer.start()


def after_step(context, step):
    if hasattr(context, 'freezer') and hasattr(context, 'frozen_current_time'):
        context.freezer.stop()
