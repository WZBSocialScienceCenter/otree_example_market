from channels.routing import route_class

from otree.channels import consumers as otree_consumers
from otree.channels.routing import channel_routing

from .admin_extensions.channels_consumers import ExportDataChannelsExtension

channel_routing = [route for route in channel_routing if route.consumer.__name__ != 'ExportData']

channel_routing.append(route_class(
    ExportDataChannelsExtension,
    path=r"^/export/$")
)
