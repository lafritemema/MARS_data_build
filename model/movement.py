from enum import Enum
from typing import Dict, List, Tuple
import numpy as np
import abc

class MovementType(Enum):
    """Path type enumeration

    Args:
        Enum (char): fanuc path code
    """

    CIRCULAR = 'C'
    LINEAR = 'L'
    JOINT = 'J'

class PositionType(Enum):

    """tcp position representation type enumeration

    Args:
        Enum (str): fanuc tcp position representation type
    """
    JOINT = 'jnt'
    CARTESIAN = 'crt'

class WristConfig(Enum):
    """wrist configuration enumerator

    Args:
        Enum (char): fanuc wrist config code
    """
    FLIP = 'F'
    NOFLIP = 'N'

class ForeArmConfig(Enum):
    """ForeArm configuration enumerator

    Args:
        Enum (char): fanuc forearm config code
    """
    UP = 'U'
    DOWN = 'D'


class ArmConfig(Enum):
    """Arm configuration enumerator

    Args:
        Enum (char): fanuc arm config code
    """
    TOWARD = 'T'
    BACKWARD = 'D'


class Configuration:
    """Class used to represent the arm configuration
    """
    def __init__(self, wrist: WristConfig,
                 forearm: ForeArmConfig,
                 arm: ArmConfig,
                 j4: int = 0,
                 j5: int = 0,
                 j6: int = 0) -> 'Configuration':
        """Configuration object initializer

        Args:
            wrist (WristConfig): wrist configuration enumeration (FLIP|NOFLIP)
            forearm (ForeArmConfig): forearm configuration
                enumeration (UP|DOWN)
            arm (ArmConfig): arm configuration
                enumeration (TOWARD|BACKWARD)
            j4 (int, optional) : max rotation code for j4, default 0
            j5 (int, optional) : max rotation code for j5, default 0
            j6 (int, optional) : max rotation code for j6, default 0
        """
        self.__wrist: WristConfig = wrist
        self.__forearm: ForeArmConfig = forearm
        self.__arm: ArmConfig = arm
        self.__j4: int = 0
        self.__j5: int = 0
        self.__j6: int = 0

    @staticmethod
    def parse(serialize_config: Dict) -> 'Configuration':
        wrist = WristConfig[serialize_config['wrist']]
        forearm = ForeArmConfig[serialize_config['forearm']]
        arm = ArmConfig[serialize_config['arm']]
        j4 = serialize_config['j4']
        j5 = serialize_config['j5']
        j6 = serialize_config['j6']

        return Configuration(wrist, forearm, arm, j4, j5, j6)

    def to_dict(self):
        return {
            "wrist": self.__wrist.name,
            "forearm": self.__forearm.name,
            "arm": self.__arm.name,
            "j4": self.__j4,
            "j5": self.__j5,
            "j6": self.__j6
        }

    def to_cmd_data(self):
        return {
            "wrist": self.__wrist.name,
            "forearm": self.__forearm.name,
            "arm": self.__arm.name,
            "j4": self.__j4,
            "j5": self.__j5,
            "j6": self.__j6
        }

class Position:

    """Class used to represent a TCP position"""

    _VECTOR_KEYS=None
    __metaclass__ = abc.ABCMeta

    def __init__(self,
                 pvector: np.array,
                 ptype: PositionType,
                 e1: int,
                 config: Configuration = None,
                 ut: int = 0,
                 uf: int = 0) -> 'Position':
        """
        Position object initializer

        Args:
            pvector (np.array): tcp position vector
            ptype (PositionType): position type enumeration
            e1 (int): 7 axis position
            config (Configuration): Arm configuration
            ut: always to 0
            uf: always to 0
        """

        self._vector: np.array = pvector
        self.__type: PositionType = ptype
        self.__config: Configuration = config
        self.__e1: int = e1
        self.__ut = ut
        self.__uf = uf

    @property
    def vector(self):
        return self._vector

    @vector.setter
    def vector(self, nvector):
        self._vector = nvector

    @property
    def e1(self):
        return self.__e1

    @e1.setter
    def e1(self, ne1):
        self.__e1 = ne1

    @property
    def type(self):
        return self.__type.name

    @staticmethod
    def parse(serialize_position) -> 'Position':
        type = serialize_position['type']
        if type == 'CARTESIAN':
            return PositionCrt.parse(serialize_position)
        elif type == 'JOINT':
            return PositionJoint.parse(serialize_position)
        else:
            raise Exception('position parsing default')

    def to_dict(self) -> Dict:
        """ get a dictionnary describing the cartesian position object

        Returns:
            Dict: dictionnary with Position object informations
        """

        return {
            "ut": self.__ut,
            "uf": self.__uf,
            "type": self.__type.name,
            "e1": self.__e1,
            "vector": self.__vector_to_dict(),
            "config": self.__config.to_dict() if self.__config else None
        }

    def to_cmd_data(self):
        return {
            "ut": self.__ut,
            "uf": self.__uf,
            "type": self.__type.value,
            "e1": self.__e1,
            "vector": self.__vector_to_dict(),
            "config": self.__config.to_cmd_data() if self.__config else None
        }

    def __vector_to_dict(self):
        vector_list = []
        for index, key in enumerate(self.__class__._VECTOR_KEYS):
            vector_list.append((key, round(float(self._vector[index]), 3)))

        return dict(vector_list)


class PositionCrt(Position):

    _VECTOR_KEYS = ['x', 'y', 'z', 'w', 'p', 'r']

    """ Class used to represent a Position in cartesian representation
    Inherit from Position Class"""

    def __init__(self, pvector: np.array,
                 e1: int,
                 config: Configuration) -> 'PositionCrt':
        """PositionCrt object initializer

        Args:
            pvector (np.array): tcp position vector
            e1 (int): 7 axis position
            config (Configuration): Arm configuration
        """
        # initialize Position Object with CARTESIAN position type

        super(PositionCrt, self)\
            .__init__(pvector, PositionType.CARTESIAN,
                      e1, config)

    @classmethod
    def parse(cls, serialize_crtpos: Dict) -> 'PositionCrt':
        e1 = serialize_crtpos['e1']
        config = Configuration.parse(serialize_crtpos['config'])

        svector = serialize_crtpos['vector']
        vector_array = [svector[key] for key in cls._VECTOR_KEYS]
        vector = np.array(vector_array)

        return cls(vector, e1, config)


class PositionJoint(Position):

    _VECTOR_KEYS = ['j1', 'j2', 'j3', 'j4', 'j5', 'j6']

    """ Class used to represent a Position in joint representation
    Inherit from Position Class"""

    def __init__(self, pvector: np.array, e1: int):
        """[summary]

        Args:
            pvector (np.array): tcp position vector
            e1 (int): 7 axis position
        """

        # initialize Position Object with JOINT position type.
        # no Configuration need for JOINT position type

        super(PositionJoint, self)\
            .__init__(pvector, PositionType.JOINT, e1)

    @classmethod
    def parse(cls, serialize_jntpos: Dict) -> 'PositionJoint':
        e1 = serialize_jntpos['e1']

        svector = serialize_jntpos['vector']
        vector_array = [svector[key] for key in cls._VECTOR_KEYS]
        vector = np.array(vector_array)

        return cls(vector, e1)


class Movement:

    """ Class used to represent a movement passing point
    """
    def __init__(self, cnt: int,
                 speed: int,
                 _type: MovementType,
                 position: Position) -> 'Movement':
        """Point object initializer

        Args:
            cnt (int): passing accuracy from the point
            speed (int): movement speed
            path (Path): trajectory shape
            position (Position): tcp position
        """
        self.__cnt: int = cnt
        self.__speed: int = speed
        self.__position: Position = position
        self.__type: MovementType = _type

    @property
    def position(self):
        return self.__position

    @property
    def position_type(self):
        return self.__position.type

    @property
    def cnt(self)-> int:
        return self.__cnt
    
    @property
    def speed(self)-> int:
        return self.__speed
    
    @property
    def type(self)-> int:
        return self.__type.name

    @staticmethod
    def parse(serialize_point: Dict) -> 'Movement':
        cnt = serialize_point['cnt']
        path = MovementType[serialize_point['type']]
        speed = serialize_point['speed']
        position = Position.parse(serialize_point['position'])

        return Movement(cnt, speed, path, position)

    def to_dict(self):
        return {
            "cnt": self.__cnt,
            "speed": self.__speed,
            "position": self.__position.to_dict(),
            "type": self.__type.name
        }

    def to_cmd_data(self) -> Dict:
        return {
            "parameters": {
                    "cnt": self.__cnt,
                    "speed": self.__speed,
                    "type": self.__type
                },
            "position": self.__position.to_cmd_data()
            }
    '''
    def get_sequence(self) -> Dict:

        path = proxyapi.PathCode[self.__path.name].value

        return {
            "settings": [path, self.__speed, self.__cnt],
            "position": self.__position.get_sequence()
        }'''