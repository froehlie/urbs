import math
import pyomo.core as pyomo
from .modelhelper import search_sell_buy_tuple
				
# process

# process capacity == new capacity + existing capacity
def def_process_capacity_rule(m, sit, pro):
    return (m.cap_pro[sit, pro] ==
                m.cap_pro_new[sit, pro] +
                m.process_dict['inst-cap'][(sit, pro)])
    
# process input power == process throughput * input ratio
def def_process_input_rule(m, tm, sit, pro, co):
    return (m.e_pro_in[tm, sit, pro, co] ==
            m.tau_pro[tm, sit, pro] * m.r_in_dict[(pro, co)])


# process output power = process throughput * output ratio
def def_process_output_rule(m, tm, sit, pro, co):
    return (m.e_pro_out[tm, sit, pro, co] ==
            m.tau_pro[tm, sit, pro] * m.r_out_dict[(pro, co)])


# process input (for supim commodity) = process capacity * timeseries
def def_intermittent_supply_rule(m, tm, sit, pro, coin):                                    ########
    if coin in m.com_supim:
        return (m.e_pro_in[tm, sit, pro, coin] ==
                m.cap_pro[sit, pro] * m.supim_dict[(sit, coin)][tm])
    else:
        return pyomo.Constraint.Skip

def def_intermittent_supply_rule_const_cap(m, tm, sit, pro, coin):                        #########
    if coin in m.com_supim:
        return (m.e_pro_in[tm, sit, pro, coin] ==
                m.process_dict['inst-cap'][(sit, pro)] * m.supim_dict[(sit, coin)][tm])
    else:
        return pyomo.Constraint.Skip

# process throughput <= process capacity                                        ##########
def res_process_throughput_by_capacity_rule(m, tm, sit, pro):                   
    return (m.tau_pro[tm, sit, pro] <= m.cap_pro[sit, pro])

def res_process_throughput_by_capacity_rule_const_cap(m, tm, sit, pro):         
    return (m.tau_pro[tm, sit, pro] <= m.process_dict['inst-cap'][(sit, pro)])

def res_process_maxgrad_lower_rule(m, t, sit, pro):                             ##########
    return (m.tau_pro[t-1, sit, pro] -
            m.cap_pro[sit, pro] * m.process_dict['max-grad'][(sit, pro)] *
            m.dt <= m.tau_pro[t, sit, pro])

def res_process_maxgrad_lower_rule_const_cap(m, t, sit, pro):                    
    return (m.tau_pro[t-1, sit, pro] -
            m.process_dict['inst-cap'][(sit, pro)] * 
            m.process_dict['max-grad'][(sit, pro)] *
            m.dt <= m.tau_pro[t, sit, pro])
            
def res_process_maxgrad_upper_rule(m, t, sit, pro):                             ########### 
    return (m.tau_pro[t-1, sit, pro] +
            m.cap_pro[sit, pro] * m.process_dict['max-grad'][(sit, pro)] *
            m.dt >= m.tau_pro[t, sit, pro])

def res_process_maxgrad_upper_rule_const_cap(m, t, sit, pro):                              
    return (m.tau_pro[t-1, sit, pro] +
            m.process_dict['inst-cap'][(sit, pro)] * 
            m.process_dict['max-grad'][(sit, pro)] *
            m.dt >= m.tau_pro[t, sit, pro])        

# lower bound <= process capacity <= upper bound                                ##############
def res_process_capacity_rule(m, sit, pro):
    return (m.process_dict['cap-lo'][sit, pro],
            m.cap_pro[sit, pro],
            m.process_dict['cap-up'][sit, pro])

def res_throughput_by_capacity_min_rule(m, tm, sit, pro):                       ###########
    return (m.tau_pro[tm, sit, pro] >=
            m.cap_pro[sit, pro] *
            m.process_dict['min-fraction'][(sit, pro)])

def res_throughput_by_capacity_min_rule_const_cap(m, tm, sit, pro):                       ###########
    return (m.tau_pro[tm, sit, pro] >=
            m.process_dict['inst-cap'][(sit, pro)] * 
            m.process_dict['min-fraction'][(sit, pro)])

def def_partial_process_input_rule(m, tm, sit, pro, coin):                      ##########
    R = m.r_in_dict[(pro, coin)]  # input ratio at maximum operation point
    r = m.r_in_min_fraction[pro, coin]  # input ratio at lowest
    # operation point
    min_fraction = m.process_dict['min-fraction'][(sit, pro)]

    online_factor = min_fraction * (r - R) / (1 - min_fraction)
    throughput_factor = (R - min_fraction * r) / (1 - min_fraction)

    return (m.e_pro_in[tm, sit, pro, coin] ==
            m.cap_pro[sit, pro] * online_factor +
            m.tau_pro[tm, sit, pro] * throughput_factor)

def def_partial_process_input_rule_const_cap(m, tm, sit, pro, coin):                    
    R = m.r_in_dict[(pro, coin)]  # input ratio at maximum operation point
    r = m.r_in_min_fraction[pro, coin]  # input ratio at lowest
    # operation point
    min_fraction = m.process_dict['min-fraction'][(sit, pro)]

    online_factor = min_fraction * (r - R) / (1 - min_fraction)
    throughput_factor = (R - min_fraction * r) / (1 - min_fraction)

    return (m.e_pro_in[tm, sit, pro, coin] ==
            m.process_dict['inst-cap'][(sit, pro)] * online_factor +
            m.tau_pro[tm, sit, pro] * throughput_factor)

def def_partial_process_output_rule(m, tm, sit, pro, coo):                      #############
    R = m.r_out.loc[pro, coo]  # input ratio at maximum operation point
    r = m.r_out_min_fraction[pro, coo]  # input ratio at lowest operation point
    min_fraction = m.process_dict['min-fraction'][(sit, pro)]

    online_factor = min_fraction * (r - R) / (1 - min_fraction)
    throughput_factor = (R - min_fraction * r) / (1 - min_fraction)

    return (m.e_pro_out[tm, sit, pro, coo] ==
            m.cap_pro[sit, pro] * online_factor +
            m.tau_pro[tm, sit, pro] * throughput_factor)

def def_partial_process_output_rule_const_cap(m, tm, sit, pro, coo):                     #############
    R = m.r_out.loc[pro, coo]  # input ratio at maximum operation point
    r = m.r_out_min_fraction[pro, coo]  # input ratio at lowest operation point
    min_fraction = m.process_dict['min-fraction'][(sit, pro)]

    online_factor = min_fraction * (r - R) / (1 - min_fraction)
    throughput_factor = (R - min_fraction * r) / (1 - min_fraction)

    return (m.e_pro_out[tm, sit, pro, coo] ==
            m.process_dict['inst-cap'][(sit, pro)] * online_factor +
            m.tau_pro[tm, sit, pro] * throughput_factor)

# used process area <= maximal process area
def res_area_rule(m, sit):                                                      #############
    if m.site.loc[sit]['area'] >= 0 and sum(
                         m.process.loc[(s, p), 'area-per-cap']
                         for (s, p) in m.pro_area_tuples
                         if s == sit) > 0:
        total_area = sum(m.cap_pro[s, p] *
                        m.process.loc[(s, p), 'area-per-cap']
                        for (s, p) in m.pro_area_tuples_expansion
                        if s == sit) + \
                     sum(m.process_dict['inst-cap'][(s, p)] *
                        m.process.loc[(s, p), 'area-per-cap']
                        for (s, p) in (m.pro_area_tuples-m.pro_area_tuples_expansion)
                        if s == sit)
        return total_area <= m.site.loc[sit]['area']
    else:
        # Skip constraint, if area is not numeric
        return pyomo.Constraint.Skip


# power connection capacity: Sell == Buy
def res_sell_buy_symmetry_rule(m, sit_in, pro_in, coin):                        ##############
    # constraint only for sell and buy processes
    # and the processes must be in the same site
    if coin in m.com_buy:
        sell_pro = search_sell_buy_tuple(m, sit_in, pro_in, coin)
        if sell_pro is None:
            return pyomo.Constraint.Skip
        else:
            return (m.cap_pro[sit_in, pro_in] == m.cap_pro[sit_in, sell_pro])
    else:
        return pyomo.Constraint.Skip
def res_sell_buy_symmetry_rule_const_cap(m, sit_in, pro_in, coin):                        ##############
    # constraint only for sell and buy processes
    # and the processes must be in the same site
    if coin in m.com_buy:
        sell_pro = search_sell_buy_tuple(m, sit_in, pro_in, coin)
        if sell_pro is None:
            return pyomo.Constraint.Skip
        else:
            return (m.process_dict['inst-cap'][(sit_in, pro_in)] == m.process_dict['inst-cap'][(sit_in, sell_pro)])
    else:
        return pyomo.Constraint.Skip