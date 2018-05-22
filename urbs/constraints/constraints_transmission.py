import math
import pyomo.core as pyomo


# transmission

# transmission capacity == new capacity + existing capacity									
def def_transmission_capacity_rule(m, sin, sout, tra, com):
    """return (m.cap_tra[sin, sout, tra, com] ==
            m.cap_tra_new[sin, sout, tra, com] +
            m.transmission_dict['inst-cap'][(sin, sout, tra, com)])"""
    if m.transmission_dict['inst-cap'][(sin, sout, tra, com)] < m.transmission_dict['cap-up'][(sin, sout, tra, com)]:
        return (m.cap_tra[sin, sout, tra, com] ==
                m.cap_tra_new[sin, sout, tra, com] +
                m.transmission_dict['inst-cap'][(sin, sout, tra, com)])
    else:
        return (m.cap_tra[sin, sout, tra, com] == m.transmission_dict['inst-cap'][(sin, sout, tra, com)])

# transmission output == transmission input * efficiency
def def_transmission_output_rule(m, tm, sin, sout, tra, com):
    return (m.e_tra_out[tm, sin, sout, tra, com] ==
            m.e_tra_in[tm, sin, sout, tra, com] *
            m.transmission_dict['eff'][(sin, sout, tra, com)])


# transmission input <= transmission capacity
def res_transmission_input_by_capacity_rule(m, tm, sin, sout, tra, com):
    return (m.e_tra_in[tm, sin, sout, tra, com] <=
            m.cap_tra[sin, sout, tra, com])


# lower bound <= transmission capacity <= upper bound
def res_transmission_capacity_rule(m, sin, sout, tra, com):
    return (m.transmission_dict['cap-lo'][(sin, sout, tra, com)],
            m.cap_tra[sin, sout, tra, com],
            m.transmission_dict['cap-up'][(sin, sout, tra, com)])


# transmission capacity from A to B == transmission capacity from B to A
def res_transmission_symmetry_rule(m, sin, sout, tra, com):
    return m.cap_tra[sin, sout, tra, com] == m.cap_tra[sout, sin, tra, com]
