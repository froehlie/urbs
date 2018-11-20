import math
import pyomo.core as pyomo
from .input import *

def add_storage(m):
    
    # generate ordered time step sets
    m.t = pyomo.Set(
        initialize=m.timesteps,
        ordered=True,
        doc='Set of timesteps')

    # storage (e.g. hydrogen, pump storage)
    m.sto = pyomo.Set(
        initialize=m.storage.index.get_level_values('Storage').unique(),
        doc='Set of storage technologies')
    
    # storage tuples
    m.sto_tuples = pyomo.Set(
        within=m.stf*m.sit*m.sto*m.com,
        initialize=m.storage.index,
        doc='Combinations of possible storage by site,'
            'e.g. (2020,Mid,Bat,Elec)')
    
    # tuples for intertemporal operation
    if m.mode['int']:
        m.operational_sto_tuples = pyomo.Set(
            within=m.sit*m.sto*m.com*m.stf*m.stf,
            initialize=[(sit, sto, com, stf, stf_later)
                        for (sit, sto, com, stf, stf_later)
                        in op_sto_tuples(m.sto_tuples, m)],
            doc='Processes that are still operational through stf_later'
                '(and the relevant years following), if built in stf'
                'in stf.')
        m.inst_sto_tuples = pyomo.Set(
            within=m.sit*m.sto*m.com*m.stf,
            initialize=[(sit, sto, com, stf)
                        for (sit, sto, com, stf)
                        in inst_sto_tuples(m)],
            doc='Installed storages that are still operational through stf')

    # storage tuples for storages with fixed initial state
    m.sto_init_bound_tuples = pyomo.Set(
        within=m.stf*m.sit*m.sto*m.com,
        initialize=m.stor_init_bound.index,
    doc='storages with fixed initial state')

    storage tuples for storages with given energy to power ratio
    m.sto_ep_ratio_tuples = pyomo.Set(
        within=m.stf*m.sit*m.sto*m.com,
        initialize=m.sto_ep_ratio.index,
        doc='storages with given energy to power ratio')

    # Variables
    m.cap_sto_c = pyomo.Var(
        m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='Total storage size (MWh)')
    m.cap_sto_c_new = pyomo.Var(
        m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='New storage size (MWh)')
    m.cap_sto_p = pyomo.Var(
        m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='Total storage power (MW)')
    m.cap_sto_p_new = pyomo.Var(
        m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='New  storage power (MW)')
    m.e_sto_in = pyomo.Var(
        m.tm, m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='Power flow into storage (MW) per timestep')
    m.e_sto_out = pyomo.Var(
        m.tm, m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='Power flow out of storage (MW) per timestep')
    m.e_sto_con = pyomo.Var(
        m.t, m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='Energy content of storage (MWh) in timestep')

    # storage rules
    m.def_storage_state = pyomo.Constraint(
        m.tm, m.sto_tuples,
        rule=def_storage_state_rule,
        doc='storage[t] = (1 - sd) * storage[t-1] + in * eff_i - out / eff_o')
    if m.mode['int']:
        m.def_int_storage_power = pyomo.Constraint(
            m.sto_tuples,
            rule=def_int_storage_power_rule,
            doc='storage power = inst-cap + new power')
    else:
        m.def_storage_power = pyomo.Constraint(
            m.sto_tuples,
            rule=def_storage_power_rule,
            doc='storage power = inst-cap + new power')            
    if m.mode['int']:
        m.def_int_storage_capacity = pyomo.Constraint(
            m.sto_tuples,
            rule=def_int_storage_capacity_rule,
            doc='storage capacity = inst-cap + new capacity')
    else:
        m.def_storage_capacity = pyomo.Constraint(
            m.sto_tuples,
            rule=def_storage_capacity_rule,
            doc='storage capacity = inst-cap + new capacity')
    m.res_storage_input_by_power = pyomo.Constraint(
        m.tm, m.sto_tuples,
        rule=res_storage_input_by_power_rule,
        doc='storage input <= storage power')
    m.res_storage_output_by_power = pyomo.Constraint(
        m.tm, m.sto_tuples,
        rule=res_storage_output_by_power_rule,
        doc='storage output <= storage power')
    m.res_storage_state_by_capacity = pyomo.Constraint(
        m.t, m.sto_tuples,
        rule=res_storage_state_by_capacity_rule,
        doc='storage content <= storage capacity')
    m.res_storage_power = pyomo.Constraint(
        m.sto_tuples,
        rule=res_storage_power_rule,
        doc='storage.cap-lo-p <= storage power <= storage.cap-up-p')
    m.res_storage_capacity = pyomo.Constraint(
        m.sto_tuples,
        rule=res_storage_capacity_rule,
        doc='storage.cap-lo-c <= storage capacity <= storage.cap-up-c')
    m.res_initial_and_final_storage_state = pyomo.Constraint(
        m.t, m.sto_init_bound_tuples,
        rule=res_initial_and_final_storage_state_rule,
        doc='storage content initial == and final >= storage.init * capacity')
    m.res_initial_and_final_storage_state_var = pyomo.Constraint(
        m.t, m.sto_tuples - m.sto_init_bound_tuples,
        rule=res_initial_and_final_storage_state_var_rule,
        doc='storage content initial <= final, both variable')
    m.def_storage_energy_power_ratio = pyomo.Constraint(
        m.sto_ep_ratio_tuples,
        rule=def_storage_energy_power_ratio_rule,
        doc='storage capacity = storage power * storage E2P ratio')
    