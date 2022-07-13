from enum import Enum
from typing import Dict
from .definition import Definition, Drilling, Manipulation, Path, Probing
# MODIFGEN from .__init__ import *
import model


ACTION_DEFINITION = {
  'MOVE.TCP.WORK': Path,
  'MOVE.TCP.APPROACH': Path,
  'MOVE.TCP.CLEARANCE': Path,
  'MOVE.STATION.WORK': Path,
  'MOVE.STATION.TOOL': Path,
  'MOVE.STATION.HOME': Path,
  'WORK.DRILL':Drilling,
  'WORK.PROBE': Probing,
  'LOAD.EFFECTOR':Manipulation,
  'UNLOAD.EFFECTOR':Manipulation
}

# action object
class Action:

    """Class used to represent a robot basic action.

    Attributes
    ----------
    id : str
        the action id
    dependencies : List[Action]
        list of dependencies actions
    next : List[Action]
        list of next actions
    definition : object
        definition object. read only
    priority : int
        action priority. read only
    description : str
        action description
    type : str
        action type name. read only

    Methods
    -------
    add_dependences(action)
        add a new action in the dependences list

    add_next(action)
        add a new action in the next list

    """

    def __init__(self, id: str,
                 atype: str,
                 definition: Definition,
                 description: str):

        """Action object initializer

        Args:
            id (str): unique action id
            atype (str): action type
            definition (object): action definition according action type
            description (str): human readable description
        """

        self.__id: str = id
        self.__type: str = atype
        self.__definition: Definition = definition
        self.__description: str = description

    # getter and setters
    @property
    def id(self) -> str:
        """ get the action id

        Returns:
            str: action id
        """
        return self.__id

    @id.setter
    def id(self, nid: str):
        """ function to avoid id redefinition
        """
        raise ValueError("id redefinition forbidden")

    @property
    def type(self) -> str:
        """ get the action type name

        Returns:
            str :  type name
        """
        return self.__type

    @type.setter
    def type(self, ntype: str):
        """function to avoid type redefinition
        """
        raise ValueError("type redefinition forbidden")

    @property
    def definition(self) -> Definition:
        """ get the definition object

        Returns:
            object: action definition
        """
        return self.__definition

    @definition.setter
    def definition(self, ndef: object):
        """ function to avoid definition redefinition
        """
        raise ValueError("definition redefinition forbidden")

    @property
    def description(self) -> str:
        """ get the action description

        Returns:
            str: action description
        """

        return self.__description

    @description.setter
    def description(self, ndesc: str):
        """ set the action description

        Args:
            ndesc (str): new action description
        """
        self.__description = ndesc

    def __repr__(self) -> str:
        """ overload the __repr__ function
        Returns:
            str: human readeable representation of Action
        """
        return self.__description

    @staticmethod
    def parse(serialize_action: Dict) -> 'Action':

        _type = serialize_action['type']
        id = str(serialize_action['_id'])

        try:
          definition_object:Definition = ACTION_DEFINITION[_type]
          definition = definition_object.parse(serialize_action['definition'])
          
          description = serialize_action['description']

          return Action(id, 
                _type,
                definition,
                description)

        except KeyError:
          print(f'Action type {_type} is not a valid action type')

        
    def to_dict(self, drop_id:bool=False):
        d_action = {
            "_id": self.__id,
            "type": self.__type,
            "description": self.__description,
            "definition": self.__definition.to_dict(),
        }
        if drop_id:
            d_action.pop('_id')
        return d_action

    def get_commands(self):
        # get the command fonction accordig the action type (ex:MOVE.TCP.WORK)
        # the command register is defined in the register.py file in the mars module
        cmd_fct = model.COMMAND_REGISTER[self.__type]
        
        #apply the fonction with the definition as parameters to get the commands
        cmd_list = cmd_fct(self.__definition)
        
        # return the commands under dict format
        return [c.to_dict() for c in cmd_list]
    
    
    @classmethod
    def get_from_db(cls, action_id:str):
        action = model.DB_DRIVER.find_by_id(action_id)
        # MODIFGEN action = DB_DRIVER.find_by_id(action_id)
        return cls.parse(action)
