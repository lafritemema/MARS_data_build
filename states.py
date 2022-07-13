from neomodel.core import StructuredNode
from enum import Enum
from neo4mars.resource.situation import StateObject
from typing import Dict, List, Tuple
from utils import BasicDefinition


class Relation(Enum):
  EQUAL = 'eq'
  NOT_EQUAL = 'neq'

class StateRS:
  def __init__(self,
               property_node:StructuredNode,
               relation:Relation,
               state:str):
    self.__property_node = property_node
    self.__relation = relation
    self.__state = state
  
  @property
  def property_node(self):
    return self.__property_node
  
  @property
  def relation(self):
    return self.__relation

  @property
  def state(self):
    return self.__state

  @property
  def definition(self):
    return {
      "state": self.__state,
      "relation": self.__relation.value
    }

class PreconditionRS(StateRS):
  def __init__(self,
               property_node:StructuredNode,
               relation:str,
               state:str,
               priority:int):
    
    super().__init__(property_node,
                     relation,
                     state)

    self.__priority = priority

  @property
  def priority(self):
    return self.__priority

  @property
  def definition(self):
    definition = super().definition
    definition["priority"] = self.__priority
    return definition

class ResultRS(StateRS):
  def __init__(self,
               property_node:StructuredNode,
               relation:str,
               state:str,
               description:str) -> None:
    
    super().__init__(property_node,
                     relation,
                     state)

    self.__description = description
 
  @property
  def definition(self):
    definition = super().definition
    definition["description"] = self.__description
    return definition

class SCDefinition (BasicDefinition):
  def __init__(self,
               node:StructuredNode,
               preconditions:List[PreconditionRS],
               results:List[ResultRS]):
    BasicDefinition.__init__(self, node)
    self.__preconditions = preconditions
    self.__results = results
  
  @property
  def preconditions(self):
    return self.__preconditions

  @property
  def results(self):
    return self.__results


class StatesData:

  STATE_OBJECT_ID:List = ['effector', 'station', 'tcp_approach', 'tcp_work']

  PROBE_ASSEMBLY_ID:Dict[str,Tuple[str,str]] = {
    'y-1292': ('asna2392-3-04.167', 'asna2392-3-04.184'),
    'y-763': ('asna2392-3-04.229', 'asna2392-3-04.185'),
    'y-254': ('asna2392-3-03.38', 'asna2392-3-03.15'),
    'y+254': ('asna2392-3-03.29', 'asna2392-3-03.21'),
    'y+763': ('asna2392-3-04.210', 'asna2392-3-04.196'),
    'y+1292': ('asna2392-3-04.233', 'asna2392-3-04.186')
  }

  def __init__(self, states_collection:Dict[str, BasicDefinition]):
    self.__states = states_collection
  
  @property
  def states(self):
    return self.__states

  @staticmethod
  def generate_probing_uid(rail_position:str, side:str):
    if side == 'front':
      return 'kff_'+rail_position
    elif side == 'rear':
      return 'kfr_'+rail_position

  @classmethod
  def build(cls):
    states_collection = {}
    
    for so in cls.STATE_OBJECT_ID:
      description =  f'state meta object for {so}'
      states_collection[so] = BasicDefinition(StateObject(uid=so,
                                                          description=description,
                                                          priority=0))
    
    for rail_pos in cls.PROBE_ASSEMBLY_ID.keys():

      front_probing_uid = cls.generate_probing_uid(rail_pos, 'front')
      front_probing_desc = f'state meta object for probing operation at {rail_pos} front'
      rear_probing_uid = cls.generate_probing_uid(rail_pos, 'rear')
      rear_probing_desc = f'state meta object for probing operation at {rail_pos} rear'

      front_probing_so = StateObject(uid=front_probing_uid,
                                     description=front_probing_desc,
                                     priority=0)
      
      rear_probing_so = StateObject(uid=rear_probing_uid,
                                    description=rear_probing_desc,
                                    priority=0)

      states_collection[front_probing_uid] = BasicDefinition(front_probing_so)
      states_collection[rear_probing_uid] = BasicDefinition(rear_probing_so)
    
    return cls(states_collection)

  def get_probed_assy(self)->Dict[str, BasicDefinition]:
    assy_probe_collection = {}
    for yloc, assies in StatesData.PROBE_ASSEMBLY_ID.items():
      kfront, krear = assies
      assy_probe_collection[kfront] = self.states.get(StatesData.generate_probing_uid(yloc, 'front'))
      assy_probe_collection[krear] = self.states.get(StatesData.generate_probing_uid(yloc, 'rear'))

    return assy_probe_collection

  def save_data(self):
    for state_def in self.__states.values():
      state_def.node.save()
