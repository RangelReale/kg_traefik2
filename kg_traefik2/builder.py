from typing import List, Optional, Sequence, Any

import yaml
from kgp_configrendertoml import ConfigFileRender_TOML

from kubragen import KubraGen
from kubragen.builder import Builder
from kubragen.configfile import ConfigFileRenderMulti, ConfigFileRender_Yaml, ConfigFileRender_RawStr
from kubragen.data import ValueData
from kubragen.exception import InvalidParamError, InvalidNameError
from kubragen.helper import QuotedStr, LiteralStr
from kubragen.object import ObjectItem, Object
from kubragen.types import TBuild, TBuildItem
from .option import Traefik2Options


class Traefik2Builder(Builder):
    """
    Traefik 2 builder.

    Based on `Traefik & Kubernetes <https://doc.traefik.io/traefik/providers/kubernetes-crd/>`_.

    .. list-table::
        :header-rows: 1

        * - build
          - description
        * - BUILD_CRD
          - creates CRDs
        * - BUILD_ACCESSCONTROL
          - creates service account, roles, and roles bindings
        * - BUILD_SERVICE
          - creates Deployment and Service

    .. list-table::
        :header-rows: 1

        * - build item
          - description
        * - BUILDITEM_SERVICE_ACCOUNT
          - ServiceAccount
        * - BUILDITEM_CLUSTER_ROLE
          - ClusterRole
        * - BUILDITEM_CLUSTER_ROLE_BINDING
          - ClusterRoleBinding
        * - BUILDITEM_DEPLOYMENT
          - Deployment
        * - BUILDITEM_SERVICE
          - Service

    .. list-table::
        :header-rows: 1

        * - object name
          - description
          - default value
        * - service
          - Service
          - ```<basename>```
        * - service-account
          - ServiceAccount
          - ```<basename>```
        * - cluster-role
          - ClusterRole
          - ```<basename>```
        * - cluster-role-binding
          - ClusterRoleBinding
          - ```<basename>```
        * - deployment
          - Deployment
          - ```<basename>```
        * - pod-label-all
          - label *app* to be used by selection
          - ```<basename>```
    """
    options: Traefik2Options
    _namespace: str
    configfile: Optional[str]

    SOURCE_NAME = 'kg_traefik2'

    BUILD_CRD: TBuild = 'crd'
    BUILD_ACCESSCONTROL: TBuild = 'accesscontrol'
    BUILD_CONFIG: TBuild = 'config'
    BUILD_SERVICE: TBuild = 'service'

    BUILDITEM_CONFIG: TBuildItem = 'config'
    BUILDITEM_SERVICE_ACCOUNT: TBuildItem = 'service-account'
    BUILDITEM_CLUSTER_ROLE: TBuildItem = 'cluster-role'
    BUILDITEM_CLUSTER_ROLE_BINDING: TBuildItem = 'cluster-role-binding'
    BUILDITEM_DEPLOYMENT: TBuildItem = 'deployment'
    BUILDITEM_SERVICE: TBuildItem = 'service'

    def __init__(self, kubragen: KubraGen, options: Optional[Traefik2Options] = None):
        super().__init__(kubragen)
        if options is None:
            options = Traefik2Options()
        self.options = options
        self.configfile = None

        self._namespace = self.option_get('namespace')

        if self.option_get('config.authorization.serviceaccount_create') is not False:
            serviceaccount_name = self.basename()
        else:
            serviceaccount_name = self.option_get('config.authorization.serviceaccount_use')
            if serviceaccount_name == '':
                serviceaccount_name = None

        if self.option_get('config.authorization.roles_create') is not False:
            role_name = self.basename()
        else:
            role_name = None

        if self.option_get('config.authorization.roles_bind') is not False:
            if serviceaccount_name is None:
                raise InvalidParamError('To bind roles a service account is required')
            if role_name is None:
                raise InvalidParamError('To bind roles the role must be created')
            rolebinding_name = self.basename()
        else:
            rolebinding_name = None

        self.object_names_init({
            'config': self.basename('-config'),
            'service': self.basename(),
            'service-account': serviceaccount_name,
            'cluster-role': role_name,
            'cluster-role-binding': rolebinding_name,
            'deployment': self.basename(),
            'pod-label-app': self.basename(),
        })

    def option_get(self, name: str):
        return self.kubragen.option_root_get(self.options, name)

    def basename(self, suffix: str = ''):
        return '{}{}'.format(self.option_get('basename'), suffix)

    def namespace(self):
        return self._namespace

    def build_names(self) -> List[TBuild]:
        return [self.BUILD_CRD, self.BUILD_ACCESSCONTROL, self.BUILD_CONFIG, self.BUILD_SERVICE]

    def build_names_required(self) -> List[TBuild]:
        ret = [self.BUILD_SERVICE]
        if self.option_get('config.create_traefik_crd') is not False:
            ret.append(self.BUILD_CRD)
        if self.option_get('config.traefik_config') is not None:
            ret.append(self.BUILD_CONFIG)
        if self.option_get('config.authorization.serviceaccount_create') is not False or \
                self.option_get('config.authorization.roles_create') is not False:
            ret.append(self.BUILD_ACCESSCONTROL)
        return ret

    def builditem_names(self) -> List[TBuildItem]:
        return [
            self.BUILDITEM_CONFIG,
            self.BUILDITEM_CLUSTER_ROLE,
            self.BUILDITEM_SERVICE_ACCOUNT,
            self.BUILDITEM_CLUSTER_ROLE_BINDING,
            self.BUILDITEM_DEPLOYMENT,
            self.BUILDITEM_SERVICE,
        ]

    def internal_build(self, buildname: TBuild) -> List[ObjectItem]:
        if buildname == self.BUILD_CRD:
            return self.internal_build_crd()
        elif buildname == self.BUILD_ACCESSCONTROL:
            return self.internal_build_accesscontrol()
        elif buildname == self.BUILD_CONFIG:
            return self.internal_build_config()
        elif buildname == self.BUILD_SERVICE:
            return self.internal_build_service()
        else:
            raise InvalidNameError('Invalid build name: "{}"'.format(buildname))

    def internal_build_crd(self) -> List[ObjectItem]:
        return self._traefik_crd()

    def internal_build_accesscontrol(self) -> List[ObjectItem]:
        ret = []

        if self.option_get('config.authorization.serviceaccount_create') is not False:
            ret.extend([
                Object({
                    'apiVersion': 'v1',
                    'kind': 'ServiceAccount',
                    'metadata': {
                        'name': self.object_name('service-account'),
                        'namespace': self.namespace(),
                    }
                }, name=self.BUILDITEM_SERVICE_ACCOUNT, source=self.SOURCE_NAME, instance=self.basename())
            ])

        if self.option_get('config.authorization.roles_create') is not False:
            ret.extend([
                Object({
                    'apiVersion': 'rbac.authorization.k8s.io/v1beta1',
                    'kind': 'ClusterRole',
                    'metadata': {
                        'name': self.object_name('cluster-role'),
                    },
                    'rules': [{
                        'apiGroups': [''],
                        'resources': ['services', 'endpoints', 'secrets'],
                        'verbs': ['get', 'list', 'watch']
                    },
                    {
                        'apiGroups': ['extensions', 'networking.k8s.io'],
                        'resources': ['ingresses', 'ingressclasses'],
                        'verbs': ['get', 'list', 'watch']
                    },
                    {
                        'apiGroups': ['extensions'],
                        'resources': ['ingresses/status'],
                        'verbs': ['update']
                    },
                    {
                        'apiGroups': ['traefik.containo.us'],
                        'resources': ['middlewares',
                                      'ingressroutes',
                                      'traefikservices',
                                      'ingressroutetcps',
                                      'ingressrouteudps',
                                      'tlsoptions',
                                      'tlsstores'],
                        'verbs': ['get', 'list', 'watch']
                    }]
                }, name=self.BUILDITEM_CLUSTER_ROLE, source=self.SOURCE_NAME, instance=self.basename())
            ])

        if self.option_get('config.authorization.roles_bind') is not False:
            ret.extend([
                Object({
                    'apiVersion': 'rbac.authorization.k8s.io/v1',
                    'kind': 'ClusterRoleBinding',
                    'metadata': {
                        'name': self.object_name('cluster-role-binding'),
                    },
                    'roleRef': {
                        'apiGroup': 'rbac.authorization.k8s.io',
                        'kind': 'ClusterRole',
                        'name': self.object_name('cluster-role'),
                    },
                    'subjects': [{
                        'kind': 'ServiceAccount',
                        'name': self.object_name('service-account'),
                        'namespace': self.namespace(),
                    }]
                }, name=self.BUILDITEM_CLUSTER_ROLE_BINDING, source=self.SOURCE_NAME, instance=self.basename())
            ])

        return ret

    def internal_build_config(self) -> List[ObjectItem]:
        ret = []

        if self.option_get('config.traefik_config') is not None:
            if self.option_get('config.config_format') == Traefik2Options.CONFIGFORMAT_TOML:
                cfname = 'prometheus.toml'
            elif self.option_get('config.config_format') == Traefik2Options.CONFIGFORMAT_YAML:
                cfname = 'prometheus.yml'
            else:
                raise InvalidParamError('Unknown Traefik config format: ""{}'.format(
                    self.option_get('config.config_format')))

            ret.extend([
                Object({
                    'apiVersion': 'v1',
                    'kind': 'ConfigMap',
                    'metadata': {
                        'name': self.object_name('config'),
                        'namespace': self.namespace(),
                    },
                    'data': {
                        cfname: LiteralStr(self.configfile_get()),
                    },
                }, name=self.BUILDITEM_CONFIG, source=self.SOURCE_NAME, instance=self.basename())
            ])
        return ret

    def internal_build_service(self) -> List[ObjectItem]:
        ret = [Object({
            'kind': 'Deployment',
            'apiVersion': 'apps/v1',
            'metadata': {
                'name': self.object_name('deployment'),
                'namespace': self.namespace(),
                'labels': {
                    'app': self.object_name('pod-label-app'),
                },
            },
            'spec': {
                'selector': {
                    'matchLabels': {
                        'app': self.object_name('pod-label-app'),
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': self.object_name('pod-label-app'),
                        },
                        'annotations': ValueData({
                            'prometheus.io/scrape': QuotedStr('true'),
                            'prometheus.io/path': QuotedStr('/metrics'),
                            'prometheus.io/port': QuotedStr(self.option_get('config.prometheus_port')),
                        }, enabled=self.option_get('config.enable_prometheus') is not False and self.option_get(
                            'config.prometheus_annotation') is not False),
                    },
                    'spec': {
                        'serviceAccountName': ValueData(value=self.object_name('service-account'), disabled_if_none=True),
                        'volumes': [
                            ValueData({
                                'name': 'traefik2-config',
                                'configMap': {
                                    'name': self.object_name('config')
                                }
                            }, enabled=self.option_get('config.traefik_config') is not None),
                        ],
                        'containers': [{
                            'name': 'traefik',
                            'image': self.option_get('container.traefik2'),
                            'args': self.option_get('config.traefik_args'),
                            'ports': self._build_container_ports(),
                            'volumeMounts': [
                                ValueData({
                                    'name': 'traefik2-config',
                                    'mountPath': '/etc/traefik',
                                }, enabled=self.option_get('config.traefik_config') is not None),
                            ],
                            'resources': ValueData(value=self.option_get('kubernetes.resources.deployment'),
                                                   disabled_if_none=True),
                        }]
                    }
                }
            }
        }, name=self.BUILDITEM_DEPLOYMENT, source=self.SOURCE_NAME, instance=self.basename()), Object({
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': self.object_name('service'),
                'namespace': self.namespace(),
            },
            'spec': {
                'selector': {
                    'app': self.object_name('pod-label-app')
                },
                'ports': self._build_service_ports(),
            }
        }, name=self.BUILDITEM_SERVICE, source=self.SOURCE_NAME, instance=self.basename())]
        return ret

    def _build_container_ports(self):
        ret = []
        for port in self.option_get('config.ports'):
            ret.append({
                'name': port.name,
                'containerPort': port.port_container,
            })
        return ret

    def _build_service_ports(self):
        ret = []
        for port in self.option_get('config.ports'):
            if port.in_service:
                ret.append({
                    'name': port.name,
                    'protocol': port.protocol,
                    'port': port.port_service,
                })
        return ret

    def configfile_get(self) -> Optional[str]:
        if self.configfile is None:
            configfile = self.option_get('config.traefik_config')
            if configfile is None:
                return None
            if isinstance(configfile, str):
                self.configfile = configfile
            else:
                configfilerender = ConfigFileRenderMulti([])
                if self.option_get('config.config_format') == Traefik2Options.CONFIGFORMAT_TOML:
                    configfilerender.renderer_add(ConfigFileRender_TOML())
                elif self.option_get('config.config_format') == Traefik2Options.CONFIGFORMAT_YAML:
                    configfilerender.renderer_add(ConfigFileRender_Yaml())
                else:
                    raise InvalidParamError('Unknown Traefik config format: ""{}'.format(self.option_get('config.config_format')))
                configfilerender.renderer_add(ConfigFileRender_Yaml())
                self.configfile = configfilerender.render(configfile.get_value(self))
        return self.configfile

    def _traefik_crd(self):
        return yaml.load_all('''apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: ingressroutes.traefik.containo.us

spec:
  group: traefik.containo.us
  version: v1alpha1
  names:
    kind: IngressRoute
    plural: ingressroutes
    singular: ingressroute
  scope: Namespaced

---
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: middlewares.traefik.containo.us

spec:
  group: traefik.containo.us
  version: v1alpha1
  names:
    kind: Middleware
    plural: middlewares
    singular: middleware
  scope: Namespaced

---
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: ingressroutetcps.traefik.containo.us

spec:
  group: traefik.containo.us
  version: v1alpha1
  names:
    kind: IngressRouteTCP
    plural: ingressroutetcps
    singular: ingressroutetcp
  scope: Namespaced

---
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: ingressrouteudps.traefik.containo.us

spec:
  group: traefik.containo.us
  version: v1alpha1
  names:
    kind: IngressRouteUDP
    plural: ingressrouteudps
    singular: ingressrouteudp
  scope: Namespaced

---
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: tlsoptions.traefik.containo.us

spec:
  group: traefik.containo.us
  version: v1alpha1
  names:
    kind: TLSOption
    plural: tlsoptions
    singular: tlsoption
  scope: Namespaced

---
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: tlsstores.traefik.containo.us

spec:
  group: traefik.containo.us
  version: v1alpha1
  names:
    kind: TLSStore
    plural: tlsstores
    singular: tlsstore
  scope: Namespaced

---
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: traefikservices.traefik.containo.us

spec:
  group: traefik.containo.us
  version: v1alpha1
  names:
    kind: TraefikService
    plural: traefikservices
    singular: traefikservice
  scope: Namespaced
''', Loader=yaml.Loader)
