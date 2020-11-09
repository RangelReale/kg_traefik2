# KubraGen Builder: Traefik 2

[![PyPI version](https://img.shields.io/pypi/v/kg_traefik2.svg)](https://pypi.python.org/pypi/kg_traefik2/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/kg_traefik2.svg)](https://pypi.python.org/pypi/kg_traefik2/)

kg_traefik2 is a builder for [KubraGen](https://github.com/RangelReale/kubragen) that deploys 
a [Traefik 2](https://traefik.io/) server in Kubernetes.

[KubraGen](https://github.com/RangelReale/kubragen) is a Kubernetes YAML generator library that makes it possible to generate
configurations using the full power of the Python programming language.

* Website: https://github.com/RangelReale/kg_traefik2
* Repository: https://github.com/RangelReale/kg_traefik2.git
* Documentation: https://kg_traefik2.readthedocs.org/
* PyPI: https://pypi.python.org/pypi/kg_traefik2

## Example

```python
from kubragen import KubraGen
from kubragen.configfile import ConfigFile_Static, ConfigFileOutput_Dict
from kubragen.consts import PROVIDER_GOOGLE, PROVIDERSVC_GOOGLE_GKE
from kubragen.object import Object
from kubragen.option import OptionRoot
from kubragen.options import Options
from kubragen.output import OutputProject, OD_FileTemplate, OutputFile_ShellScript, OutputFile_Kubernetes, \
    OutputDriver_Print
from kubragen.provider import Provider

from kg_traefik2 import Traefik2Builder, Traefik2Options, Traefik2ConfigFile, Traefik2OptionsPort

kg = KubraGen(provider=Provider(PROVIDER_GOOGLE, PROVIDERSVC_GOOGLE_GKE), options=Options({
    'namespaces': {
        'mon': 'app-monitoring',
    },
}))

out = OutputProject(kg)

shell_script = OutputFile_ShellScript('create_gke.sh')
out.append(shell_script)

shell_script.append('set -e')

#
# OUTPUTFILE: app-namespace.yaml
#
file = OutputFile_Kubernetes('app-namespace.yaml')

file.append([
    Object({
        'apiVersion': 'v1',
        'kind': 'Namespace',
        'metadata': {
            'name': 'app-monitoring',
        },
    }, name='ns-monitoring', source='app', instance='app')
])

out.append(file)
shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

shell_script.append(f'kubectl config set-context --current --namespace=app-monitoring')

#
# SETUP: traefik2
#
traefik2_config_file = Traefik2ConfigFile()

traefik2_config = Traefik2Builder(kubragen=kg, options=Traefik2Options({
    'namespace': OptionRoot('namespaces.mon'),
    'basename': 'mytraefik2',
    'config': {
        'traefik_config': traefik2_config_file,
        'traefik_args': [
            '--entrypoints.web.Address=:80',
            '--entryPoints.metrics.address=:9090',
            '--metrics.prometheus=true',
            '--metrics.prometheus.entryPoint=metrics',
        ],
        'ports': [
            Traefik2OptionsPort(name='web', port_container=80, port_service=80),
            Traefik2OptionsPort(name='metrics', port_container=9090, in_service=False),
        ],
    },
    'kubernetes': {
        'resources': {
            'deployment': {
                'requests': {
                    'cpu': '150m',
                    'memory': '300Mi'
                },
                'limits': {
                    'cpu': '300m',
                    'memory': '450Mi'
                },
            },
        },
    }
}))

traefik2_config.ensure_build_names(traefik2_config.BUILD_CRD, traefik2_config.BUILD_ACCESSCONTROL,
                                   traefik2_config.BUILD_CONFIG, traefik2_config.BUILD_SERVICE)

#
# OUTPUTFILE: traefik2-crd.yaml
#
file = OutputFile_Kubernetes('traefik2-crd.yaml')
out.append(file)

file.append(traefik2_config.build(traefik2_config.BUILD_CRD))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))


#
# OUTPUTFILE: traefik2-config.yaml
#
file = OutputFile_Kubernetes('traefik2-config.yaml')
out.append(file)

file.append(traefik2_config.build(traefik2_config.BUILD_ACCESSCONTROL, traefik2_config.BUILD_CONFIG))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

#
# OUTPUTFILE: traefik2.yaml
#
file = OutputFile_Kubernetes('traefik2.yaml')
out.append(file)

file.append(traefik2_config.build(traefik2_config.BUILD_SERVICE))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

#
# Write files
#
out.output(OutputDriver_Print())
# out.output(OutputDriver_Directory('/tmp/build-gke'))
```

Output:

```text
****** BEGIN FILE: 001-app-namespace.yaml ********
apiVersion: v1
kind: Namespace
metadata:
  name: app-monitoring

****** END FILE: 001-app-namespace.yaml ********
****** BEGIN FILE: 002-traefik2-crd.yaml ********
apiVersion: apiextensions.k8s.io/v1beta1
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
<...more...>
****** END FILE: 002-traefik2-crd.yaml ********
****** BEGIN FILE: 003-traefik2-config.yaml ********
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mytraefik2
  namespace: app-monitoring
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRole
metadata:
  name: mytraefik2
rules:
- apiGroups: ['']
  resources: [services, endpoints, secrets]
  verbs: [get, list, watch]
- apiGroups: [extensions, networking.k8s.io]
  resources: [ingresses, ingressclasses]
  verbs: [get, list, watch]
- apiGroups: [extensions]
  resources: [ingresses/status]
  verbs: [update]
- apiGroups: [traefik.containo.us]
  resources: [middlewares, ingressroutes, traefikservices, ingressroutetcps, ingressrouteudps,
    tlsoptions, tlsstores]
  verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: mytraefik2
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: mytraefik2
subjects:
- kind: ServiceAccount
  name: mytraefik2
  namespace: app-monitoring
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mytraefik2-config
  namespace: app-monitoring
data:
  prometheus.toml: |
    [global]
    checkNewVersion = false
    sendAnonymousUsage = false

****** END FILE: 003-traefik2-config.yaml ********
****** BEGIN FILE: 004-traefik2.yaml ********
kind: Deployment
apiVersion: apps/v1
metadata:
  name: mytraefik2
  namespace: app-monitoring
  labels:
    app: mytraefik2
spec:
  selector:
    matchLabels:
      app: mytraefik2
  template:
    metadata:
      labels:
        app: mytraefik2
    spec:
      serviceAccountName: mytraefik2
      volumes:
      - name: traefik2-config
        configMap:
          name: mytraefik2-config
      containers:
      - name: traefik
<...more...>
****** END FILE: 004-traefik2.yaml ********
****** BEGIN FILE: create_gke.sh ********
#!/bin/bash

set -e
kubectl apply -f 001-app-namespace.yaml
kubectl config set-context --current --namespace=app-monitoring
kubectl apply -f 002-traefik2-crd.yaml
kubectl apply -f 003-traefik2-config.yaml
kubectl apply -f 004-traefik2.yaml

****** END FILE: create_gke.sh ********
```

### Credits

based on

[Traefik & Kubernetes](https://doc.traefik.io/traefik/providers/kubernetes-crd/)

## Author

Rangel Reale (rangelspam@gmail.com)
