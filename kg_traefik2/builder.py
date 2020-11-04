from typing import List, Optional, Sequence, Any

import yaml

from kubragen import KubraGen
from kubragen.builder import Builder
from kubragen.data import ValueData
from kubragen.exception import InvalidParamError, InvalidNameError
from kubragen.helper import QuotedStr
from kubragen.object import ObjectItem, Object
from kubragen.types import TBuild, TBuildItem
from .option import Traefik2Options


class Traefik2Builder(Builder):
    options: Traefik2Options
    _namespace: str

    SOURCE_NAME = 'kg_traefik2'

    BUILD_CRD: TBuild = 'crd'
    BUILD_ACCESSCONTROL: TBuild = 'accesscontrol'
    BUILD_SERVICE: TBuild = 'service'

    BUILDITEM_CLUSTER_ROLE: TBuildItem = 'cluster-role'
    BUILDITEM_SERVICE_ACCOUNT: TBuildItem = 'service-account'
    BUILDITEM_CLUSTER_ROLE_BINDING: TBuildItem = 'cluster-role-binding'
    BUILDITEM_DEPLOYMENT: TBuildItem = 'deployment'
    BUILDITEM_SERVICE: TBuildItem = 'service'

    def __init__(self, kubragen: KubraGen, options: Optional[Traefik2Options] = None):
        super().__init__(kubragen)
        if options is None:
            options = Traefik2Options()
        self.options = options

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

        self.object_names_update({
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
        return [self.BUILD_CRD, self.BUILD_ACCESSCONTROL, self.BUILD_SERVICE]

    def build_names_required(self) -> List[TBuild]:
        ret = [self.BUILD_SERVICE]
        if self.option_get('config.create_traefik_crd') is not False:
            ret.append(self.BUILD_CRD)
        if self.option_get('config.authorization.serviceaccount_create') is not False or \
                self.option_get('config.authorization.roles_create') is not False:
            ret.append(self.BUILD_ACCESSCONTROL)
        return ret

    def builditem_names(self) -> List[TBuildItem]:
        return [
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
                        'serviceAccountName': ValueData(value=self.object_name('service-account'),
                                                        enabled=self.object_name('service-account') is not None),
                        'containers': [{
                            'name': 'traefik',
                            'image': self.option_get('container.traefik'),
                            'args': self.option_get('config.traefik_args'),
                            'ports': self._build_container_ports(),
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
