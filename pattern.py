from typing import Dict
from neo4mars.process.area import Area
from tqdm import tqdm

from utils import BasicDefinition

class PatternData:

  RAILS = ['y-1292', 'y-763', 'y-254',
           'y+254', 'y+763', 'y+1292']

  def __init__(self, area_collection:Dict[str, BasicDefinition]):
    self.__areas = area_collection
  
  @property
  def areas(self):
    return self.__areas

  @classmethod
  def build(cls):
    area_collection = {}

    area_collection['web'] = BasicDefinition(Area(uid='web',
                                  description='web',
                                  type='area',
                                  reference='rail'))

    # create and save flange 
    area_collection['flange'] = BasicDefinition(Area(uid='flange',
                                     description='flange',
                                     type="area",
                                     reference="rail"))

    area_collection['front'] = BasicDefinition(Area(uid="front",
                                    description="front",
                                    type="side",
                                    reference="crossbeam"))
    area_collection['rear'] = BasicDefinition(Area(uid="rear",
                                   description="rear",
                                   type="side",
                                   reference="crossbeam"))
    area_collection['right'] = BasicDefinition(Area(uid="right",
                                    description="right",
                                    type="side",
                                    reference="rail"))
    area_collection['left'] = BasicDefinition(Area(uid="left",
                                   description="left",
                                   type="side",
                                   reference="rail"))
    
    for rail in cls.RAILS:
      area_collection[rail] = BasicDefinition(Area(uid=rail,
                                   description=rail,
                                   type="rail",
                                   reference="aircraft"))

    return cls(area_collection)

  def save_data(self):
    print('save pattern nodes')
    for area_def in tqdm(self.__areas.values()):
      area_def.node.save()
