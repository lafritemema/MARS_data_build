# from db.exceptions import DBDriverException
# from db.functions import build_driver as __build_driver
from typing import Dict
from exceptions import BaseException
from .exceptions import MarsException, MarsExceptionType
from mars.equipment import Equipment as EQUIPMENT
from mars.reference import Reference as REFERENCE
from mars.register import COMMAND_REGISTER



'''def build_environment(mars_config:Dict):
  try:
    # build the driver from conf database definition
    database_config = mars_config['database']
    MARS_DB_DRIVER = __build_driver(database_config)
    return EQUIPMENT, REFERENCE, COMMAND_REGISTER, MARS_DB_DRIVER

  except KeyError as error:
    missing_key = error.args[0]
    raise MarsException(['CONFIG', 'MARS'],
                        MarsExceptionType.CONFIG_ERROR,
                        "the configuration parameter {missing_key} is missing")
  except DBDriverException as error:
    error.add_in_stack(['MARS'])
    raise error
  except BaseException as error:
    error.add_in_stack(['MARS'])
    raise error'''

