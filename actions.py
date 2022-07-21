from pandas import DataFrame, Series, isna, notna
from pymongo import MongoClient
from assets import AssetsData
import df_functions as dff
from typing import List, Dict
# from model import action, equipment
# from model import definition
from operations import OpInstanceDefinition, OperationType, OperationsData
from pattern import PatternData
from utils import BasicDefinition, get_config_from_file
from states import SCDefinition,\
                   PreconditionRS,\
                   ResultRS,\
                   StatesData,\
                   Relation
from neo4mars.resource.action import Action as ActionNode

from model.action import Action
from model.definition import Drilling, Manipulation,\
                             Path, Probing
import model.movement as MMvt
import yaml
from model.equipment import Operation
import numpy as np
import model
from tqdm import tqdm
from typing import Tuple

COLLECTION = 'carrier'
RAILS = {1:'y-1292', 2:'y-763', 3:'y-254', 4:'y+254', 5:'y+763', 6:'y+1292'}
ARM_CONFIG = {
  'wrist':{
    'F':MMvt.WristConfig.FLIP,
    'N':MMvt.WristConfig.NOFLIP
  },
  'forearm':{
    'U':MMvt.ForeArmConfig.UP,
    'D':MMvt.ForeArmConfig.DOWN
  },
  'arm':{
    'T': MMvt.ArmConfig.TOWARD,
    'B': MMvt.ArmConfig.BACKWARD
  }
}

EFFECTORS_STATES = {
  'web': 'web_c_drilling',
  'flange':'flange_c_drilling'
}

MONGO_SERVER_HOST = 'debianvm'
MONGO_SERVER_PORT = 27017
MONGO_DATABASE = 'mars'

def get_arm_configuration(wrist:str, forearm:str, arm:str):
  wrist = ARM_CONFIG['wrist'][wrist]
  forearm = ARM_CONFIG['forearm'][forearm]
  arm = ARM_CONFIG['arm'][arm]

  return MMvt.Configuration(wrist, forearm, arm)


def get_movement_from_data(mvt_data:Series):

    vector = np.array([ # arm position
        mvt_data.x_j1,
        mvt_data.y_j2,
        mvt_data.z_j3,
        mvt_data.w_j4,
        mvt_data.p_j5,
        mvt_data.r_j6
    ])

    e1 = mvt_data.e1  # 7° axe position
    speed = mvt_data.speed  # mvt speed
    cnt = mvt_data.cnt  # mvt precision
    path = mvt_data.path  # mvt type of trajectory
    pos_type = mvt_data.position_type  # mvt position type

    if pos_type == "JOINT":
        position = MMvt.PositionJoint(vector, e1)
    elif pos_type == "CRT":
        config = get_arm_configuration(mvt_data.wrist,
                                       mvt_data.forearm,
                                       mvt_data.arm)
                        
        position = MMvt.PositionCrt(vector, e1, config)
    else:
        raise Exception("Parsing default : {pos_type} not valid.")

    # get the movement type
    mov_type = MMvt.MovementType[path]
    
    # build movement
    return MMvt.Movement(cnt, speed, mov_type, position)

class ActionDefinition(SCDefinition):
  def __init__(self,
               node: ActionNode,
               action:Action,
               preconditions: List[PreconditionRS],
               results: List[ResultRS],
               assets:List[BasicDefinition],
               pattern:List[BasicDefinition],
               operations:List[OpInstanceDefinition]):
    super().__init__(node, preconditions, results)
    self.__action = action
    self.__assets = assets
    self.__pattern = pattern
    self.__operations = operations
  
  @property
  def action(self):
    return self.__action
  
  @property
  def assets(self):
    return self.__assets

  @property
  def pattern(self):
    return self.__pattern

  @property
  def operations(self):
    return self.__operations

  def to_dict(self):
    action_def = self.__action.to_dict()
    action_def.pop('_id')
    return action_def

def fill_mvt_configuration(configuration:Dict, config_args:Dict):
  
  config_txt = yaml.dump(configuration)

  for args, value in config_args.items():
    config_txt = config_txt.replace(args, value)

  config = yaml.load(config_txt, Loader=yaml.Loader)
  return config

class Movements:
  def __init__(self,
              stations:Dict[str,ActionDefinition],
              approaches:Dict[str,ActionDefinition],
              clearances:Dict[str,ActionDefinition],
              works:Dict[str,ActionDefinition]) -> None:
    self.__stations = stations
    self.__approaches = approaches
    self.__clearances = clearances
    self.__works = works

  @property
  def stations(self):
    return self.__stations
  @property
  def approaches(self):
    return self.__approaches
  @property
  def clearances(self):
    return self.__clearances
  @property
  def works(self):
    return self.__works
class ActionsData:

  PATH = ['JOINT', 'LINEAR', 'CIRCULAR']
  POS_TYPE = ['JOINT', 'CRT']
  WRIST = ['F', 'N', None]
  FOREARM = ['U', 'D', None]
  ARM = ['T','D', None]
  WORK_MVT = ['station', 'approach', 'work', 'clearance']
  CONFIG_MVT = ['home', 'tool']

  WEB_MOVEMENTS_COL = ['rail', 'mvt', 'localisation', # 'designation',
                       'reference', 'id', 'point', 'path',
                       'position_type', 'speed', 'cnt',
                       'x_j1','y_j2', 'z_j3',
                       'w_j4', 'p_j5', 'r_j6', 'e1', 
                       'wrist', 'forearm', 'arm',
                       'conf_j1', 'conf_j4', 'conf_j6',
                       'UF', 'UT']
  
  ACTIONS_TYPE = {
    'station':'MOVE.STATION.WORK',
    'work':'MOVE.TCP.WORK',
    'approach':'MOVE.TCP.APPROACH',
    'clearance':'MOVE.TCP.CLEARANCE',
    'home':'MOVE.STATION.HOME',
    'tool':'MOVE.STATION.TOOL'
  }

  MVT_COL = ["x_j1", "y_j2", "z_j3",
             "w_j4", "p_j5", "r_j6",
             "e1", "speed", "cnt",
             "path","position_type", 
             "wrist", "forearm", "arm", 
             "UT", "UF",
             "reference", "id"]

  UT_CODE = {
    1: "NO_EFFECTOR",
    2: "WEB_C_DRILLING",
    3: "FLANGE_C_DRILLING"
  }

  UF_CODE = {
    3: "CELL_FRAME"
  }

  def __init__(self,
               manipulations_collection:Dict[str,ActionDefinition],
               movemements_collection:Movements,
               operation_collection:Dict[str, ActionDefinition]):

    self.__manipulations = manipulations_collection
    self.__movements = movemements_collection
    self.__operations = operation_collection

  @property
  def manipulations(self):
    return self.__manipulations
  
  @property
  def movements(self):
    return self.__movements

  @property
  def operations(self):
    return self.__operations

  @classmethod
  def __build_relationships(cls, preconditions:Dict,
                            results:Dict,
                            states_data:StatesData) -> Tuple[List[PreconditionRS], List[ResultRS]]:
    preconditions_rs = []
    for precondition in preconditions:
      state_def = states_data.states.get(precondition['state_object'])
      assert state_def, f"{precondition['state_object']} not in states data"
      relation = Relation[precondition['relation']]
      precond_rs = PreconditionRS(property_node=state_def.node,
                                relation=relation,
                                state=precondition['state'],
                                priority=precondition['priority'])
      preconditions_rs.append(precond_rs)

    results_rs = []
    for result in results:
      property_def = states_data.states.get(result['state_object'])
      assert property_def, f"state {result['state_object']} not in states collection"
      property_node = property_def.node
      
      relation = Relation[result['relation']]
      
      result_rs = ResultRS(property_node=property_node,
                            relation=relation,
                            state=result['state'],
                            description=result['description'])
      results_rs.append(result_rs)
    
    return preconditions_rs, results_rs

  @classmethod
  def __build_manipulation_definition(cls, manipulation:Dict,
                                      states_data:StatesData,
                                      assets_data:AssetsData) -> Tuple[str, ActionDefinition]:
    equipment_def = manipulation['equipment']
    operation = manipulation['operation']

    equipment = model.\
                EQUIPMENT[equipment_def['type']]\
                          [equipment_def['reference']]

    action_type = '.'.join([operation, equipment.type])

    description = manipulation['description']
    definition = Manipulation(Operation[operation], equipment)
    
    action = Action('', action_type, definition, description)
    preconditions = manipulation['preconditions']
    results = manipulation['results']
    
    action_node = ActionNode(description=description,
                              type=action_type,
                              collection=COLLECTION)

    action_preconditions, actions_results = cls.__build_relationships(preconditions=preconditions,
                                                                     results=results,
                                                                     states_data=states_data)
    mars = assets_data.assets.get('mars')
    assert mars, f"assets mars not in assets collection"
    effector = assets_data.assets.get(equipment_def['reference'].lower())
    assert effector, f"assets {equipment_def['reference']} not in assets collection"
    human = assets_data.assets.get('human')
    assert human, f"assets human not in assets collection"
    assets = [mars, effector, human]

    pattern = []
    operations = []

    action_definition = ActionDefinition(node=action_node,
                                         action=action,
                                         preconditions=action_preconditions,
                                         results=actions_results,
                                         assets=assets,
                                         pattern=pattern,
                                         operations=operations)
    
    coll_key = '_'.join([operation, equipment.reference]).lower()
    return coll_key, action_definition


  @classmethod
  def __build_path_definition(cls,
                              mvt_type:str,
                              movement_config:Dict,
                              action_type:str,
                              mvt_data:DataFrame,
                              states_data:StatesData,
                              assets_data:AssetsData=None,
                              pattern_data:PatternData=None,
                              rail_area:str=None,
                              rail_position:str=None,
                              assemblies_uids:Dict[str,str]=None,
                              localisation:str=None):
    
    # get data first line to extract data in the folowwing processing
    fmvt_data = mvt_data.iloc[0]
    # get localisation information, if nan empty list
    sides = localisation.split('_') if localisation and notna(localisation) else []

    # if variables information in configuration
    config_var = movement_config.get('variables')
    if config_var:
      # build data to fill config
      config_args = {}
      if '$area' in config_var:
        config_args['$area'] = ' '.join([rail_area] + sides).lower()
        config_args['$rail'] =  rail_position
      if '$station' in config_var:
        config_args['$station'] = '_'.join([rail_area, rail_position] + sides).lower()
      if '$effector' in config_var:
        config_args['$effector'] = EFFECTORS_STATES[rail_area]
      if '$approach' in config_var:
        config_args['$approach'] = '_'.join([rail_area, rail_position] + sides).lower()
      if '$kfront' in config_var:
        config_args['$kfront'] = StatesData.generate_probing_uid(rail_position, 'front')
      if '$krear' in config_var:
        config_args['$krear'] = StatesData.generate_probing_uid(rail_position, 'rear')
      if '$work' in config_var:
        assy_ref = fmvt_data.reference
        assy_id = fmvt_data.id

        assykey = f'{assy_ref}.{assy_id}'.lower()
        assy_uid = assemblies_uids.get(assykey)

        assert assy_uid, f"error: {assykey} not in fastener data"
        config_args['$work'] = assy_uid
        config_args['$assembly'] = assykey

      #fill configuration
      movement_config = fill_mvt_configuration(movement_config,
                                               config_args)

    # build node 
    action_node = ActionNode(description=movement_config['description'],
                             type=action_type,
                             collection=COLLECTION)

   
    # processing to build Action definition for mongo document
    movements = []
    for row in mvt_data.iterrows():
      _, mvt_def = row
      movements.append(get_movement_from_data(mvt_def))

    #get user tool and frame information
    ut_code = fmvt_data.UT
    ut_name = cls.UT_CODE[ut_code]
    ut = model.EQUIPMENT['EFFECTOR'][ut_name]

    uf_code = fmvt_data.UF
    uf_name = cls.UF_CODE[uf_code]
    uf = model.REFERENCE['FRAME'][uf_name]

    path = Path(uf, ut, movements)

    # build action
    mvt_action = Action('',action_type,
                        path,
                        movement_config['description'])

    mvt_preconditions, mvt_results = cls.__build_relationships(preconditions=movement_config['preconditions'],
                                                               results=movement_config['results'],
                                                               states_data=states_data)
    
    assets = []
    pattern = []
    operations = []

    if mvt_type in ['work', 'approach', 'clearance', 'station']:
      if rail_area == 'web':
        assets.append(assets_data.assets.get('web_c_drilling'))
        pattern.append(pattern_data.areas.get('web'))
      elif rail_area == 'flange':
        assets.append(assets_data.assets.get('flange_c_drilling'))
        pattern.append(pattern_data.areas.get('flange'))

      assets.append(assets_data.assets.get('mars'))

    if rail_position:
      area = pattern_data.areas.get(rail_position)
      assert area, f"area {rail_position} not in pattern data"
      pattern.append(area)
    if localisation:
      crossbeam_side, rail_side = localisation.lower().split('_')
      
      crossbeam_side_def = pattern_data.areas.get(crossbeam_side)
      assert crossbeam_side_def, f"area {crossbeam_side} not in pattern data"
      pattern.append(crossbeam_side_def)

      rail_side_def = pattern_data.areas.get(rail_side)
      assert rail_side_def, f"area {rail_side} not in pattern data"
      pattern.append(rail_side_def)


    action_def = ActionDefinition(node=action_node,
                                  action=mvt_action,
                                  preconditions=mvt_preconditions,
                                  results=mvt_results,
                                  assets=assets,
                                  pattern=pattern,
                                  operations=operations)

    #build key for collection
    if mvt_type == 'work':
      assy_ref = fmvt_data.reference
      assy_id = fmvt_data.id
      key = f'{assy_ref}.{assy_id}'.lower()
    elif mvt_type in ['station', 'approach', 'clearance']:
      key = "_".join([rail_area, rail_position] + sides).lower()
    else:
      key = mvt_type

    return key, action_def
  
  @classmethod
  def __build_movements_collection(cls,
                                        rail_area:str,
                                        mvt_data:DataFrame,
                                        mvt_config:Dict[str, Dict],
                                        states_data:StatesData,
                                        assemblies_uids:Dict[str, str],
                                        assets_data:AssetsData,
                                        pattern_data:PatternData):
    
    movements_collection = {
      "work":{},
      "station":{},
      "approach":{},
      "clearance":{}
    }

    # update the web data point columns to avoid double value
    mvt_data.point = mvt_data.point + mvt_data.rail * 100
    # create a key column - concat of id and reference
    mvt_data['key'] = mvt_data.reference + '.' + mvt_data.id.astype('str')
    # group the data by rail - mvt - point - key - point
    # now df index is rail - mvt - point
    
    if not isna(mvt_data.localisation).all():
      mvt_data = mvt_data\
                .groupby(['rail', 'mvt', 'key', 'localisation', 'point'])\
                .first()
    else:
      mvt_data = mvt_data\
                .groupby(['rail', 'mvt', 'key', 'point'])\
                .first()
    
    # loop throw the rail list
    for rail_id, rail_position in RAILS.items():
      # loop throw the movements
      for mvt in cls.WORK_MVT:
        # get action type according the movement
        action_type = cls.ACTIONS_TYPE[mvt]
        # get the configuration (preconditions, results) in the movement config
        movement_config = mvt_config[mvt]

        # get data relative to rail_id - mvt with only the columns describing the movements
        rail_mvt_df = mvt_data.loc[(rail_id, mvt), cls.MVT_COL]
        # get the uniq keys in the index
        
        if 'localisation' in rail_mvt_df.index.names :
          key_locs = set([(key, loc) for key, loc, point in rail_mvt_df.index])
          for key, localisation in key_locs:
            mvt_df = rail_mvt_df.loc[key, localisation]
            action_key, action_def = cls.__build_path_definition(mvt,
                                                                movement_config,
                                                                action_type,
                                                                mvt_df,
                                                                states_data,
                                                                assets_data,
                                                                pattern_data,
                                                                rail_area,
                                                                rail_position,
                                                                assemblies_uids,
                                                                localisation)

            movements_collection[mvt][action_key] = action_def
        else:
          keys  = rail_mvt_df.index\
                .get_level_values('key')\
                .drop_duplicates()

          for key in keys:
            mvt_df = rail_mvt_df.loc[key]
            action_key, action_def = cls.__build_path_definition(mvt,
                                                                  movement_config,
                                                                  action_type,
                                                                  mvt_df,
                                                                  states_data,
                                                                  assets_data,
                                                                  pattern_data,
                                                                  rail_area,
                                                                  rail_position,
                                                                  assemblies_uids)

            movements_collection[mvt][action_key] = action_def
        
    return movements_collection

  @classmethod
  def __build_probing_collection(cls, 
                                 works_movements:Dict[str, ActionDefinition],
                                 states_data:StatesData,
                                 assets_data:AssetsData):
    
    action_type = 'WORK.PROBE'
    probing_effector = 'flange_c_drilling'
    preconditions_stateobjects = ['tcp_work', 'station', 'effector', 'tcp_approach']

    probing_collection = {}
    probing_assies = states_data.get_probed_assy()

    for assy, stdef in probing_assies.items():
      work = works_movements.get(assy)

      assert work, f'the assembly {assy} not exist in work movement collection'
      
      # get probing precondition => work precondition - kf states relationship
      probing_preconditions = [precondition for precondition in work.preconditions\
                               if precondition.property_node.uid in preconditions_stateobjects]
      
      last_priority = probing_preconditions[-1].priority

      probing_preconditions.append(PreconditionRS(property_node=stdef.node,
                                                  relation=Relation.NOT_EQUAL,
                                                  state='probed',
                                                  priority=last_priority+1))

      probing_results = [ResultRS(property_node=stdef.node,
                                  relation=Relation.EQUAL,
                                  state='probed',
                                  description=f"reference {stdef.node.uid} probed")]

      waction_def:Path = work.action.definition
      ut = waction_def.user_tool
      uf = waction_def.user_frame
      movement = waction_def.movements[0]

      probing_definition = Probing(ut, uf, movement)
      action = Action('',
                      action_type,
                      probing_definition,
                      f'probing of reference {stdef.node.uid}')

      probing_node = ActionNode(description=f'probing of reference {stdef.node.uid}',
                                type=action_type,
                                collection=COLLECTION)
      
      effector = assets_data.assets.get(probing_effector)
      assert effector, f'the effector {probing_effector} not exist in assets collection'

      mars = assets_data.assets.get('mars')
      assert mars, f'the carrier mars not exist in assets collection'

      assets = [effector, mars]

      action_definition = ActionDefinition(probing_node,
                                           action,
                                           probing_preconditions,
                                           probing_results,
                                           assets=assets,
                                           pattern=[],
                                           operations=[])

      probing_collection[f'p{assy}'] = action_definition

    return probing_collection


  @classmethod
  def __build_drilling_collection(cls, 
                                  works_movements:Dict[str, ActionDefinition],
                                  operations_data:OperationsData,
                                  assets_data:AssetsData):
    
    action_type = 'WORK.DRILL'

    drilling_collection = {}

    for assy, work_def in works_movements.items():
      drilling_preconditions = work_def.preconditions.copy()
      last_priority = drilling_preconditions[-1].priority
      
      for result in work_def.results:
        drilling_preconditions.append(PreconditionRS(property_node=result.property_node,
                                                     relation=Relation.EQUAL,
                                                     state=result.state,
                                                     priority=last_priority+1))

    
      results = []
      pattern = []

      mars = assets_data.assets.get('mars')
      assert mars, f'the carrier mars not exist in assets collection'
      assets = [mars]

      wpattern = [area_def.node.uid for area_def in work_def.pattern]
      
      if 'flange' in wpattern:
        effector = assets_data.assets.get('flange_c_drilling')
      elif 'web' in wpattern:
        effector = assets_data.assets.get('web_c_drilling')
      assert effector, f'no effector with key web_c_drilling or flange_c_drilling exist in assets collection'
      assets.append(effector)

      operation_key = OperationsData.generate_uid(OperationType.DRILL, assy)
      operations = [operations_data.instances.get(operation_key)]

      drilling_node = ActionNode(description=f'drilling of assembly {assy}',
                                type=action_type,
                                collection=COLLECTION)

      drilling_definition = Drilling(10,10,True)
      
      action = Action('',
                      action_type,
                      drilling_definition,
                      f'drilling of assembly {assy}')

      drilling_def = ActionDefinition(node=drilling_node,
                                      action=action,
                                      preconditions=drilling_preconditions,
                                      results=results,
                                      assets=assets,
                                      pattern=pattern,
                                      operations=operations)
      
      drilling_collection[f'd{assy}'] = drilling_def

    return drilling_collection
  
  @classmethod
  def build_from_files(cls, 
                       chconf_movements_file:str,
                       web_movements_file:str,
                       flange_movements_file:str,
                       manipulations_yaml_file:str,
                       movements_yaml_file:str,
                       states_data:StatesData,
                       operations_data:OperationsData,
                       assemblies_uids:Dict[str,str],
                       assets_data:AssetsData,
                       pattern_data:PatternData) -> 'ActionsData':
    mvt_checks = {
      'path': cls.PATH,
      'position_type' : cls.POS_TYPE,
      'wrist': cls.WRIST,
      'forearm': cls.FOREARM,
      'arm': cls.ARM,
      'mvt': cls.WORK_MVT + cls.CONFIG_MVT
    }

    # import the web data
    web_mov_df = dff.build_and_check(web_movements_file,
                                    'csv',
                                    cls.WEB_MOVEMENTS_COL,
                                    mvt_checks)

    # import the flange data   
    flange_mov_df = dff.build_and_check(flange_movements_file,
                                    'csv',
                                    cls.WEB_MOVEMENTS_COL,
                                    mvt_checks)

    manipulations_config = get_config_from_file(manipulations_yaml_file)
    movements_config = get_config_from_file(movements_yaml_file)
    movements_config = movements_config['movements']

    manipulations_collection = {}
    for manipulation in manipulations_config['manipulations']:
      key, action_definition = cls.__build_manipulation_definition(manipulation,
                                                                   states_data,
                                                                   assets_data)
      manipulations_collection[key] = action_definition
    
    # init the movement collection
    movements_collection = {
      "work":{},
      "station":{},
      "approach":{},
      "clearance":{}
    }

    web_mvt = cls.__build_movements_collection('web',
                                               web_mov_df,
                                               movements_config,
                                               states_data,
                                               assemblies_uids,
                                               assets_data,
                                               pattern_data)

    for key in web_mvt:
      movements_collection[key].update(web_mvt[key])

    flange_mvt = cls.__build_movements_collection('flange',
                                               flange_mov_df,
                                               movements_config,
                                               states_data,
                                               assemblies_uids,
                                               assets_data,
                                               pattern_data)

    for key in flange_mvt:
      movements_collection[key].update(flange_mvt[key])
    
    # build changeconfig movement collection
    # import the change conf data 
    chconf_mov_df = dff.build_and_check(chconf_movements_file,
                                        'csv',
                                        cls.WEB_MOVEMENTS_COL,
                                        mvt_checks)

    for mvt in cls.CONFIG_MVT:
      mvt_data_df = chconf_mov_df[chconf_mov_df.mvt == mvt]
      movement_config = movements_config[mvt]
      action_type = cls.ACTIONS_TYPE[mvt]
      key, definition = cls.__build_path_definition(mvt,
                                               movement_config,
                                               action_type,
                                               mvt_data_df,
                                               states_data)

      movements_collection['station'][key] = definition

    movements = Movements(movements_collection['station'],
                          movements_collection['approach'],
                          movements_collection['clearance'],
                          movements_collection['work'])

    operations_collection = {}

    probings_collection = cls.__build_probing_collection(movements.works,
                                              states_data,
                                              assets_data)
    operations_collection.update(probings_collection)
    drillings_collection = cls.__build_drilling_collection(movements.works,
                                                           operations_data,
                                                           assets_data)
    operations_collection.update(drillings_collection)

    return cls(manipulations_collection, movements, operations_collection)

  @staticmethod
  def __save_in_mongo(action_collection:Dict[str, ActionDefinition]):
    
    mclient = MongoClient(MONGO_SERVER_HOST, MONGO_SERVER_PORT)
    carrier = mclient.get_database(MONGO_DATABASE).get_collection(COLLECTION)

    action_definitions = [action_def.action.to_dict(drop_id=True) for action_def in action_collection.values()]

    res = carrier.insert_many(action_definitions)

    if not res.acknowledged :
        raise Exception("Error during insertion") 
    else :
      mongo_ids = res.inserted_ids
      
      index=0
      for action_def in action_collection.values():
        action_def.node.uid = str(mongo_ids[index])
        index+=1
  
  @staticmethod
  def __save_nodes_and_connect(actions_collection:Dict[str, ActionDefinition]):
    
    for key, action_def in tqdm(actions_collection.items()):
      node:ActionNode = action_def.node
      preconditions = action_def.preconditions
      results = action_def.results
      assets = action_def.assets
      pattern = action_def.pattern
      operations = action_def.operations

      node.save()

      for precond in preconditions:
        node.preconditions.connect(precond.property_node,
                                   precond.definition)

      for result in results:
        node.results.connect(result.property_node,
                             result.definition)
      
      for asset_def in assets:
        node.assets.connect(asset_def.node)

      for area_def in pattern:
        node.areas.connect(area_def.node)

      for operation_def in operations:
        node.operations.connect(operation_def.node)

  def save_data(self):
    print('save actions in mongodb')
    print('save manipulations in mongodb')
    self.__save_in_mongo(self.__manipulations)
    print('save work movements in mongodb')
    self.__save_in_mongo(self.__movements.works)
    print('save approach movements in mongodb')
    self.__save_in_mongo(self.__movements.approaches)
    print('save clearance movements in mongodb')
    self.__save_in_mongo(self.__movements.clearances)
    print('save station movements in mongodb')
    self.__save_in_mongo(self.__movements.stations)
    print('save operations in mongodb')
    self.__save_in_mongo(self.__operations)
    print('mongodb saving done')

    print('save actions in neo4j')
    print('save manipulations in neo4j')
    self.__save_nodes_and_connect(self.__manipulations)
    print('save work movements in neo4j')
    self.__save_nodes_and_connect(self.__movements.works)
    print('save approach movements in neo4j')
    self.__save_nodes_and_connect(self.__movements.approaches)
    print('save clearance movements in neo4j')
    self.__save_nodes_and_connect(self.__movements.clearances)
    print('save station movements in neo4j')
    self.__save_nodes_and_connect(self.__movements.stations)
    print('save operations in neo4j')
    self.__save_nodes_and_connect(self.__operations)
    print('neo4j saving done')




