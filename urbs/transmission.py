import math
import pyomo.core as pyomo
from .input import *

def op_tra_tuples(tra_tuple, m):
    """ s.a. op_pro_tuples
    """
    op_tra = []
    sorted_stf = sorted(list(m.stf))

    for (stf, sit1, sit2, tra, com) in tra_tuple:
        for stf_later in sorted_stf:
            index_helper = sorted_stf.index(stf_later)
            if stf_later == max(sorted_stf):
                if (stf_later +
                   m.global_prop.loc[(max(sorted_stf), 'Weight'), 'value'] - 1
                   <= stf + m.transmission.loc[(stf, sit1, sit2, tra, com),
                                               'depreciation']):
                    op_tra.append((sit1, sit2, tra, com, stf, stf_later))
            elif (sorted_stf[index_helper+1] <=
                  stf + m.transmission.loc[(stf, sit1, sit2, tra, com),
                                           'depreciation'] and
                  stf <= stf_later):
                op_tra.append((sit1, sit2, tra, com, stf, stf_later))
            else:
                pass

    return op_tra


def add_transmission(m):

    # tranmission (e.g. hvac, hvdc, pipeline...)
    m.tra = pyomo.Set(
        initialize=m.transmission.index.get_level_values('Transmission')
                                    .unique(),
        doc='Set of transmission technologies')
    # transmission tuples
    m.tra_tuples = pyomo.Set(
        within=m.stf*m.sit*m.sit*m.tra*m.com,
        initialize=m.transmission.index,
        doc='Combinations of possible transmissions, e.g. '
            '(2020,South,Mid,hvac,Elec)')

    if m.mode['int']:
        m.operational_tra_tuples = pyomo.Set(
            within=m.sit*m.sit*m.tra*m.com*m.stf*m.stf,
            initialize=[(sit, sit_, tra, com, stf, stf_later)
                        for (sit, sit_, tra, com, stf, stf_later)
                        in op_tra_tuples(m.tra_tuples, m)],
            doc='Transmissions that are still operational through stf_later'
                '(and the relevant years following), if built in stf'
                'in stf.')
        m.inst_tra_tuples = pyomo.Set(
            within=m.sit*m.sit*m.tra*m.com*m.stf,
            initialize=[(sit, sit_, tra, com, stf)
                        for (sit, sit_, tra, com, stf)
                        in inst_tra_tuples(m)],
            doc='Installed transmissions that are still operational' 
                'through stf')
    
    # Variables
    m.cap_tra = pyomo.Var(
        m.tra_tuples,
        within=pyomo.NonNegativeReals,
        doc='Total transmission capacity (MW)')
    m.cap_tra_new = pyomo.Var(
        m.tra_tuples,
        within=pyomo.NonNegativeReals,
        doc='New transmission capacity (MW)')
    m.e_tra_in = pyomo.Var(
        m.tm, m.tra_tuples,
        within=pyomo.NonNegativeReals,
        doc='Power flow into transmission line (MW) per timestep')
    m.e_tra_out = pyomo.Var(
        m.tm, m.tra_tuples,
        within=pyomo.NonNegativeReals,
        doc='Power flow out of transmission line (MW) per timestep')

    # transmission
    if m.mode['int']:
        m.def_int_transmission_capacity = pyomo.Constraint(
            m.tra_tuples,
            rule=def_int_transmission_capacity_rule,
            doc='total transmission capacity = inst-cap + new capacity')
    else:
        m.def_transmission_capacity = pyomo.Constraint(
            m.tra_tuples,
            rule=def_transmission_capacity_rule,
            doc='total transmission capacity = inst-cap + new capacity')
    m.def_transmission_output = pyomo.Constraint(
        m.tm, m.tra_tuples,
        rule=def_transmission_output_rule,
        doc='transmission output = transmission input * efficiency')
    m.res_transmission_input_by_capacity = pyomo.Constraint(
        m.tm, m.tra_tuples,
        rule=res_transmission_input_by_capacity_rule,
        doc='transmission input <= total transmission capacity')
    m.res_transmission_capacity = pyomo.Constraint(
        m.tra_tuples,
        rule=res_transmission_capacity_rule,
        doc='transmission.cap-lo <= total transmission capacity <= '
            'transmission.cap-up')
    m.res_transmission_symmetry = pyomo.Constraint(
        m.tra_tuples,
        rule=res_transmission_symmetry_rule,
        doc='total transmission capacity must be symmetric in both directions')

