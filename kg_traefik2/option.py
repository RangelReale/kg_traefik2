from typing import Optional, Sequence, Mapping

from kubragen.configfile import ConfigFile
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
        * - config |rarr| traefik_config
          - Traefik 2 config file
          - str, ConfigFile
          -
        * - config |rarr| config_format
          - Config format
          - :data:`Traefik2Options.CONFIGFORMAT_TOML`, :data:`Traefik2Options.CONFIGFORMAT_YAML`
          - ```Traefik2Options.CONFIGFORMAT_TOML```
        * - config |rarr| traefik_args
          - traefik args
          - Sequence
          - []
        * - config |rarr| ports
          - ports configuration
          - Sequence[:class:`Traefik2OptionsPort`]
          - []
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

    CONFIGFORMAT_TOML = 'toml'
    CONFIGFORMAT_YAML = 'yaml'

    def define_options(self):
        """
        Declare the options for the Traefik 2 builder.

        :return: The supported options
        """
        return {
            'basename': OptionDef(required=True, default_value='traefik2', allowed_types=[str]),
            'namespace': OptionDef(required=True, default_value='default', allowed_types=[str]),
            'config': {
                'traefik_config': OptionDef(allowed_types=[str, ConfigFile]),
                'config_format': OptionDef(default_value=self.CONFIGFORMAT_TOML, allowed_types=[str]),
                'traefik_args': OptionDef(required=True, default_value=[], allowed_types=[Sequence]),
                'ports': OptionDef(required=True, default_value=[], allowed_types=[Sequence]),
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
