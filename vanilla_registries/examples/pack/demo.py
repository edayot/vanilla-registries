from beet import Context
from vanilla_registries import GeneratedData


def beet_default(ctx: Context):
    a = ctx.inject(GeneratedData)
    print(a.blocks["barrel"])
