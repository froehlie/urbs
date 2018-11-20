import math
import pyomo.core as pyomo
from .input import *

def add_dsm(m):

    # modelled Demand Side Management time steps (downshift):
    # downshift effective in tt to compensate for upshift in t
    m.tt = pyomo.Set(
        within=m.t,
        initialize=m.timesteps[1:],
        ordered=True,
        doc='Set of additional DSM time steps')

    # DSM Tuples
    m.dsm_site_tuples = pyomo.Set(
        within=m.stf*m.sit*m.com,
        initialize=m.dsm.index,
        doc='Combinations of possible dsm by site, e.g. (2020, Mid, Elec)')
    m.dsm_down_tuples = pyomo.Set(
        within=m.tm*m.tm*m.stf*m.sit*m.com,
        initialize=[(t, tt, stf, site, commodity)
                    for (t, tt, stf, site, commodity)
                    in dsm_down_time_tuples(m.timesteps[1:],
                                            m.dsm_site_tuples,
                                            m)],
        doc='Combinations of possible dsm_down combinations, e.g. '
            '(5001,5003,2020,Mid,Elec)')

    # Variables
    m.dsm_up = pyomo.Var(
        m.tm, m.dsm_site_tuples,
        within=pyomo.NonNegativeReals,
        doc='DSM upshift')
    m.dsm_down = pyomo.Var(
        m.dsm_down_tuples,
        within=pyomo.NonNegativeReals,
        doc='DSM downshift')

    # DSM rules
    m.def_dsm_variables = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=def_dsm_variables_rule,
        doc='DSMup * efficiency factor n == DSMdo (summed)')

    m.res_dsm_upward = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=res_dsm_upward_rule,
        doc='DSMup <= Cup (threshold capacity of DSMup)')

    m.res_dsm_downward = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=res_dsm_downward_rule,
        doc='DSMdo (summed) <= Cdo (threshold capacity of DSMdo)')

    m.res_dsm_maximum = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=res_dsm_maximum_rule,
        doc='DSMup + DSMdo (summed) <= max(Cup,Cdo)')

    m.res_dsm_recovery = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=res_dsm_recovery_rule,
        doc='DSMup(t, t + recovery time R) <= Cup * delay time L')
