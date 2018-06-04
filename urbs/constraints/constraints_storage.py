import math
import pyomo.core as pyomo


# storage

# storage content in timestep [t] == storage content[t-1] * (1-discharge)
# + newly stored energy * input efficiency
# - retrieved energy / output efficiency
def def_storage_state_rule(m, t, sit, sto, com):
    return (m.e_sto_con[t, sit, sto, com] ==
            m.e_sto_con[t-1, sit, sto, com] *
            (1 - m.storage_dict['discharge'][(sit, sto, com)]) +
            m.e_sto_in[t, sit, sto, com] *
            m.storage_dict['eff-in'][(sit, sto, com)] * m.dt -
            m.e_sto_out[t, sit, sto, com] /
            m.storage_dict['eff-out'][(sit, sto, com)] * m.dt)


# storage power == new storage power + existing storage power
def def_storage_power_rule(m, sit, sto, com):
    return (m.cap_sto_p[sit, sto, com] ==
            m.cap_sto_p_new[sit, sto, com] +
            m.storage_dict['inst-cap-p'][(sit, sto, com)])


# storage capacity == new storage capacity + existing storage capacity
def def_storage_capacity_rule(m, sit, sto, com):
    return (m.cap_sto_c[sit, sto, com] ==
            m.cap_sto_c_new[sit, sto, com] +
            m.storage_dict['inst-cap-c'][(sit, sto, com)])


# storage input <= storage power
def res_storage_input_by_power_rule(m, t, sit, sto, com):
    return m.e_sto_in[t, sit, sto, com] <= m.cap_sto_p[sit, sto, com]
def res_storage_input_by_power_rule_const_p(m, t, sit, sto, com):
    return m.e_sto_in[t, sit, sto, com] <= m.storage_dict['inst-cap-p'][(sit, sto, com)]

# storage output <= storage power
def res_storage_output_by_power_rule(m, t, sit, sto, com):
    return m.e_sto_out[t, sit, sto, com] <= m.cap_sto_p[sit, sto, com]
def res_storage_output_by_power_rule_const_p(m, t, sit, sto, com):
    return m.e_sto_out[t, sit, sto, com] <= m.storage_dict['inst-cap-p'][(sit, sto, com)]

# storage content <= storage capacity
def res_storage_state_by_capacity_rule(m, t, sit, sto, com):
    return m.e_sto_con[t, sit, sto, com] <= m.cap_sto_c[sit, sto, com]
def res_storage_state_by_capacity_rule_const_c(m, t, sit, sto, com):
    return m.e_sto_con[t, sit, sto, com] <= m.storage_dict['inst-cap-c'][(sit, sto, com)]

# lower bound <= storage power <= upper bound
def res_storage_power_rule(m, sit, sto, com):
    return (m.storage_dict['cap-lo-p'][(sit, sto, com)],
            m.cap_sto_p[sit, sto, com],
            m.storage_dict['cap-up-p'][(sit, sto, com)])


# lower bound <= storage capacity <= upper bound
def res_storage_capacity_rule(m, sit, sto, com):
    return (m.storage_dict['cap-lo-c'][(sit, sto, com)],
            m.cap_sto_c[sit, sto, com],
            m.storage_dict['cap-up-c'][(sit, sto, com)])


# initialization of storage content in first timestep t[1]
# forced minimun  storage content in final timestep t[len(m.t)]
# content[t=1] == storage capacity * fraction <= content[t=final]
def res_initial_and_final_storage_state_rule(m, t, sit, sto, com):
    if t == m.t[1]:  # first timestep (Pyomo uses 1-based indexing)
        return (m.e_sto_con[t, sit, sto, com] ==
                m.cap_sto_c[sit, sto, com] *
                m.storage_dict['init'][(sit, sto, com)])
    elif t == m.t[len(m.t)]:  # last timestep
        return (m.e_sto_con[t, sit, sto, com] >=
                m.cap_sto_c[sit, sto, com] *
                m.storage_dict['init'][(sit, sto, com)])
    else:
        return pyomo.Constraint.Skip
def res_initial_and_final_storage_state_rule_const_c(m, t, sit, sto, com):
    if t == m.t[1]:  # first timestep (Pyomo uses 1-based indexing)
        return (m.e_sto_con[t, sit, sto, com] ==
                m.storage_dict['cap-up-c'][(sit, sto, com)] *
                m.storage_dict['init'][(sit, sto, com)])
    elif t == m.t[len(m.t)]:  # last timestep
        return (m.e_sto_con[t, sit, sto, com] >=
                m.storage_dict['cap-up-c'][(sit, sto, com)] *
                m.storage_dict['init'][(sit, sto, com)])
    else:
        return pyomo.Constraint.Skip