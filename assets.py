
from enum import Enum
from utils import BasicDefinition
from typing import Dict
from utils import get_config_from_file, GetItemEnum
from neo4mars.resource.asset import Carrier, EndEffector

class AssetType(Enum, metaclass=GetItemEnum):
  CARRIER = Carrier
  ENDEFFECTOR = EndEffector

class AssetsData:
  def __init__(self, assets_collection:Dict[str, BasicDefinition]) -> None:
    self.__assets = assets_collection
  
  @property
  def assets(self):
    return self.__assets

  @classmethod
  def build_from_file(cls, assets_yaml_file:str):
    assets_def = get_config_from_file(assets_yaml_file)
    
    assets_collection = {}
    for uid, asset_def in assets_def.items():
      
      '''node_def = {
        'uid' : uid,
        'description': asset_def['description'],
        'interface': asset_def['interface']
      }'''
      
      node_class = AssetType[asset_def['type']]
      asset_node = node_class(uid=uid,
                              description= asset_def['description'],
                              interface=asset_def['interface'])

      assets_collection[uid] = BasicDefinition(asset_node)
    
    return cls(assets_collection)

  def save_data(self):
    for asset_def in self.__assets.values():
      asset_def.node.save()