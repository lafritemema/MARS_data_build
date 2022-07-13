
from typing import Dict, List

import df_functions as dff
from neo4mars.process.area import Area
from parts import PartsData
from pandas import DataFrame, to_numeric, Series, isna
from neo4mars.product.fastener import Class as FClass, Instance as FInstance
from neo4mars.product.part import Instance as PInstance
from neo4mars.product.assembly import Assembly

from neomodel.contrib.spatial_properties import NeomodelPoint

from pattern import PatternData
from tqdm import tqdm
from utils import BasicDefinition, InstanceDefinition

def get_rail_position(yValue: float) -> str :
    rail:str
    v:float

    # get the absolute value of yValue (no considering sign)
    v = abs(yValue)

    if v < 1760 and v > 1710 :
        rail = "1732"
    elif v < 1310 and v > 1260 :
        rail = "1292"
    elif v < 790 and v > 740 :
        rail = "763"
    elif v < 280 and v > 230 :
        rail = "254"

    signe = '+' if yValue > 0 else '-'

    return f'y{signe}{rail.lower()}'

def build_element_stack(row:Series):
  ptt = {
           "frontweb":["left splice", "front rail", "right splice"],
           "rearweb":["left splice", "rear rail", "right splice"],
           "frontflangeleftinsideexternal": ["left splice", "front rail"],
           "frontflangeleftinsideinternal": ["left splice", "front rail", "square"],
           "frontflangeleftoutsideexternal": ["left splice", "front rail"],
           "frontflangeleftoutsideinternal": ["left splice", "square"],
           "frontflangerightinsideexternal": ["right splice", "front rail"],
           "frontflangerightinsideinternal": ["right splice", "front rail", "square"],
           "frontflangerightoutsideexternal": ["right splice", "front rail"],
           "frontflangerightoutsideinternal": ["right splice", "square"],
           "rearflangeleftinsideexternal": ["left splice", "rear rail"],
           "rearflangeleftinsideinternal": ["left splice", "rear rail", "crossbeam"],
           "rearflangeleftoutsideexternal": ["left splice", "rear rail"],
           "rearflangeleftoutsideinternal": ["left splice", "rear rail", "crossbeam"],
           "rearflangerightinsideexternal": ["right splice", "rear rail"],
           "rearflangerightinsideinternal": ["right splice", "rear rail", "crossbeam"],
           "rearflangerightoutsideexternal": ["right splice", "rear rail"],
           "rearflangerightoutsideinternal": ["right splice", "rear rail", "crossbeam"]
          }
    
  cside = row.crossbeam_side
  area = row.rail_area
  rside = ""
  rpos = ""
  xpos = ""
  
  if area == "flange" :
      rside = row.rail_side
      rpos = "inside" if row.rail_position.find('254') !=-1 else "outside"
      xpos = "internal" if (row.xe > 15320 and row.xe < 15398) else "external"
  
  pattern = f"{cside}{area}{rside}{rpos}{xpos}"
  
  return ptt[pattern]

def replace_reference(row:Series, parts_data:PartsData):
    ref_tab = []
    el_stack = row.el_to_tight
    rail_position = row.rail_position

    for el in el_stack:
        yref = rail_position if not el == 'crossbeam' else "c35"
        reference = parts_data.get_element(el, yref)
        ref_uid = PartsData.generate_uid(reference, yref)
        ref_tab.append(ref_uid)
    
    return ref_tab

def generate_stack(row:Series):
    stack_list = []
    
    thickness = row.parts_thickness_stack
    materials = row.parts_material_stack
    references = row.ref_to_tight
    
    for index, reference in enumerate(references):
      stack_list.append((reference, thickness[index], materials[index]))
    
    return stack_list


class FastenersData:
  def __init__(self,
               classes_collection:Dict[str, BasicDefinition],
               instances_collection:Dict[str, InstanceDefinition]):
    self.__classes = classes_collection
    self.__instances = instances_collection
  
  @property
  def classes(self)->BasicDefinition:
    return self.__classes
  
  @property
  def instances(self)->InstanceDefinition:
    return self.__instances

  def save_nodes(self):
    print('save fastener nodes')
    print('save class nodes')
    for bdef in tqdm(self.__classes.values()):
      bdef.node.save()

    print('save and connect instance nodes')
    for instance_def in tqdm(self.__instances.values()):
      node = instance_def.node
      mother_node = instance_def.mother_node

      node.save()
      node.mother_class.connect(mother_node)


class AssembleRS:
  def __init__(self,
               part:PInstance,
               thickness:str,
               material:str,
               index:int):
    self.__part = part
    self.__thickness = float(thickness)
    self.__material = material
    self.__index = index
  
  @property
  def part(self):
    return self.__part

  @property
  def definition(self):
    return {"stackMaterial":self.__material,
            "stackThickness":self.__thickness,
            "stackIndex":self.__index}



class AssemblyDefinition(BasicDefinition):
  def __init__(self,
               node:Assembly,
               fastener: FInstance,
               assemble:List[AssembleRS],
               pattern: List[Area]):
    BasicDefinition.__init__(self, node)
    self.__fastener=fastener
    self.__assemble=assemble
    self.__pattern=pattern
  
  @property
  def fastener(self):
    return self.__fastener
  
  @property
  def assemble(self):
    return self.__assemble
    
  @property
  def pattern(self):
    return self.__pattern

class AssembliesData:

  COLUMNS = ['Xe','Ye','Ze',
              'Xdir', 'Ydir', 'Zdir',
              'Parts_Thickness_Stack',
              'Id', 'Parts_Material_Stack',
              'Name',
              'Fastener_Diameter']

  RENAMED_COLUMNS = ['xe', 'ye', 'ze', 'xdir', 'ydir', 'zdir',
                     'parts_thickness_stack',
                     'id', 'parts_material_stack','aname',
                     'fastener_diameter']

  def __init__(self,
               assembly_collection:Dict[str, AssemblyDefinition],
               fasterners_data:FastenersData):
    self.__fasteners = fasterners_data
    self.__assemblies = assembly_collection

  @property
  def fasteners(self)->FastenersData:
    return self.__fasteners

  @property
  def assemblies(self)->Dict[str, AssemblyDefinition]:
    return self.__assemblies

  @classmethod
  def __build_master_dataframe(cls, source_file:str, parts_data:PartsData)->DataFrame:
    # get dataframe from source file
    df = dff.build_and_check(source_file=source_file,
                             ftype='json',
                             columns=cls.COLUMNS)
    df.columns = cls.RENAMED_COLUMNS
    # cast dir data 
    df.xdir = to_numeric(df.xdir, downcast='integer')
    df.ydir = to_numeric(df.ydir, downcast='integer')
    df.zdir = to_numeric(df.zdir, downcast='integer')

    # add 15367 to x to realign reference
    df.xe = df.xe + 15367

    # y is inverted in catia (left - 0 + right)
    # so realign the y in aircraft reference
    df.ye = df.ye * -1

     # round coordinates
    df.xe = df.xe.round(3)
    df.ye = df.ye.round(3)
    df.ze = df.ze.round(3)

    # create rail_position data using get_rail_position function
    df['rail_position'] = df.ye.apply(get_rail_position)

    # extract the reference
    df['reference'] = df.aname.str.extract(r'^([^\.]*)')
    df.reference = df.reference.str.lower()
    
    # drop rail y+1732 ans y-1732 from data 
    df = df[(df.rail_position != "y+1732")\
            & (df.rail_position != "y-1732")]

    # create fastener_type
    df.loc[df.reference.str.match(r'^en6115'), 'fastener_type'] = "Hi-Lite"
    df.loc[df.reference.str.match(r'^asna2392'), 'fastener_type'] = "Lockbolt"

    # transform initial data
    df.loc[df.parts_material_stack.notna(),
           "parts_material_stack"] = df.parts_material_stack.str.split(';')
    df.loc[df.parts_thickness_stack.notna(),
           "parts_thickness_stack"] = df.parts_thickness_stack.str.replace('mm', "").str.split(';')

    # create crossbeam side info
    df.loc[df.xe > 15367, "crossbeam_side"] = "rear"
    df.loc[isna(df.crossbeam_side), "crossbeam_side"] = "front"

    # create area side info
    df.loc[df.zdir == -1 , 'rail_area'] = 'flange'
    df.loc[isna(df.rail_area), 'rail_area'] = "web"

    # for flange (zdir != 0) add the rail side
    # if y > rail ref => left of the rail
    # define a at_left series
    at_left = to_numeric(df.rail_position.str[1:]) < df.ye
    df.loc[(df.zdir !=0) & at_left, 'rail_side'] = 'left'
    # other flange are at right
    df.loc[(df.zdir !=0) & isna(df.rail_side), 'rail_side'] = 'right'

    # create colums describing elements tighted by assembly (only name)
    df['el_to_tight'] = df[['crossbeam_side', 'rail_area', 'rail_position', 'xe', 'rail_side']]\
                        .apply(build_element_stack, axis=1)

    # create colums describing element tighted by assembly (only references)
    # use parts_data object to get refrence
    df['ref_to_tight'] = df[['el_to_tight', 'rail_position']]\
                        .apply(replace_reference,
                               parts_data=parts_data,
                               axis=1)

    # TODO insert tmp drilling and fastening informations

    return df

  @staticmethod
  def __build_fastener_class_node(definition:Series)->FClass:
    uid = definition.reference.lower()
    reference = definition.reference
    _type = definition.fastener_type
    diameter = definition.fastener_diameter
    description=definition.fastener_type
    
    return FClass(uid=uid,
                 description=description,
                 reference=reference,
                 type=_type,
                 diameter=diameter)

  @staticmethod
  def __build_fastener_instance_node(definition:Series)->FInstance:
    description="fastener "+ definition.aname
    reference=definition.reference
    uid=str(definition.id)
    
    return FInstance(description=description,
                    reference=reference,
                    uid=uid.lower())

  @classmethod
  def __build_fastener_instance_definition(cls, definition:Series,
                                           mother_node:FClass)->InstanceDefinition:
    node = cls.__build_fastener_instance_node(definition)

    return InstanceDefinition(node,
                              mother_node)


  @staticmethod
  def __build_assembly_node(definition:Series)->Assembly:
    origin = NeomodelPoint(x=definition.xe, y=definition.ye, z=definition.ze)
    orient = [definition.xdir, definition.ydir, definition.zdir]
    description = "assembly "+definition.aname
    uid = str(definition.id)
    
    return Assembly(origin=origin,
                    orient=orient,
                    description=description,
                    uid=uid.lower())

  @staticmethod
  def __build_assemble_definition(stack_def:List, parts_data:PartsData) -> List[AssembleRS]:
    stack = []
    for index, definition in enumerate(stack_def):
      # get the part node (first index)
      ref, thickness, material = definition
      part_def = parts_data.instances.get(ref)

      assert part_def, f'{ref} not found in parts instances collection'

      stack_el = AssembleRS(part_def.node,
                            thickness,
                            material,
                            index)

      stack.append(stack_el)
    
    return stack

  @staticmethod
  def __build_pattern_definition(definition:Series, pattern_data:PatternData) -> List[Area]:

    pattern = [definition.rail_area, definition.rail_position,
               definition.rail_side, definition.crossbeam_side]
    return [pattern_data.areas.get(area) for area in pattern if not isna(area)]


  @classmethod
  def build_from_file(cls, source_file:str,
                      parts_data:PartsData,
                      pattern_data:PatternData)->'AssembliesData':

    master_df = cls.__build_master_dataframe(source_file, parts_data)
    fclass_df = master_df[['reference', 'fastener_type', 'fastener_diameter']]\
                .drop_duplicates('reference')
    finstance_df = master_df[['id', 'reference', 'aname']]

    assy_df = master_df[['xe', 'ye', 'ze',
                         'xdir', 'ydir', 'zdir',
                         'aname', 'id',
                         'rail_area', 'crossbeam_side',
                         'rail_side', 'rail_position']]

    assy_df['stack'] = master_df[['parts_material_stack', 'ref_to_tight', 'parts_thickness_stack']]\
                       .apply(generate_stack, axis=1)

    fclass_collection = {}
    for row in fclass_df.iterrows():
      _, definition = row
      node = cls.__build_fastener_class_node(definition)
      fclass_collection[definition.reference.lower()] = BasicDefinition(node)
    
    finstance_collection = {}
    for row in finstance_df.iterrows():
      _, definition = row

      class_def = fclass_collection.get(definition.reference.lower())
      assert class_def, f'{definition.reference} not found in fastener class_collection'
      
      finstance_def = cls.__build_fastener_instance_definition(definition,
                                                               class_def.node)
      
      finstance_collection[definition.aname.lower()] = finstance_def

    fasteners = FastenersData(fclass_collection, finstance_collection)
    
    assy_collection = {}
    for row in assy_df.iterrows():
      _, definition = row
      node = cls.__build_assembly_node(definition)
      
      assemble = cls.__build_assemble_definition(definition.stack,
                                                 parts_data)

      pattern = cls.__build_pattern_definition(definition,
                                               pattern_data)

      finstance_def = fasteners.instances.get(definition.aname.lower())
      assert finstance_def, f'{definition.aname} not found in fastener instance_collection'
     
      coll_obj = AssemblyDefinition(node,
                                    finstance_def.node,
                                    assemble,
                                    pattern)

      assy_collection[definition.aname.lower()] = coll_obj

    return cls(assy_collection, fasteners)
    
  def save_data(self)->None:
    self.__fasteners.save_nodes()
    print('save and connect assembly nodes')
    
    for assy_def in tqdm(self.__assemblies.values()):
      node = assy_def.node
      fastener = assy_def.fastener
      assemble = assy_def.assemble
      pattern = assy_def.pattern

      node.save()
      node.fastener.connect(fastener)
      
      for stackel in assemble:
        node.assemble.connect(stackel.part, stackel.definition)
      
      for area_def in pattern:
        node.pattern.connect(area_def.node)



      
