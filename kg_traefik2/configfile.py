from typing import Optional, Any, Sequence, Mapping

from kubragen.configfile import ConfigFileOutput, ConfigFileOutput_Dict, ConfigFile_Extend, \
    ConfigFileExtension, ConfigFileExtensionData
from kubragen.merger import Merger
from kubragen.option import OptionDef
from kubragen.options import Options, option_root_get, OptionGetter


class Traefik2ConfigFileOptions(Options):
    """
    Options for Traefik 2 config file.

    .. list-table::
        :header-rows: 1

        * - option
          - description
          - allowed types
          - default value
        * - config |rarr| merge_config
          - Mapping to merge into final config
          - Mapping
          -
    """
    def define_options(self) -> Optional[Any]:
        """
        Declare the options for the Traefik 2 config file.

        :return: The supported options
        """
        return {
            'config': {
                'merge_config': OptionDef(allowed_types=[Mapping]),
            },
        }


class Traefik2ConfigFile(ConfigFile_Extend):
    """
    Traefik 2 main configuration file in TOML/Yaml format.
    """
    options: Traefik2ConfigFileOptions

    def __init__(self, options: Optional[Traefik2ConfigFileOptions] = None,
                 extensions: Optional[Sequence[ConfigFileExtension]] = None):
        super().__init__(extensions)
        if options is None:
            options = Traefik2ConfigFileOptions()
        self.options = options

    def option_get(self, name: str):
        return option_root_get(self.options, name)

    def init_value(self, options: OptionGetter) -> ConfigFileExtensionData:
        return ConfigFileExtensionData({
            'global': {
                'checkNewVersion': False,
                'sendAnonymousUsage': False,
            },
        })

    def finish_value(self, options: OptionGetter, data: ConfigFileExtensionData) -> ConfigFileOutput:
        if self.option_get('config.merge_config') is not None:
            Merger.merge(data.data, self.option_get('config.merge_config'))
        return ConfigFileOutput_Dict(data.data)
