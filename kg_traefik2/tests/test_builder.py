import unittest

from kubragen import KubraGen
from kubragen.jsonpatch import FilterJSONPatches_Apply, ObjectFilter, FilterJSONPatch
from kubragen.provider import Provider_Generic

from kg_traefik2 import Traefik2Builder, Traefik2Options


class TestBuilder(unittest.TestCase):
    def setUp(self):
        self.kg = KubraGen(provider=Provider_Generic())

    def test_empty(self):
        traefik2_config = Traefik2Builder(kubragen=self.kg)
        self.assertEqual(traefik2_config.object_name('service'), 'traefik2')
        self.assertEqual(traefik2_config.object_name('deployment'), 'traefik2')

    def test_basedata(self):
        traefik2_config = Traefik2Builder(kubragen=self.kg, options=Traefik2Options({
            'namespace': 'myns',
            'basename': 'mytraefik2',
        }))
        self.assertEqual(traefik2_config.object_name('service'), 'mytraefik2')
        self.assertEqual(traefik2_config.object_name('deployment'), 'mytraefik2')

        FilterJSONPatches_Apply(items=traefik2_config.build(traefik2_config.BUILD_SERVICE), jsonpatches=[
            FilterJSONPatch(filters=ObjectFilter(names=[traefik2_config.BUILDITEM_SERVICE]), patches=[
                {'op': 'check', 'path': '/metadata/name', 'cmp': 'equals', 'value': 'mytraefik2'},
                {'op': 'check', 'path': '/metadata/namespace', 'cmp': 'equals', 'value': 'myns'},
            ]),
        ])
