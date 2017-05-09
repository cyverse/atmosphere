import dateutil.parser
import freezegun
from behaving import environment as benv

PERSONAS = {}


def before_all(context):
    benv.before_all(context)


def after_all(context):
    benv.after_all(context)


def before_feature(context, feature):
    benv.before_feature(context, feature)


def after_feature(context, feature):
    benv.after_feature(context, feature)


def before_scenario(context, scenario):
    benv.before_scenario(context, scenario)
    context.personas = PERSONAS


def after_scenario(context, scenario):
    benv.after_scenario(context, scenario)


def before_step(context, step):
    if hasattr(context, 'frozen_current_time'):
        if not hasattr(context, 'freezer'):
            context.freezer = freezegun.freeze_time(context.frozen_current_time, tick=True)
        else:
            context.freezer.time_to_freeze = dateutil.parser.parse(context.frozen_current_time)
        context.freezer.start()


def after_step(context, step):
    if hasattr(context, 'freezer') and hasattr(context, 'frozen_current_time'):
        context.freezer.stop()
