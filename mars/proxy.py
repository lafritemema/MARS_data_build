
from enum import Enum, EnumMeta
import uuid

from zmq import SUBSCRIBE
from model.definition import Manipulation
from typing import List, Dict, Union, Tuple
from copy import deepcopy
from inspect import signature
from model.movement import Position, Movement
from model.command import Command
from utils import GetAttrEnum, GetItemEnum

"""
CONSTANTS
"""
DEFAULT_TRACKING_INTERVAL = 1000

"""
ENUMERATIONS
"""

# Enumeration defining the Register bulk
class RegisterBulk(Enum, metaclass=GetAttrEnum):
  SINGLE = "/single"
  BLOCK = "/block"
  ALL = "/all"

# Enumeration defining the register types
class RegisterType(Enum):
  STRING = "/stringRegister", 5, 5, None, "text"
  POSITION_JOINT = "/positionRegister", 10, 10, 'jnt', "position"
  POSITION_CARTESIAN = "/positionRegister", 10, 10, 'crt', "position"
  NUMERIC_INT = "/numericRegister", 120, 115, 'int', "value"
  NUMERIC_FLOAT = "/numericRegister", 120, 115, 'float', "value"

  @property
  def base_path(self):
    return self.value[0]

  @property
  def read_limit(self):
    return self.value[1]

  @property
  def write_limit(self):
    return self.value[2]
  
  def build_query(self, start_register:int, block_size:int =1):
    if block_size > 1:
      query =  {
        'startReg' : start_register,
        'blockSize' : block_size
      }
    else :
      query = {
        'reg':start_register
      }

    if self.value[3]:
        query['type'] = self.value[3]
    
    return query
  
  def build_body(self, data:Union[Dict, str, int, float, List[Dict], List[str], List[int], List[float]]):
    #init a dict
    body = {}
    # get the key according the register type
    key = self.value[4]

    # if data is a list or tuple
    if type(data) == list or type(data) == tuple:
      # add a s to the key and fill the body
      body[key+'s'] = data
      return body
    else:
       # fill the body with initial key
      body[key] = data
      return body

class ConstantRegister(Enum, metaclass=GetAttrEnum):
  UT = 18
  UF = 19
  PROGRAM = 1
  PROCESS = 9
  MOVEMENT_PARA_BEGIN = 20
  POSITION_BEGIN = 1
  EFFECTOR_REFERENCE = 150
  CUTTING_TOOL = 151
  DRILLING_PARA_BEGIN = 155
  DRILLING_FEEDBACK_BEGIN = 166
  DRILLING_COUNTER = 162
  CLAMPING_COUNTER = 163

class ConstantRegBlockSize(Enum, metaclass=GetAttrEnum):
  DRILLING_FEEDBACK = 7

class Relation(Enum):
  EQUAL = "eq"
  NOT_EQUAL = "neq"

class Process(Enum):
  IN_PROGRESS = -1
  SUCCESS = 0
  ERROR = 1

class Program(Enum):
  TRAJ_GEN = 1
  DRILLING = 2
  CHANGE_UTUF = 3
  PROBING = 4

class MovementTypeCode(Enum, metaclass=GetItemEnum):
  JOINT = 1
  LINEAR = 2
  CIRCULAR = 3

class ProxyAction(Enum):
  REQUEST = 'REQUEST'
  WAIT = 'WAIT'

class Frame(Enum):
  CELL_FRAME = 3

class ProxyEquipmentI(EnumMeta):
  def _get_tracker_def(self, operation:str):
    pass
  @staticmethod
  def _get_register_info():
    pass

class Effector(Enum, metaclass=ProxyEquipmentI):
  WEB_C_DRILLING = 2
  FLANGE_C_DRILLING = 3
  NO_EFFECTOR = 1

  def _get_tracker_def(self, operation:str):
    fct = getattr(Effector, operation)
    if (len(signature(fct).parameters)) > 0:
      return fct(self)
    else:
      return fct()
      

  @staticmethod
  def LOAD(effector:'Effector') -> Tuple[str, int]:
    return (Relation.EQUAL.value, effector.value)
  
  @staticmethod
  def UNLOAD() -> Tuple[str, int]:
    return (Relation.EQUAL.value, Effector.NO_EFFECTOR.value)

  @staticmethod
  def _get_register_info() -> Tuple[RegisterType, int]:
    return RegisterType.NUMERIC_INT, ConstantRegister.EFFECTOR_REFERENCE

class ProxyEquipment(Enum, metaclass=GetItemEnum):
  EFFECTOR = Effector

class ProxyMethod(Enum):
  GET = "GET"
  PUT = "PUT"
  SUBSCRIBE= "SUBSCRIBE"

"""
PROXYCOMMAND OBJECT
"""
class ProxyCommand(Command):
  def __init__(self,
               action:ProxyAction,
               description:str,
               method:ProxyMethod,
               path:str,
               query:Dict,
               body:Dict):

    definition = {
      "method":method.value,
      "path":path,
      "query":query,
      "body":body
    }

    super().__init__("PROXY",
                     action.value,
                     description,
                     definition)


# WaitCommand object (uid is the command to wait)
class WaitCommand(Command):
  def __init__(self, description:str, uid:str):
    super().__init__("PROXY",
                     ProxyAction.WAIT.value,
                     description,
                     {'uid':uid})


"""
UTILITIES FONCTIONS
"""

def __split_data_by_limit(data: List[Union[Dict, int, str]],
                          size_limit: int) -> List[Union[Dict, int, float, str]] :
  """Split a list into a list of sublist with max size respecting the size limit
     Used to respect the fanuc register read and write limit  

  Args:
      data (List[Dict or int or str]): list to split
      size_limit (int): max size of a sublist

  Returns:
      List[List[Dict, int, float, str]]: a list of sublist respeting the size limit
  """

  sub_list = []
  i = 0
  step = 0
  while i < len(data):
      step += 1
      sub_list.append(data[i:step*size_limit])
      i += size_limit

  return sub_list

def __split_position_list_generator(position_list:List[Position]) -> Tuple[str, List[Position]]:
  
  pos_type = position_list[0].type
  index = 0
  while 1 :
      sublist = []
      while position_list[index].type == pos_type:
          sublist.append(position_list[index])
          index+=1
          if index >= len(position_list):
              yield pos_type, sublist
              return 0
      yield pos_type, sublist
      pos_type = position_list[index].type


"""
LOW LEVEL PROXY COMMANDS
"""

# low level proxy service -> read register
def __read_register(register_type:RegisterType,
                    start_register:int,
                    block_size:int=1) -> List[Tuple[str, str, Dict]]:
  """fonction to build a commmand definition to read a register or a list of registers

  Args:
      register_type (RegisterType): type of register to read
      start_register (int): the first register to read
      block_size (int, optional): number of register to read. Defaults to 1.

  Returns:
      List[Tuple[str, str, Dict]]: a list of tuple with (method, path, query)
  """


  # use routing block if block size > 1 else single
  if block_size > 1:
    routing = RegisterBulk.BLOCK
  else:
    routing = RegisterBulk.SINGLE

   # get method and path
  METHOD = ProxyMethod.GET
  PATH = register_type.base_path + routing

  # check if the block_size not upper than register read limit (defined by fanuc)
  if block_size > register_type.read_limit:

    # if block size is upper, split the packet in block
    # define a list
    commands = []
  
    index = start_register
    k_el = block_size

    # build a query dict for each block 
    while k_el > 0:
      
      el_number = k_el if k_el < register_type.read_limit else register_type.read_limit
      query = register_type.build_query(index, el_number)
      
      commands.append((METHOD, PATH, query))

      index += el_number
      k_el -= el_number
    
    # return the list of command
    return commands
  
  else:
    # build a query
    query = register_type.build_query(start_register, block_size)
    # return the command in an list
    return  [(METHOD, PATH, query)]
    
# low level proxy service -> write register
def __write_register(register_type:RegisterType,
                     start_register:int,
                     data:Union[Dict, str, int, float, List[Dict], List[str], List[int], List[float]]) -> List[Tuple[str, str, Dict, Dict]]:
  """function to build a command definition to write a register or a list of registers

  Args:
      register_type (RegisterType): the type of register
      start_register (int): first register to write
      data (Union[Dict, str, int, float, List[Dict], List[str], List[int], List[float]]): data to write in registers

  Returns:
      List[Tuple[str, str, Dict, Dict]] :  list of command definition under tuple format (method, path, query, body)
  """

  _data = data[0] if (type(data) == list or type(data) == tuple) and len(data) == 1 else data

  # if the data type => list
  if type(_data) == list or type(_data) == tuple:
    # use the block routing path
    routing = RegisterBulk.BLOCK
  else:
    # use the single routing path
    routing = RegisterBulk.SINGLE
  
  # define method an path
  METHOD = ProxyMethod.PUT
  PATH = register_type.base_path + routing

  #init a default body
  BODY = {
    "data" : None
  }

  # if data => list, 
  if type(_data) == list or type(_data) == tuple:
    # check the register write limit
    if len(_data) > register_type.write_limit:
      commands = []
      # split data to respect limits
      split_data = __split_data_by_limit(_data, register_type.write_limit)
      
      # begin to start register
      index = start_register
      
      # build query and body for each block
      for d in split_data:
        query = register_type.build_query(index, len(d))
        body = BODY.copy()
        body['data'] = register_type.build_body(d)
        
        commands.append(METHOD, PATH, query, body)
        # update the index
        index += len(d)
      
      return commands

    else:
      query = register_type.build_query(start_register, len(_data))
      body = BODY.copy()
      body['data'] = register_type.build_body(_data)
    
      return [(METHOD, PATH, query, body)]

  else :
    # fill the query and body parameters of base command dict
    query =  register_type.build_query(start_register)
    body = BODY.copy()
    body['data'] = register_type.build_body(_data)
    
    return [(METHOD, PATH, query, body)]

class TrackerType(Enum, metaclass=GetAttrEnum):
  ALERT = 'alert'
  REPORT = 'report'

# low level proxy service -> track register
def __track_register(register_type:RegisterType,
                   register_num:int,
                   interval:int=1000,
                   expected:Tuple[Relation, Union[str, int, float]]=None) -> Dict :
  """function to build a command definition to track the value of a specific register

  Args:
      register_type (RegisterType): type of register to track
      register_num (int): num of register to track
      interval (int, optional): traking frequency in ms. Defaults to 1000.
      expected (Tuple, optional): In case of alert type tracker, expected a tuple (relation, value). Defaults to None.

  Returns:
      Tuple[str, str, Dict, Dict]: a command definition under a Tuple format (method, path, query, body)
  """
  # routing => single
  routing = RegisterBulk.SINGLE

  # define method and path
  METHOD = ProxyMethod.SUBSCRIBE
  PATH = register_type.base_path + routing

  #define default body
  BODY = {
      "setting": None
  }
  
  tracker_uid = str(uuid.uuid4())

  # define the tracker settings
  # if expected, tracker type alert
  if expected:
    # build the expected body {relation:..., value: ...}
    expected_body = {
      "data": register_type.build_body(expected[1]),
      "relation": expected[0]
    }

    # build tracker setting body with expected informations
    tracker_setting = {
        "tracker": TrackerType.ALERT,
        "expected": expected_body,
        "interval": interval,
        "uid": tracker_uid
    }
  else:
    # build tracker setting body
    tracker_setting = {
        "tracker": TrackerType.REPORT,
        "interval": interval,
        "uid": tracker_uid
    }

  # define the tracker body
  tracker_body = {
        "type": "tracker",
        "settings": tracker_setting
    }
  
  # fill the query and body parameters of base command dict

  query = register_type.build_query(register_num)
  body = BODY.copy()
  body['setting'] = tracker_body

  return METHOD, PATH, query, body, tracker_uid


"""
HIGH LEVEL PROXY COMMAND
"""
def run_program(program:Program) -> List[ProxyCommand]:
  """function to generate the list of commands to necessary to launch a program

  Args:
      program (Program): program to launch

  Returns:
      List[ProxyCommand]: list of commands to launch the program
  """
  # get write command parameters, __write_register return a list, so get the item 0
  w_method, w_path, w_query, w_body = __write_register(RegisterType.NUMERIC_INT,
                                                       ConstantRegister.PROGRAM,
                                                       program.value)[0]

  # define a proxy command to write data => write program value on register
  set_program_cmd = ProxyCommand(ProxyAction.REQUEST,
                                 f"set program register to run {program.name} program (code : {program.value})",
                                 w_method,
                                 w_path,
                                 w_query,
                                 w_body)


  # get track command parameters
  t_method, t_path, t_query, t_body, tracker_uid = __track_register(RegisterType.NUMERIC_INT,
                                                       ConstantRegister.PROCESS,
                                                       DEFAULT_TRACKING_INTERVAL,
                                                      (Relation.NOT_EQUAL.value, Process.IN_PROGRESS.value))


  # define a proxy command to track end of program
  tracker_cmd = ProxyCommand(ProxyAction.REQUEST,
                             f"init tracker to track process register value wait until {Relation.NOT_EQUAL.name} {Process.IN_PROGRESS.name}",
                             t_method, t_path, t_query, t_body)

  # wait command with tracker uid
  wait_cmd = WaitCommand(f"wait end of program {program.name}", tracker_uid);
  # return the list of commands
  return [set_program_cmd, tracker_cmd, wait_cmd]


def set_utuf(user_tool:str, user_frame:str) -> List[ProxyCommand]:
  """function to generate the list of commands to update the user tool and the user frame

  Args:
      ut (str): effector id
      uf (str): frame id

  Returns:
      List[ProxyCommand]: list of command to update the informations
  """
  # get the proxy enumeration for user tool and user frame
  ut = Effector[user_tool]
  uf = Frame[user_frame]

  # get write command parameters __write_register return a list, so get the item 0
  w_method, w_path, w_query, w_body =  __write_register(RegisterType.NUMERIC_INT,
                                               ConstantRegister.UT,
                                               (ut.value, uf.value))[0]

  # init a command to set ut and uf
  set_utuf_cmd = ProxyCommand(ProxyAction.REQUEST,
                              f"update the user tool register : {ut.name} (code {ut.value}), update the user frame register: {uf.name} (code {uf.value})",
                              w_method,
                              w_path,
                              w_query,
                              w_body)
  
  # init a list with the set_utuf command
  commands = [set_utuf_cmd]
  # extend the list with commands to run the change_utuf program
  commands.extend(run_program(Program.CHANGE_UTUF))
  
  return commands


def __set_movements_parameters(movements_parameters:List[int]) -> List[ProxyCommand]:
  """function to generate list of commands to set movement parameters

  Args:
      movements_parameters (List[int]): movements parameters to set

  Returns:
      List[ProxyCommand]: list of proxy command to set parameters
  """

  # get the command definition using write_register function
  # if size of parameters list exceed the number of insertion in one shot (E/IP fanuc limit) the function return a list of cmd def
  w_cmd_def = __write_register(RegisterType.NUMERIC_INT,
                               ConstantRegister.MOVEMENT_PARA_BEGIN,
                               movements_parameters)

  commands = []
  for method, path, query, body in w_cmd_def:
    # generate a proxy command for each definitions
    cmd = ProxyCommand(ProxyAction.REQUEST,
                       "set num of movements and movements parameters (speed, cnt and type) in numeric registers.",
                       method,
                       path,
                       query,
                       body)
    
    # and append to the list of commands
    commands.append(cmd)

  return commands

def __set_movements_positions(positions:List[Position]) -> List[ProxyCommand]:
  """function to generate command or list of commands to set movements position

  Args:
      positions (List[Position]): positions to set

  Returns:
      List[ProxyCommand]: 
  """
  # maybe several type of position (JOINT or CARTESIAN) in the list
  # so i use a generator to split them if necessary
  pos_split_by_type_gen = __split_position_list_generator(positions)
  
  # init a pos begin index
  pos_begin = ConstantRegister.POSITION_BEGIN
  
  # init a list for commands
  commands = []

  # iterate in the generator
  for _type, pos in pos_split_by_type_gen:
    # get the positions type and the register type associated
    pos_type = "POSITION_"+_type
    reg_type = RegisterType[pos_type]

    # convert positions in dictionnary
    pos_dict = [p.to_cmd_data() for p in pos]

    # generate the command definition using write_register
    # if number of position exceed the write limit write_register return a list of cmd
    w_cmd_def = __write_register(reg_type,
                               pos_begin,
                               pos_dict)

    for method, path, query, body in w_cmd_def:
    # generate a proxy command for each definitions
      cmd = ProxyCommand(ProxyAction.REQUEST,
                         "set num of movements and movements parameters (speed, cnt and type) in numeric registers.",
                         method,
                         path,
                         query,
                         body)
    
    # and append to the list of commands
      commands.append(cmd)
    
    # increment pos_begin index
    pos_begin+=len(pos)
  
  # return the list of commands
  return commands


def set_movements(movements:List[Movement]) -> List[ProxyCommand]:
  """function to generate a list of commands to set the movements data

  Args:
      movements (List[Movement]): movements to set

  Returns:
      List[ProxyCommand]: list of commands to set movements data
  """
  # init a list for parameters with movements list size (number of points to insert)
  parameters = [len(movements)]
  # init a list for positions
  positions = []

  for movement in movements:
    mov_type = movement.type
    # extend the parameters list with movement.type, movement.speed, movement.cnt
    parameters.extend((MovementTypeCode[mov_type], movement.speed, movement.cnt))
    # add the position in the position list
    positions.append(movement.position)

  set_para_cmds = __set_movements_parameters(parameters)
  set_pos_cmds = __set_movements_positions(positions)

  return set_para_cmds + set_pos_cmds

def set_drilling_parameters(drilling_parameters:List[int]) -> List[ProxyCommand]:
  """function to generate list of commands to set drilling parameters

  Args:
      drilling_parameters (List[int]): list of values to set

  Returns:
      List[ProxyCommand]: list of commands
  """
  # get the command parameter, return the list, i get the first item
  method, path, query, body = __write_register(RegisterType.NUMERIC_INT,
                             ConstantRegister.DRILLING_PARA_BEGIN,
                             drilling_parameters)[0]

  return [ProxyCommand(ProxyAction.REQUEST,
                       "insert drilling parameters in numeric registers",
                       method,
                       path,
                       query,
                       body)] 

def get_drilling_report() -> List[ProxyCommand]:
  """function to generate a list of commands to get drilling report parameters

  Returns:
      List[ProxyCommand]: list of command
  """

  method, path, query = __read_register(RegisterType.NUMERIC_FLOAT,
                                        ConstantRegister.DRILLING_FEEDBACK_BEGIN,
                                        ConstantRegBlockSize.DRILLING_FEEDBACK)[0]
  
  return [ProxyCommand(ProxyAction.REQUEST,
                       "get drilling report",
                       method,
                       path,
                       query)]

def confirm_manipulation(manipulation:Manipulation):
  # get equipment 
  equipment = manipulation.equipment

  # get corresponding ProxyEquipment object (for Proxy Specific information)
  p_equipment:ProxyEquipmentI = ProxyEquipment[equipment.type][equipment.reference]

  # get operation name str
  operation = manipulation.operation

  # get tracking def to check the good manipulation
  tracker_def_para = p_equipment._get_tracker_def(operation)
  # get info about register to track according to equipment type (type:RegisterType, num:int)
  register_type, register_num = p_equipment._get_register_info()
  
  # define the tracker definition
  method, path, query, body, tracker_uid = __track_register(register_type,
                                     register_num,
                                     DEFAULT_TRACKING_INTERVAL,
                                     tracker_def_para)
  
  # define the command
  tracker_command = ProxyCommand(ProxyAction.REQUEST,
                                 f"init tracker to alert for {equipment.reference} {equipment.type} {operation} operation",
                                 method,
                                 path,
                                 query,
                                 body)
  
  # wait command with tracker uid
  wait_cmd = WaitCommand(f"wait end of manipulation {operation} {equipment.reference} {equipment.type}",
                         tracker_uid)

  return [tracker_command, wait_cmd]