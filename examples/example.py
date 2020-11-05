from kubragen import KubraGen
from kubragen.consts import PROVIDER_GOOGLE, PROVIDERSVC_GOOGLE_GKE
from kubragen.object import Object
from kubragen.option import OptionRoot
from kubragen.options import Options
from kubragen.output import OutputProject, OD_FileTemplate, OutputFile_ShellScript, OutputFile_Kubernetes, \
    OutputDriver_Print
from kubragen.provider import Provider

from kg_traefik2 import Traefik2Builder, Traefik2Options

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
traefik2_config = Traefik2Builder(kubragen=kg, options=Traefik2Options({
    'namespace': OptionRoot('namespaces.mon'),
    'basename': 'mytraefik2',
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
                                   traefik2_config.BUILD_SERVICE)

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

file.append(traefik2_config.build(traefik2_config.BUILD_ACCESSCONTROL))

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
