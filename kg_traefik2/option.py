from typing import Optional, Sequence, Mapping

from kubragen.option import OptionDef
from kubragen.options import Options


class Traefik2OptionsPort:
    """
    Port options for the Traefik 2 builder.

    :param name: port name
    :param port_container: port number in the container
    :param protocol: IP protocol (TCP, UDP)
    :param in_service: whether the port also appear is service definition
    :param port_service: port number on the service, if available
    """
    name: str
    port_container: int
    port_service: Optional[int]
    protocol: str
    in_service: bool

    def __init__(self, name: str, port_container: int, protocol: str = 'TCP', in_service: bool = True,
                 port_service: Optional[int] = None):
        self.name = name
        self.port_container = port_container
        self.port_service = port_service
        self.protocol = protocol
        self.in_service = in_service


class Traefik2Options(Options):
    """
    Options for the Traefik 2 builder.

    .. list-table::
        :header-rows: 1

        * - option
          - description
          - allowed types
          - default value
        * - basename
          - object names prefix
          - str
          - ```traefik2```
        * - namespace
          - namespace
          - str
          - ```default```
        * - config |rarr| traefik_args
          - traefik args
          - Sequence
          - [\
                '--entrypoints.web.Address=:80',\
                '--entryPoints.metrics.address=:9090',\
                '--metrics.prometheus=true',\
                '--metrics.prometheus.entryPoint=metrics',\
            ]
        * - config |rarr| ports
          - ports configuration
          - Sequence[:class:`Traefik2OptionsPort`]
          - [\
                Traefik2OptionsPort(name='web', port_container=80, port_service=80),\
                Traefik2OptionsPort(name='metrics', port_container=9090, in_service=False),\
            ]
        * - config |rarr| create_traefik_crd
          - whether to create the traefik crds
          - bool
          - ```True```
        * - config |rarr| enable_prometheus
          - enable prometheus
          - bool
          - ```True```
        * - config |rarr| prometheus_annotation
          - add prometheus annotations
          - bool
          - ```False```
        * - config |rarr| authorization |rarr| serviceaccount_create
          - whether to create a service account
          - bool
          - ```True```
        * - config |rarr| authorization |rarr| serviceaccount_use
          - service account to use if not creating
          - str
          -
        * - config |rarr| authorization |rarr| roles_create
          - whether create roles
          - bool
          - ```True```
        * - config |rarr| authorization |rarr| roles_bind
          - whether to bind roles to service account
          - bool
          - ```True```
        * - container |rarr| traefik2
          - traefik 2 container image
          - str
          - ```traefik:<version>```
        * - kubernetes |rarr| resources |rarr| deployment
          - Kubernetes Deployment resources
          - Mapping
          -
    """
    def define_options(self):
        """
        Declare the options for the Traefik 2 builder.

        :return: The supported options
        """
        return {
            'basename': OptionDef(required=True, default_value='traefik2', allowed_types=[str]),
            'namespace': OptionDef(required=True, default_value='default', allowed_types=[str]),
            'config': {
                'traefik_args': OptionDef(required=True, default_value=[
                    '--entrypoints.web.Address=:80',
                    '--entryPoints.metrics.address=:9090',
                    '--metrics.prometheus=true',
                    '--metrics.prometheus.entryPoint=metrics',
                ], allowed_types=[Sequence]),
                'ports': OptionDef(required=True, default_value=[
                    Traefik2OptionsPort(name='web', port_container=80, port_service=80),
                    Traefik2OptionsPort(name='metrics', port_container=9090, in_service=False),
                ], allowed_types=[Sequence]),
                'create_traefik_crd': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                'enable_prometheus': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                'prometheus_port': OptionDef(required=True, default_value=9090, allowed_types=[int]),
                'prometheus_annotation': OptionDef(required=True, default_value=False, allowed_types=[bool]),
                'authorization': {
                    'serviceaccount_create': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                    'serviceaccount_use': OptionDef(allowed_types=[str]),
                    'roles_create': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                    'roles_bind': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                },
            },
            'container': {
                'traefik2': OptionDef(required=True, default_value='traefik:v2.2', allowed_types=[str]),
            },
            'kubernetes': {
                'resources': {
                    'deployment': OptionDef(allowed_types=[Mapping]),
                }
            },
        }
