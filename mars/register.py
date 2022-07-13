
from typing import List
from model.definition import Drilling, Path, Manipulation, Probing
from model.command import Command
from mars import proxy, hmi

def __build_traj_gen_sequence(path:Path) -> List[Command]:
  """function to generate list of commands to perform a trajectory

  Args:
      path (Path): path object defining the trajectory

  Returns:
      List[Command]: list of commands
  """

  # get cmd to update ut and uf
  set_utuf_cmds = proxy.set_utuf(path.user_tool, path.user_frame)
  # get cmd to set movements data
  set_movements_cmds = proxy.set_movements(path.movements)

  # get cmd to run program and wait for end
  run_program_cmds = proxy.run_program(proxy.Program.TRAJ_GEN)

  # return the list of commands
  return set_utuf_cmds + set_movements_cmds + run_program_cmds
  

def __build_probing_sequence(probe:Probing) -> List[Command]:
  """function to generate list of commands to perform a probing

  Args:
      probe (Probing): probing object defining the probing

  Returns:
      List[Command]: list of commands
  """
  # get cmd to update ut and uf
  set_utuf_cmds = proxy.set_utuf(probe.user_tool, probe.user_frame)
  # get cmd to set movements data
  set_movement_cmds = proxy.set_movements([probe.movement])
  # get cmd to run program and wait for end
  run_program_cmds = proxy.run_program(proxy.Program.PROBING)

  return set_utuf_cmds + set_movement_cmds + run_program_cmds

def __build_drilling_sequence(drilling:Drilling):
  # TODO : add additional parameters if needed

  # get the drilling parameters
  drilling_parameters = (drilling.speed, drilling.feed, int(drilling.peak))
  # get cmd to set parameters
  set_para_cmds = proxy.set_drilling_parameters(drilling_parameters)
  # get cmd to run drilling sequence

  run_program_cmds = proxy.run_program(proxy.Program.DRILLING)

  # TODO : add cmd to get drilling report from effector
  # drilling_report_cmd = proxy.get_drilling_report()

  return set_para_cmds + run_program_cmds # + drilling_report_cmd

def __build_manipulation_sequence(manipulation:Manipulation):
  # get command for hmi manipulation message
  hmi_msg_command = hmi.send_manipulation_message(manipulation)
  # get command for proxy tracking to confirm manipulation
  proxy_tracker_cmd = proxy.confirm_manipulation(manipulation)
  
  return hmi_msg_command + proxy_tracker_cmd


COMMAND_REGISTER = {
  'MOVE.TCP.WORK' : __build_traj_gen_sequence,
  'MOVE.TCP.APPROACH' : __build_traj_gen_sequence,
  'MOVE.TCP.CLEARANCE' : __build_traj_gen_sequence,
  'MOVE.STATION.WORK': __build_traj_gen_sequence,
  'MOVE.STATION.HOME' : __build_traj_gen_sequence,
  'MOVE.STATION.TOOL' : __build_traj_gen_sequence,
  'WORK.DRILL' : __build_drilling_sequence, 
  'WORK.PROBE' : __build_probing_sequence,
  'LOAD.EFFECTOR' : __build_manipulation_sequence,
  'UNLOAD.EFFECTOR' : __build_manipulation_sequence,
}