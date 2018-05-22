import math
import pyomo.core as pyomo
from .modelhelper import *

# commodity

# vertex equation: calculate balance for given commodity and site;
# contains implicit constraints for process activity, import/export and
# storage activity (calculated by function commodity_balance);
# contains implicit constraint for stock commodity source term
def res_vertex_rule(m, tm, sit, com, com_type):
    # environmental or supim commodities don't have this constraint (yet)
    if com in m.com_env:
        return pyomo.Constraint.Skip
    if com in m.com_supim:
        return pyomo.Constraint.Skip

    # helper function commodity_balance calculates balance from input to
    # and output from processes, storage and transmission.
    # if power_surplus > 0: production/storage/imports create net positive
    #                       amount of commodity com
    # if power_surplus < 0: production/storage/exports consume a net
    #                       amount of the commodity com
    power_surplus = - commodity_balance(m, tm, sit, com)

    # if com is a stock commodity, the commodity source term e_co_stock
    # can supply a possibly negative power_surplus
    if com in m.com_stock:
        power_surplus += m.e_co_stock[tm, sit, com, com_type]

    # if com is a sell commodity, the commodity source term e_co_sell
    # can supply a possibly positive power_surplus
    if com in m.com_sell:
        power_surplus -= m.e_co_sell[tm, sit, com, com_type]

    # if com is a buy commodity, the commodity source term e_co_buy
    # can supply a possibly negative power_surplus
    if com in m.com_buy:
        power_surplus += m.e_co_buy[tm, sit, com, com_type]

    # if com is a demand commodity, the power_surplus is reduced by the
    # demand value; no scaling by m.dt or m.weight is needed here, as this
    # constraint is about power (MW), not energy (MWh)
    if com in m.com_demand:
        try:
            power_surplus -= m.demand_dict[(sit, com)][tm]
        except KeyError:
            pass
    # if sit com is a dsm tuple, the power surplus is decreased by the
    # upshifted demand and increased by the downshifted demand.
    if (sit, com) in m.dsm_site_tuples:
        power_surplus -= m.dsm_up[tm, sit, com]
        power_surplus += sum(m.dsm_down[t, tm, sit, com]
                             for t in dsm_time_tuples(
                                 tm, m.timesteps[1:],
                                 m.dsm_dict['delay'][(sit, com)]))
    return power_surplus == 0

# demand side management (DSM) constraints


# DSMup == DSMdo * efficiency factor n
def def_dsm_variables_rule(m, tm, sit, com):
    dsm_down_sum = 0
    for tt in dsm_time_tuples(tm,
                              m.timesteps[1:],
                              m.dsm_dict['delay'][(sit, com)]):
        dsm_down_sum += m.dsm_down[tm, tt, sit, com]
    return dsm_down_sum == (m.dsm_up[tm, sit, com] *
                            m.dsm_dict['eff'][(sit, com)])


# DSMup <= Cup (threshold capacity of DSMup)
def res_dsm_upward_rule(m, tm, sit, com):
    return m.dsm_up[tm, sit, com] <= int(m.dsm_dict['cap-max-up'][(sit, com)])


# DSMdo <= Cdo (threshold capacity of DSMdo)
def res_dsm_downward_rule(m, tm, sit, com):
    dsm_down_sum = 0
    for t in dsm_time_tuples(tm,
                             m.timesteps[1:],
                             m.dsm_dict['delay'][(sit, com)]):
        dsm_down_sum += m.dsm_down[t, tm, sit, com]
    return dsm_down_sum <= m.dsm_dict['cap-max-do'][(sit, com)]


# DSMup + DSMdo <= max(Cup,Cdo)
def res_dsm_maximum_rule(m, tm, sit, com):
    dsm_down_sum = 0
    for t in dsm_time_tuples(tm,
                             m.timesteps[1:],
                             m.dsm_dict['delay'][(sit, com)]):
        dsm_down_sum += m.dsm_down[t, tm, sit, com]

    max_dsm_limit = max(m.dsm_dict['cap-max-up'][(sit, com)],
                        m.dsm_dict['cap-max-do'][(sit, com)])
    return m.dsm_up[tm, sit, com] + dsm_down_sum <= max_dsm_limit


# DSMup(t, t + recovery time R) <= Cup * delay time L
def res_dsm_recovery_rule(m, tm, sit, com):
    dsm_up_sum = 0
    for t in dsm_recovery(tm,
                          m.timesteps[1:],
                          m.dsm_dict['recov'][(sit, com)]):
        dsm_up_sum += m.dsm_up[t, sit, com]
    return dsm_up_sum <= (m.dsm_dict['cap-max-up'][(sit, com)] *
                          m.dsm_dict['delay'][(sit, com)])


# stock commodity purchase == commodity consumption, according to
# commodity_balance of current (time step, site, commodity);
# limit stock commodity use per time step
def res_stock_step_rule(m, tm, sit, com, com_type):
    if com not in m.com_stock:
        return pyomo.Constraint.Skip
    else:
        return (m.e_co_stock[tm, sit, com, com_type] <=
                m.commodity_dict['maxperstep'][(sit, com, com_type)])


# limit stock commodity use in total (scaled to annual consumption, thanks
# to m.weight)
def res_stock_total_rule(m, sit, com, com_type):
    if com not in m.com_stock:
        return pyomo.Constraint.Skip
    else:
        # calculate total consumption of commodity com
        total_consumption = 0
        for tm in m.tm:
            total_consumption += (
                m.e_co_stock[tm, sit, com, com_type] * m.dt)
        total_consumption *= m.weight
        return (total_consumption <=
                m.commodity_dict['max'][(sit, com, com_type)])


# limit sell commodity use per time step
def res_sell_step_rule(m, tm, sit, com, com_type):
    if com not in m.com_sell:
        return pyomo.Constraint.Skip
    else:
        return (m.e_co_sell[tm, sit, com, com_type] <=
                m.commodity_dict['maxperstep'][(sit, com, com_type)])


# limit sell commodity use in total (scaled to annual consumption, thanks
# to m.weight)
def res_sell_total_rule(m, sit, com, com_type):
    if com not in m.com_sell:
        return pyomo.Constraint.Skip
    else:
        # calculate total sale of commodity com
        total_consumption = 0
        for tm in m.tm:
            total_consumption += (
                m.e_co_sell[tm, sit, com, com_type] * m.dt)
        total_consumption *= m.weight
        return (total_consumption <=
                m.commodity_dict['max'][(sit, com, com_type)])


# limit buy commodity use per time step
def res_buy_step_rule(m, tm, sit, com, com_type):
    if com not in m.com_buy:
        return pyomo.Constraint.Skip
    else:
        return (m.e_co_buy[tm, sit, com, com_type] <=
                m.commodity_dict['maxperstep'][(sit, com, com_type)])


# limit buy commodity use in total (scaled to annual consumption, thanks
# to m.weight)
def res_buy_total_rule(m, sit, com, com_type):
    if com not in m.com_buy:
        return pyomo.Constraint.Skip
    else:
        # calculate total sale of commodity com
        total_consumption = 0
        for tm in m.tm:
            total_consumption += (
                m.e_co_buy[tm, sit, com, com_type] * m.dt)
        total_consumption *= m.weight
        return (total_consumption <=
                m.commodity_dict['max'][(sit, com, com_type)])


# environmental commodity creation == - commodity_balance of that commodity
# used for modelling emissions (e.g. CO2) or other end-of-pipe results of
# any process activity;
# limit environmental commodity output per time step
def res_env_step_rule(m, tm, sit, com, com_type):
    if com not in m.com_env:
        return pyomo.Constraint.Skip
    else:
        environmental_output = - commodity_balance(m, tm, sit, com)
        return (environmental_output <=
                m.commodity_dict['maxperstep'][(sit, com, com_type)])


# limit environmental commodity output in total (scaled to annual
# emissions, thanks to m.weight)
def res_env_total_rule(m, sit, com, com_type):
    if com not in m.com_env:
        return pyomo.Constraint.Skip
    else:
        # calculate total creation of environmental commodity com
        env_output_sum = 0
        for tm in m.tm:
            env_output_sum += (- commodity_balance(m, tm, sit, com) * m.dt)
        env_output_sum *= m.weight
        return (env_output_sum <=
                m.commodity_dict['max'][(sit, com, com_type)])

				
