import math
import pyomo.core as pyomo
from .input import *
from .model import *

def add_buy_sell_price(m):   
    
    m.com_sell = pyomo.Set(
        within=m.com,
        initialize=commodity_subset(m.com_tuples, 'Sell'),
        doc='Commodities that can be sold')
    m.com_buy = pyomo.Set(
        within=m.com,
        initialize=commodity_subset(m.com_tuples, 'Buy'),
        doc='Commodities that can be purchased')

    # Variables
    m.e_co_sell = pyomo.Var(
        m.tm, m.com_tuples,
        within=pyomo.NonNegativeReals,
        doc='Use of sell commodity source (MW) per timestep')
    m.e_co_buy = pyomo.Var(
        m.tm, m.com_tuples,
        within=pyomo.NonNegativeReals,
        doc='Use of buy commodity source (MW) per timestep')

    # Rules
    m.res_sell_step = pyomo.Constraint(
        m.tm, m.com_tuples,
        rule=res_sell_step_rule,
        doc='sell commodity output per step <= commodity.maxperstep')
    m.res_sell_total = pyomo.Constraint(
        m.com_tuples,
        rule=res_sell_total_rule,
        doc='total sell commodity output <= commodity.max')
    m.res_buy_step = pyomo.Constraint(
        m.tm, m.com_tuples,
        rule=res_buy_step_rule,
        doc='buy commodity output per step <= commodity.maxperstep')
    m.res_buy_total = pyomo.Constraint(
        m.com_tuples,
        rule=res_buy_total_rule,
        doc='total buy commodity output <= commodity.max')

    m.res_sell_buy_symmetry = pyomo.Constraint(
        m.pro_input_tuples,
        rule=res_sell_buy_symmetry_rule,
        doc='power connection capacity must be symmetric in both directions')