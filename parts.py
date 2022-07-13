import pandas as pd
import df_functions as dff
from typing import Dict, Tuple
from neo4mars.product.part import Instance, Class
from tqdm import tqdm

from utils import BasicDefinition, InstanceDefinition

def get_element_name(code:str, el_type:str):
    if el_type == "instance":   
        element_corr = {"rar": "front rail", "rav":"rear rail", "eg":"left splice", "ed":"right splice", "eq":"square", "tr":"crossbeam"}
    elif el_type == "part" :
        element_corr = {"rar": "rail", "rav":"rail", "eg":"splice", "ed":"splice", "eq":"square", "tr":"crossbeam"}
    else:
        raise Exception("element type error")
    return element_corr[code]

def get_rail_by_id(id:int):
    rail_y = {1:"Y+1292", 2:"Y+763", 3:"Y+254", 4:"Y-254", 5:"Y-763", 6:"Y-1292"}
    return rail_y[id]


class PartsData:
  COLUMNS = ['element_code', 'parent', 'path', 'rail', 'reference']
  ELEMENT_CODE = ['ed', 'eg', 'eq', 'rar', 'rav', 'tr']
  RAIL_ID = [1,2,3,4,5,6]

  def __init__(self,
      classes_collection:Dict[str, BasicDefinition],
      instances_collection:Dict[str, InstanceDefinition],
      refbyareas:pd.DataFrame):

      self.__classes = classes_collection
      self.__instances = instances_collection
      self.__refbyareas = refbyareas

  @property
  def classes(self):
    return self.__classes
  
  @property
  def instances(self):
    return self.__instances

  def get_element(self, description:str, rail:str) -> str:
    return self.__refbyareas.loc[(description, rail), 'reference']

  @staticmethod
  def generate_uid(part_ref:str, area_ref:str) -> str:
    find = area_ref.find('+') if area_ref.find('+') != -1 else area_ref.find('-')
    
    if find != -1 :
      side = 'L' if area_ref[find] == '+' else 'R'
      uid = part_ref+side+area_ref[find+1:]
    else:
      uid = part_ref+area_ref
    
    return uid.lower()
    

  @classmethod
  def __build_dataframes(cls, parts_file:str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # build and check the dataframe
    df = dff.build_and_check(source_file=parts_file,
                        ftype='csv',
                        columns=cls.COLUMNS,
                        checks={"element_code": cls.ELEMENT_CODE,
                                "rail": cls.RAIL_ID})
    
 
    # build the part class dataframe using the df 
    class_df = df[['element_code', 'reference']].drop_duplicates('reference')
    # add ename col 
    class_df['ename'] = class_df.element_code\
                        .apply(get_element_name, el_type='part')
    # put the reference in lowercase
    class_df['reference'] = class_df.reference.str.lower()

    # build the instance df using the orignal df
    instance_df = df[['element_code', 'rail', 'reference']]
    #put the ref in lowercase
    instance_df.reference = instance_df.reference.str.lower()
    # transform rail id to rail ref (y+...) using the fonction, put in lowercase
    instance_df.rail = instance_df.rail.apply(get_rail_by_id).str.lower()
    # add ename col
    instance_df['ename'] = instance_df.element_code\
                           .apply(get_element_name,
                                  el_type='instance')

    # delete the element code col
    del instance_df['element_code']
    # group the df by ename and rail ref
    instance_df= instance_df.groupby(['ename', 'rail']).first()
    
    # crossbeam data duplicated so i need to have only one row
    # get the crossbeam ref
    crossbeam_ref = instance_df.loc['crossbeam'].iloc[0].reference.lower()
    # delete the crossbeam data
    instance_df.drop('crossbeam', inplace=True)

    # create only one row for crossbeam with ref
    instance_df.loc[('crossbeam', 'c35'), 'reference'] = crossbeam_ref
    
    return class_df, instance_df

  @staticmethod
  def __build_class_node(definition:pd.Series) -> Class:
    reference = definition.reference
    uid = definition.reference
    description = definition.ename

    return Class(uid=uid.lower(),
                 description=description,
                 reference=reference)

  @staticmethod
  def __build_instance_node(index:Tuple, definition:pd.Series) -> Instance:
    ename, area_ref = index
    reference = definition.reference

    uid = PartsData.generate_uid(reference, area_ref)

    description = f"{ename} {area_ref}"
    
    return Instance(uid=uid,
                    reference=reference,
                    description=description)

  @classmethod
  def __build_instance_definition(cls,
                                  index:Tuple,
                                  definition:pd.Series,
                                  mother_node:Class) -> InstanceDefinition:
    node = cls.__build_instance_node(index,
                                     definition)
    
    return InstanceDefinition(node=node,
                              mother_node=mother_node)
    

  @classmethod
  def build_from_file(cls, source_file:str) -> 'PartsData':
    # build part and class dataframe
    class_df, instance_df = cls.__build_dataframes(source_file)

    # build the class node collection
    class_collection = {}
    for row in class_df.iterrows():
      _, definition = row
      class_node = cls.__build_class_node(definition)
      class_collection[class_node.uid] = BasicDefinition(class_node)
    
    # build the instance node collection
    instance_collection = {}
    for row in instance_df.iterrows():
      index, definition = row
      
      class_def = class_collection.get(definition.reference)
      
      assert class_def, f'{definition.reference} not found in class_collection'

      instance_def = cls.__build_instance_definition(index,
                                                   definition,
                                                   class_def.node)
      instance_collection[instance_def.node.uid] = instance_def

    #return an PartData object 
    return cls(class_collection, instance_collection, instance_df)

  def save_data(self)->None:
    print('save parts nodes')
    print('save class nodes')
    # save the class nodes in neo4j
    for bdef in tqdm(self.__classes.values()):
      bdef.node.save()
    
    print('save instance nodes')
    # save the instance nodes in neo4j
    # and create connexion between class and instances
    for instance_def in tqdm(self.__instances.values()):
      node = instance_def.node
      mother_node = instance_def.mother_node
      
      node.save()
      node.mother_class.connect(mother_node)