# from neo4mars import process
from parts import PartsData
from pattern import PatternData
from assemblies import AssembliesData
from operations import OperationsData
from actions import ActionsData
from states import StatesData

from assets import AssetsData
from neomodel import config
import os
import warnings
from pandas.core.common import SettingWithCopyWarning

warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)

bolt_url = os.environ['NEO4J_BOLT_URL']
config.DATABASE_URL = bolt_url

MARS_CONFIG = {
  "database": {
    "type": 'MONGODB',
    "host": 'debianvm',
    "port": 27017,
    "database": 'mars',
    "collection": 'carrier'
    }
  }

import model
import mars

model.COMMAND_REGISTER, model.EQUIPMENT, model.REFERENCE = mars.COMMAND_REGISTER, mars.EQUIPMENT, mars.REFERENCE


'''
bolt_url = os.environ['NEO4J_BOLT_URL']
config.DATABASE_URL = bolt_url
'''

FASTENERS = "./data/fasteners.json"
CHCONF_INJESTION = "./data/change_conf_injestion.csv"
WEB_INJESTION = "./data/web_injestion.csv"
FLANGE_INJESTION = "./data/flange_injestion.csv"
MANIPULATIONS = "./data/manipulations.yaml"
MOVEMENTS = "./data/movements.yaml" 
PARTS = "./data/parts.csv" 
ASSETS = "./data/assets.yaml"

print('build data')
print('build pattern data')
pattern = PatternData.build()
print('build parts data')
parts = PartsData.build_from_file(PARTS)
print('build assemblies data')
assemblies = AssembliesData.build_from_file(source_file=FASTENERS,
                                            parts_data= parts,
                                            pattern_data=pattern)

# get collection of assemblies uid forfollowing processing
assemblies_uids = dict([(key, value.node.uid)\
                       for key, value in assemblies.assemblies.items()])

print('build operations data')
operations = OperationsData.build(assemblies)

print('build states data')
states = StatesData.build()

print('build assets data')
assets = AssetsData.build_from_file(ASSETS)

print('build actions data')
actions = ActionsData.build_from_files(CHCONF_INJESTION,
                                         WEB_INJESTION,
                                         FLANGE_INJESTION,
                                         MANIPULATIONS,
                                         MOVEMENTS,
                                         states,
                                         operations,
                                         assemblies_uids,
                                         assets,
                                         pattern)

print('ok build')

print('save data')
pattern.save_data()
parts.save_data()
assemblies.save_data()
operations.save_data()
states.save_data()
assets.save_data()
actions.save_data()
print('ok save')


