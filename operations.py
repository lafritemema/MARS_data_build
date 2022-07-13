
from enum import Enum
from typing import Dict, List, NewType
import re
from unittest import result
from assemblies import AssembliesData, AssemblyDefinition
from neo4mars.process.operation import Class as OClass, Instance as OInstance
from states import PreconditionRS, Relation, ResultRS, SCDefinition
from tqdm import tqdm

from utils import BasicDefinition, InstanceDefinition

class OpInstanceDefinition(SCDefinition, InstanceDefinition):
  def __init__(self,
               node:OInstance,
               mother_node:OClass,
               preconditions:List[PreconditionRS],
               results:List[ResultRS]):

    InstanceDefinition.__init__(self, node, mother_node)
    SCDefinition.__init__(self, node, preconditions, results)
    '''self.__node = node
    self.__mother_node = mother_node
    self.__preconditions = preconditions
    self.__results = results
    # self.__target_ref = target_ref
  
  @property
  def node(self):
    return self.__node

  @property
  def preconditions(self):
    return self.__preconditions

  @property
  def results(self):
    return self.__results
  
  @property
  def mother_node(self):
    return self.__mother_node 

  @property
  def target_reference(self):
    return self.__target_ref'''

class OperationType(Enum):
  DRILL = 'D', "no_drill", "drill", "drilled"
  FASTEN = 'F', "no_fasten", "fasten", "fastened"

  def __init__(self, code:str,
               precond_state:str,
               result_state:str,
               description:str):

    self.code = code
    self.precond_state = precond_state
    self.result_state = result_state
    self.__description = description
  
  def describe_on(self, element:str):
    return f'{element} {self.__description}'

class OperationsData:

  FTYPE_REGEX = r'(\S*)(?:\-\d*.\d*)$'

  def __init__(self,
               class_collection:Dict[str, BasicDefinition],
               instance_collection:Dict[str, OpInstanceDefinition]):
    self.__classes = class_collection
    self.__instances = instance_collection
  
  @property
  def classes(self):
    return self.__classes

  @property
  def instances(self):
    return self.__instances

  @staticmethod
  def generate_uid(operation_type:OperationType, element_ref:str):
    return f'{operation_type.code}{element_ref}'.lower()

  @classmethod
  def __build_class_node(cls, fastener_type:str, operation_type:OperationType):
   
    uid = cls.generate_uid(operation_type, fastener_type)
    description = f'{operation_type.name} {fastener_type}'.lower()

    return OClass(uid=uid,
                  description=description,
                  type=operation_type.name)


  @classmethod
  def __build_instance_node(cls, assy_uid:str,
                            assy_desc:str,
                            operation_type:OperationType):
    uid = cls.generate_uid(operation_type, assy_uid)
    description = f'{operation_type.name} {assy_desc}'.lower()

    return OInstance(uid=uid,
                     description=description,
                     type=operation_type.name)

  @classmethod
  def __build_operation_definition(cls,
                                   assy_definition:AssemblyDefinition,
                                   operation_type:OperationType,
                                   mother_node:OClass):
    node = cls.__build_instance_node(assy_definition.node.uid,
                                     assy_definition.node.description,
                                     operation_type)

    precondition = PreconditionRS(property_node=assy_definition.node,
                                  relation=Relation.EQUAL,
                                  state=operation_type.precond_state,
                                  priority=0)

    result = ResultRS(property_node=assy_definition.node,
                      relation=Relation.EQUAL,
                      state=operation_type.result_state,
                      description=operation_type.describe_on(assy_definition.node.description))
    
    target_reference = assy_definition.fastener.reference

    return OpInstanceDefinition(node=node,
                               mother_node=mother_node,
                               preconditions=[precondition],
                               results=[result])


  @classmethod
  def build(cls, assemblies_data:AssembliesData):
    
    # get the fastener ref from assy fastener class collection
    fastener_ref = assemblies_data.fasteners.classes.keys()
    # get the uniq type of fastener
    #  => use regex to find type from ref ad set to drop duplicates
    fastener_type = set([re.match(cls.FTYPE_REGEX, f)\
                           .group(1)\
                         for f in fastener_ref])

    # build the class collection
    class_collection = {}
    for f in fastener_type:
      for operation in [OperationType.DRILL, OperationType.FASTEN]:
        node = cls.__build_class_node(f, operation)
        class_collection[node.uid] = BasicDefinition(node)

    assemblies = assemblies_data.assemblies
    instance_collection = {}
    for assy_uid, assy_def in assemblies.items():
      for operation in [OperationType.DRILL, OperationType.FASTEN]:
        
        # get the assy type, and found key in class_collection
        # raise an assert erro if not found
        assy_ftype = re.match(cls.FTYPE_REGEX, assy_uid).group(1)
        class_uid = cls.generate_uid(operation, assy_ftype)
        class_def = class_collection.get(class_uid)
        
        assert class_def, f'{class_uid} not found in class_collection : {list(class_collection.keys())}'
        
        op_def = cls.__build_operation_definition(assy_def,
                                                  operation,
                                                  class_def.node)
                                                  
        instance_uid = cls.generate_uid(operation, assy_uid)
        instance_collection[instance_uid] = op_def
    
    return cls(class_collection, instance_collection)

  def save_data(self):
    print('save operations nodes')
    print('save class nodes')
    for bdef in tqdm(self.__classes.values()):
      bdef.node.save()
    
    print('save and connect instance nodes')
    for op_def in tqdm(self.__instances.values()):
      node = op_def.node
      mother_node = op_def.mother_node
      preconditions = op_def.preconditions
      results = op_def.results

      node.save()
      node.mother_class.connect(mother_node)

      for precond in preconditions:
        node.preconditions.connect(precond.property_node, precond.definition)
      
      for result in results:
        node.results.connect(result.property_node, result.definition)
    

      



