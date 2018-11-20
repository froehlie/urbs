import math
import pyomo.core as pyomo
from .input import *

def add_time_variable_efficiency(m):
    # process tuples for time variable efficiency
    m.pro_timevar_output_tuples = pyomo.Set(
        within=m.stf*m.sit*m.pro*m.com,
        initialize=[(stf, site, process, commodity)
                    for stf in m.eff_factor.index.levels[0]
                    for (site, process) in m.eff_factor.columns
                    for (st, pro, commodity) in m.r_out.index
                    if process == pro and st == stf and commodity not in
                    m.com_env],
    doc='Outputs of processes with time dependent efficiency')