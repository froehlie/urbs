import math
import pyomo.core as pyomo
from datetime import datetime
from .modelhelper import *
from .input import *
from .commodity import *
from .process import *
from .transmission import *
from .storage import *


def create_model(data, timesteps=None, dt=1, dual=False):
    """Create a pyomo ConcreteModel urbs object from given input data.

    Args:
        data: a dict of 6 DataFrames with the keys 'commodity', 'process',
            'transmission', 'storage', 'demand' and 'supim'.
        timesteps: optional list of timesteps, default: demand timeseries
        dt: timestep duration in hours (default: 1)
        dual: set True to add dual variables to model (slower); default: False

    Returns:
        a pyomo ConcreteModel object
    """

    # Optional
    if not timesteps:
        timesteps = data['demand'].index.tolist()
    m = pyomo_model_prep(data, timesteps)  # preparing pyomo model
    m.name = 'urbs'
    m.created = datetime.now().strftime('%Y%m%dT%H%M')
    m._data = data

    # Sets
    # ====
    # Syntax: m.{name} = Set({domain}, initialize={values})
    # where name: set name
    #       domain: set domain for tuple sets, a cartesian set product
    #       values: set values, a list or array of element tuples

    #count sites 
    site_count = m.site.size

    # generate ordered time step sets
    m.t = pyomo.Set(
        initialize=m.timesteps,
        ordered=True,
        doc='Set of timesteps')

    # modelled (i.e. excluding init time step for storage) time steps
    m.tm = pyomo.Set(
        within=m.t,
        initialize=m.timesteps[1:],
        ordered=True,
        doc='Set of modelled timesteps')

    # modelled Demand Side Management time steps (downshift):
    # downshift effective in tt to compensate for upshift in t
    m.tt = pyomo.Set(
        within=m.t,
        initialize=m.timesteps[1:],
        ordered=True,
        doc='Set of additional DSM time steps')

    # site (e.g. north, middle, south...)
    m.sit = pyomo.Set(
        initialize=m.commodity.index.get_level_values('Site').unique(),
        doc='Set of sites')

    # commodity (e.g. solar, wind, coal...)
    m.com = pyomo.Set(
        initialize=m.commodity.index.get_level_values('Commodity').unique(),
        doc='Set of commodities')

    # commodity type (i.e. SupIm, Demand, Stock, Env)
    m.com_type = pyomo.Set(
        initialize=m.commodity.index.get_level_values('Type').unique(),
        doc='Set of commodity types')

    # process (e.g. Wind turbine, Gas plant, Photovoltaics...)
    m.pro = pyomo.Set(
        initialize=m.process.index.get_level_values('Process').unique(),
        doc='Set of conversion processes')

    if not m.transmission.empty:
        # transmission (e.g. hvac, hvdc, pipeline...)
        m.tra = pyomo.Set(
            initialize=m.transmission.index.get_level_values('Transmission')
                                       .unique(),
            doc='Set of transmission technologies')

    # storage (e.g. hydrogen, pump storage)
    m.sto = pyomo.Set(
        initialize=m.storage.index.get_level_values('Storage').unique(),
        doc='Set of storage technologies')

    # cost_type
    m.cost_type = pyomo.Set(
        initialize=['Invest', 'Fixed', 'Variable', 'Fuel', 'Revenue',
                    'Purchase', 'Environmental'],
        doc='Set of cost types (hard-coded)')

    # tuple sets
    m.com_tuples = pyomo.Set(
        within=m.sit*m.com*m.com_type,
        initialize=m.commodity.index,
        doc='Combinations of defined commodities, e.g. (Mid,Elec,Demand)')
        
    m.pro_tuples = pyomo.Set(
        within=m.sit*m.pro,
        initialize=m.process.index,
        doc='Combinations of possible processes, e.g. (North,Coal plant)')
    m.pro_tuples_expansion = pyomo.Set(                                               ################
        within=m.sit*m.pro,
        initialize=[(site,process) 
                    for (site,process) in m.pro_tuples
                    if m.process_dict['inst-cap'][(site,process)] < m.process_dict['cap-up'][(site,process)]],
        doc='Combination of possible processes with expansion')
                    
    if not m.transmission.empty:
        m.tra_tuples = pyomo.Set(
            within=m.sit*m.sit*m.tra*m.com,
            initialize=m.transmission.index,
            doc='Combinations of possible transmissions, e.g. '
                '(South,Mid,hvac,Elec)')
    
    m.sto_tuples = pyomo.Set(
        within=m.sit*m.sto*m.com,
        initialize=m.storage.index,
        doc='Combinations of possible storage by site, e.g. (Mid,Bat,Elec)')
    m.dsm_site_tuples = pyomo.Set(
        within=m.sit*m.com,
        initialize=m.dsm.index,
        doc='Combinations of possible dsm by site, e.g. (Mid, Elec)')
    m.dsm_down_tuples = pyomo.Set(
        within=m.tm*m.tm*m.sit*m.com,
        initialize=[(t, tt, site, commodity)
                    for (t, tt, site, commodity)
                    in dsm_down_time_tuples(m.timesteps[1:],
                                            m.dsm_site_tuples,
                                            m)],
        doc='Combinations of possible dsm_down combinations, e.g. '
            '(5001,5003,Mid,Elec)')

    # process tuples for area rule
    m.pro_area_tuples = pyomo.Set(
        within=m.sit*m.pro,
        initialize=m.proc_area.index,
        doc='Processes and Sites with area Restriction')
    m.pro_area_tuples_expansion = pyomo.Set(                                                    ##################
        within=m.sit*m.pro,
        initialize=[(site,process) 
                    for (site,process) in m.pro_area_tuples
                    if m.process_dict['inst-cap'][(site,process)] < m.process_dict['cap-up'][(site,process)]],
        doc='Processes and sites with area restriction and expansion')

    # process input/output
    m.pro_input_tuples = pyomo.Set(
        within=m.sit*m.pro*m.com,
        initialize=[(site, process, commodity)
                    for (site, process) in m.pro_tuples
                    for (pro, commodity) in m.r_in.index
                    if process == pro],
        doc='Commodities consumed by process by site, e.g. (Mid,PV,Solar)')
    m.pro_input_tuples_const_cap = pyomo.Set(                                           
        within=m.sit*m.pro*m.com,
        initialize=[(site, process, commodity)
                    for (site, process) in m.pro_tuples-m.pro_tuples_expansion
                    for (pro, commodity) in m.r_in.index
                    if process == pro],
        doc='Commodities consumed by process by site for constant capacity, e.g. (Mid,PV,Solar)')
        
    m.pro_output_tuples = pyomo.Set(
        within=m.sit*m.pro*m.com,
        initialize=[(site, process, commodity)
                    for (site, process) in m.pro_tuples
                    for (pro, commodity) in m.r_out.index
                    if process == pro],
        doc='Commodities produced by process by site, e.g. (Mid,PV,Elec)')
    m.pro_output_tuples_const_cap = pyomo.Set(                                      
        within=m.sit*m.pro*m.com,
        initialize=[(site, process, commodity)
                    for (site, process) in m.pro_tuples-m.pro_tuples_expansion
                    for (pro, commodity) in m.r_out.index
                    if process == pro],
        doc='Commodities produced by process by site for constant capacity, e.g. (Mid,PV,Elec)')

    # process tuples for maximum gradient feature
    m.pro_maxgrad_tuples = pyomo.Set(
        within=m.sit*m.pro,
        initialize=[(sit, pro)
                    for (sit, pro) in m.pro_tuples
                    if m.process.loc[sit, pro]['max-grad'] < 1.0 / dt],
        doc='Processes with maximum gradient smaller than timestep length')
    m.pro_maxgrad_tuples_const_cap = pyomo.Set(                                    
        within=m.sit*m.pro,
        initialize=[(sit, pro)
                    for (sit, pro) in m.pro_tuples-m.pro_tuples_expansion
                    if m.process.loc[sit, pro]['max-grad'] < 1.0 / dt],
        doc='Processes with maximum gradient smaller than timestep length for constant capacity')
        
    # process tuples for partial feature
    m.pro_partial_tuples = pyomo.Set(
        within=m.sit*m.pro,
        initialize=[(site, process)
                    for (site, process) in m.pro_tuples
                    for (pro, _) in m.r_in_min_fraction.index
                    if process == pro],
        doc='Processes with partial input')
    m.pro_partial_tuples_const_cap = pyomo.Set(                                    
        within=m.sit*m.pro,
        initialize=[(site, process)
                    for (site, process) in m.pro_tuples-m.pro_tuples_expansion
                    for (pro, _) in m.r_in_min_fraction.index
                    if process == pro],
        doc='Processes with partial input for constant capacity')
        
    m.pro_partial_input_tuples = pyomo.Set(
        within=m.sit*m.pro*m.com,
        initialize=[(site, process, commodity)
                    for (site, process) in m.pro_partial_tuples
                    for (pro, commodity) in m.r_in_min_fraction.index
                    if process == pro],
        doc='Commodities with partial input ratio, e.g. (Mid,Coal PP,Coal)')
    m.pro_partial_input_tuples_const_cap = pyomo.Set(                               
        within=m.sit*m.pro*m.com,
        initialize=[(site, process, commodity)
                    for (site, process) in m.pro_partial_tuples_const_cap
                    for (pro, commodity) in m.r_in_min_fraction.index
                    if process == pro],
        doc='Commodities with partial input ratio for constant capacity, e.g. (Mid,Coal PP,Coal)')
        
    m.pro_partial_output_tuples = pyomo.Set(
        within=m.sit*m.pro*m.com,
        initialize=[(site, process, commodity)
                    for (site, process) in m.pro_partial_tuples
                    for (pro, commodity) in m.r_out_min_fraction.index
                    if process == pro],
        doc='Commodities with partial input ratio, e.g. (Mid,Coal PP,CO2)')
    m.pro_partial_output_tuples_const_cap = pyomo.Set(                             
        within=m.sit*m.pro*m.com,
        initialize=[(site, process, commodity)
                    for (site, process) in m.pro_partial_tuples_const_cap
                    for (pro, commodity) in m.r_out_min_fraction.index
                    if process == pro],
        doc='Commodities with partial input ratio for constant capacity, e.g. (Mid,Coal PP,CO2)')

    # commodity type subsets
    m.com_supim = pyomo.Set(
        within=m.com,
        initialize=commodity_subset(m.com_tuples, 'SupIm'),
        doc='Commodities that have intermittent (timeseries) input')
    m.com_stock = pyomo.Set(
        within=m.com,
        initialize=commodity_subset(m.com_tuples, 'Stock'),
        doc='Commodities that can be purchased at some site(s)')
    m.com_sell = pyomo.Set(
        within=m.com,
        initialize=commodity_subset(m.com_tuples, 'Sell'),
        doc='Commodities that can be sold')
    m.com_buy = pyomo.Set(
        within=m.com,
        initialize=commodity_subset(m.com_tuples, 'Buy'),
        doc='Commodities that can be purchased')
    m.com_demand = pyomo.Set(
        within=m.com,
        initialize=commodity_subset(m.com_tuples, 'Demand'),
        doc='Commodities that have a demand (implies timeseries)')
    m.com_env = pyomo.Set(
        within=m.com,
        initialize=commodity_subset(m.com_tuples, 'Env'),
        doc='Commodities that (might) have a maximum creation limit')

    # Parameters

    # weight = length of year (hours) / length of simulation (hours)
    # weight scales costs and emissions from length of simulation to a full
    # year, making comparisons among cost types (invest is annualized, fixed
    # costs are annual by default, variable costs are scaled by weight) and
    # among different simulation durations meaningful.
    m.weight = pyomo.Param(
        initialize=float(8760) / (len(m.tm) * dt),
        doc='Pre-factor for variable costs and emissions for an annual result')

    # dt = spacing between timesteps. Required for storage equation that
    # converts between energy (storage content, e_sto_con) and power (all other
    # quantities that start with "e_")
    m.dt = pyomo.Param(
        initialize=dt,
        doc='Time step duration (in hours), default: 1')
    
    
    """#process                                                                        ##########
    
    m.cap_pro_const = pyomo.Param(  
        within=m.sit*m.pro,
        initialize=[m.process_dict['inst-cap'][(sit, pro)]
                    for (sit,pro) in m.pro_tuples - m.pro_tuples_expansion],
        doc='Constant process capacity for no expansion')"""
    
    # Variables

    # costs
    m.costs = pyomo.Var(
        m.cost_type,
        within=pyomo.Reals,
        doc='Costs by type (EUR/a)')

    # commodity
    m.e_co_stock = pyomo.Var(
        m.tm, m.com_tuples,
        within=pyomo.NonNegativeReals,
        doc='Use of stock commodity source (MW) per timestep')
    m.e_co_sell = pyomo.Var(
        m.tm, m.com_tuples,
        within=pyomo.NonNegativeReals,
        doc='Use of sell commodity source (MW) per timestep')
    m.e_co_buy = pyomo.Var(
        m.tm, m.com_tuples,
        within=pyomo.NonNegativeReals,
        doc='Use of buy commodity source (MW) per timestep')

    # process																##########
    m.cap_pro = pyomo.Var(
        m.pro_tuples_expansion,
        within=pyomo.NonNegativeReals,
        doc='Total process capacity (MW)')         
    m.cap_pro_new = pyomo.Var(
        m.pro_tuples_expansion,
        within=pyomo.NonNegativeReals,
        doc='New process capacity (MW)')
    m.tau_pro = pyomo.Var(
        m.t, m.pro_tuples,
        within=pyomo.NonNegativeReals,
        doc='Power flow (MW) through process')
    m.e_pro_in = pyomo.Var(
        m.tm, m.pro_tuples, m.com,
        within=pyomo.NonNegativeReals,
        doc='Power flow of commodity into process (MW) per timestep')
    m.e_pro_out = pyomo.Var(
        m.tm, m.pro_tuples, m.com,
        within=pyomo.NonNegativeReals,
        doc='Power flow out of process (MW) per timestep')

    # transmission
    if not m.transmission.empty:
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

    # storage
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

    # demand side management
    m.dsm_up = pyomo.Var(
        m.tm, m.dsm_site_tuples,
        within=pyomo.NonNegativeReals,
        doc='DSM upshift')
    m.dsm_down = pyomo.Var(
        m.dsm_down_tuples,
        within=pyomo.NonNegativeReals,
        doc='DSM downshift')

    # Equation declarations
    # equation bodies are defined in separate functions, referred to here by
    # their name in the "rule" keyword.

    # commodity
    m.res_vertex = pyomo.Constraint(
        m.tm, m.com_tuples,
        rule=res_vertex_rule,
        doc='storage + transmission + process + source + buy - sell == demand')
    m.res_stock_step = pyomo.Constraint(
        m.tm, m.com_tuples,
        rule=res_stock_step_rule,
        doc='stock commodity input per step <= commodity.maxperstep')
    m.res_stock_total = pyomo.Constraint(
        m.com_tuples,
        rule=res_stock_total_rule,
        doc='total stock commodity input <= commodity.max')
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
    m.res_env_step = pyomo.Constraint(
        m.tm, m.com_tuples,
        rule=res_env_step_rule,
        doc='environmental output per step <= commodity.maxperstep')
    m.res_env_total = pyomo.Constraint(
        m.com_tuples,
        rule=res_env_total_rule,
        doc='total environmental commodity output <= commodity.max')

    # process															################################
    m.def_process_capacity = pyomo.Constraint(                            
        m.pro_tuples_expansion,
        rule=def_process_capacity_rule,
        doc='total process capacity = inst-cap + new capacity')
        
    m.def_process_input = pyomo.Constraint(
        m.tm, m.pro_input_tuples - m.pro_partial_input_tuples,
        rule=def_process_input_rule,
        doc='process input = process throughput * input ratio')
        
    m.def_process_output = pyomo.Constraint(
        m.tm, m.pro_output_tuples - m.pro_partial_output_tuples,
        rule=def_process_output_rule,
        doc='process output = process throughput * output ratio')
        
    m.def_intermittent_supply = pyomo.Constraint(                           
        m.tm, m.pro_input_tuples-m.pro_input_tuples_const_cap,
        rule=def_intermittent_supply_rule,
        doc='process output = process capacity * supim timeseries')
    m.def_intermittent_supply_const_cap = pyomo.Constraint(                 
        m.tm, m.pro_input_tuples_const_cap,
        rule=def_intermittent_supply_rule_const_cap,
        doc='process output = process capacity * supim timeseries')
        
    m.res_process_throughput_by_capacity = pyomo.Constraint(                
        m.tm, m.pro_tuples_expansion,
        rule=res_process_throughput_by_capacity_rule,
        doc='process throughput <= total process capacity')
    m.res_process_throughput_by_capacity_const_cap = pyomo.Constraint(               
        m.tm, m.pro_tuples-m.pro_tuples_expansion,
        rule=res_process_throughput_by_capacity_rule_const_cap,
        doc='process throughput <= total process capacity')
        
    m.res_process_maxgrad_lower = pyomo.Constraint(                                     
        m.tm, m.pro_maxgrad_tuples-m.pro_maxgrad_tuples_const_cap,
        rule=res_process_maxgrad_lower_rule,
        doc='throughput may not decrease faster than maximal gradient')
    m.res_process_maxgrad_lower_const_cap = pyomo.Constraint(                         
        m.tm, m.pro_maxgrad_tuples_const_cap,
        rule=res_process_maxgrad_lower_rule_const_cap,
        doc='throughput may not decrease faster than maximal gradient')
        
    m.res_process_maxgrad_upper = pyomo.Constraint(                                     
        m.tm, m.pro_maxgrad_tuples-m.pro_maxgrad_tuples_const_cap,
        rule=res_process_maxgrad_upper_rule,
        doc='throughput may not increase faster than maximal gradient')
    m.res_process_maxgrad_upper_const_cap = pyomo.Constraint(                         
        m.tm, m.pro_maxgrad_tuples_const_cap,
        rule=res_process_maxgrad_upper_rule_const_cap,
        doc='throughput may not increase faster than maximal gradient')
        
    m.res_process_capacity = pyomo.Constraint(                                           
        m.pro_tuples_expansion,
        rule=res_process_capacity_rule,
        doc='process.cap-lo <= total process capacity <= process.cap-up')
    m.res_process_capacity_const_cap = pyomo.Constraint(                              
        m.pro_tuples-m.pro_tuples_expansion,
        rule=res_process_capacity_rule_const_cap,
        doc='process.cap-lo <= total process capacity <= process.cap-up')  
        
    m.res_throughput_by_capacity_min = pyomo.Constraint(                                
        m.tm, m.pro_partial_tuples-m.pro_partial_tuples_const_cap,
        rule=res_throughput_by_capacity_min_rule,
        doc='cap_pro * min-fraction <= tau_pro')
    m.res_throughput_by_capacity_min_const_cap = pyomo.Constraint(                      
        m.tm, m.pro_partial_tuples_const_cap,
        rule=res_throughput_by_capacity_min_rule_const_cap,
        doc='cap_pro * min-fraction <= tau_pro')
        
    m.def_partial_process_input = pyomo.Constraint(                                     
        m.tm, m.pro_partial_input_tuples-m.pro_partial_input_tuples_const_cap,
        rule=def_partial_process_input_rule,
        doc='e_pro_in = '
            ' cap_pro * min_fraction * (r - R) / (1 - min_fraction)'
            ' + tau_pro * (R - min_fraction * r) / (1 - min_fraction)')
    m.def_partial_process_input_const_cap = pyomo.Constraint(                                    
        m.tm, m.pro_partial_input_tuples_const_cap,
        rule=def_partial_process_input_rule_const_cap,
        doc='e_pro_in = '
            ' cap_pro * min_fraction * (r - R) / (1 - min_fraction)'
            ' + tau_pro * (R - min_fraction * r) / (1 - min_fraction)')
            
    m.def_partial_process_output = pyomo.Constraint(                                             
        m.tm, m.pro_partial_output_tuples-m.pro_partial_output_tuples_const_cap,
        rule=def_partial_process_output_rule,
        doc='e_pro_out = '
            ' cap_pro * min_fraction * (r - R) / (1 - min_fraction)'
            ' + tau_pro * (R - min_fraction * r) / (1 - min_fraction)')
    m.def_partial_process_output_const_cap = pyomo.Constraint(                                     
        m.tm, m.pro_partial_output_tuples_const_cap,
        rule=def_partial_process_output_rule_const_cap,
        doc='e_pro_out = '
            ' cap_pro * min_fraction * (r - R) / (1 - min_fraction)'
            ' + tau_pro * (R - min_fraction * r) / (1 - min_fraction)')

    m.res_area = pyomo.Constraint(
        m.sit,
        rule=res_area_rule,
        doc='used process area <= total process area')

    m.res_sell_buy_symmetry = pyomo.Constraint(
        m.pro_input_tuples-m.pro_input_tuples_const_cap,
        rule=res_sell_buy_symmetry_rule,
        doc='power connection capacity must be symmetric in both directions')
    m.res_sell_buy_symmetry_const_cap = pyomo.Constraint(
        m.pro_input_tuples_const_cap,
        rule=res_sell_buy_symmetry_rule_const_cap,
        doc='power connection capacity must be symmetric in both directions')


    # transmission
    if not m.transmission.empty:
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

    # storage
    m.def_storage_state = pyomo.Constraint(
        m.tm, m.sto_tuples,
        rule=def_storage_state_rule,
        doc='storage[t] = storage[t-1] * (1 - discharge) + input - output')
    m.def_storage_power = pyomo.Constraint(
        m.sto_tuples,
        rule=def_storage_power_rule,
        doc='storage power = inst-cap + new power')
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
        m.t, m.sto_tuples,
        rule=res_initial_and_final_storage_state_rule,
        doc='storage content initial == and final >= storage.init * capacity')

    # costs
    m.def_costs = pyomo.Constraint(
        m.cost_type,
        rule=def_costs_rule,
        doc='main cost function by cost type')
    m.obj = pyomo.Objective(
        rule=obj_rule,
        sense=pyomo.minimize,
        doc='minimize(cost = sum of all cost types)')

    # demand side management
    m.def_dsm_variables = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=def_dsm_variables_rule,
        doc='DSMup * efficiency factor n == DSMdo')

    m.res_dsm_upward = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=res_dsm_upward_rule,
        doc='DSMup <= Cup (threshold capacity of DSMup)')

    m.res_dsm_downward = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=res_dsm_downward_rule,
        doc='DSMdo <= Cdo (threshold capacity of DSMdo)')

    m.res_dsm_maximum = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=res_dsm_maximum_rule,
        doc='DSMup + DSMdo <= max(Cup,Cdo)')

    m.res_dsm_recovery = pyomo.Constraint(
        m.tm, m.dsm_site_tuples,
        rule=res_dsm_recovery_rule,
        doc='DSMup(t, t + recovery time R) <= Cup * delay time L')

    m.res_global_co2_limit = pyomo.Constraint(
            rule=res_global_co2_limit_rule,
            doc='total co2 commodity output <= Global CO2 limit')

    if dual:
        m.dual = pyomo.Suffix(direction=pyomo.Suffix.IMPORT)
    return m


# Constraints

# total CO2 output <= Global CO2 limit
def res_global_co2_limit_rule(m):
    if math.isinf(m.global_prop.loc['CO2 limit', 'value']):
        return pyomo.Constraint.Skip
    elif m.global_prop.loc['CO2 limit', 'value'] >= 0:
        co2_output_sum = 0
        for tm in m.tm:
            for sit in m.sit:
                # minus because negative commodity_balance represents creation
                # of that commodity.
                co2_output_sum += (- commodity_balance(m, tm, sit, 'CO2') *
                                   m.dt)

        # scaling to annual output (cf. definition of m.weight)
        co2_output_sum *= m.weight
        return (co2_output_sum <= m.global_prop.loc['CO2 limit', 'value'])
    else:
        return pyomo.Constraint.Skip


# Objective
def def_costs_rule(m, cost_type):
    """Calculate total costs by cost type.

    Sums up process activity and capacity expansions
    and sums them in the cost types that are specified in the set
    m.cost_type. To change or add cost types, add/change entries
    there and modify the if/elif cases in this function accordingly.

    Cost types are
      - Investment costs for process power, storage power and
        storage capacity. They are multiplied by the annuity
        factors.
      - Fixed costs for process power, storage power and storage
        capacity.
      - Variables costs for usage of processes, storage and transmission.
      - Fuel costs for stock commodity purchase.

    """
    #count sites                                                                ###################
    site_count = m.site.size                                        
    
    if cost_type == 'Invest':
        if not m.transmission.empty:
            return m.costs[cost_type] == \
				sum(m.cap_pro_new[p] *
					m.process_dict['inv-cost'][p] *
					m.process_dict['annuity-factor'][p]
					for p in m.pro_tuples_expansion) + \
				sum(m.cap_tra_new[t] *
					m.transmission_dict['inv-cost'][t] *
					m.transmission_dict['annuity-factor'][t]
					for t in m.tra_tuples) + \
				sum(m.cap_sto_p_new[s] *
					m.storage_dict['inv-cost-p'][s] *
					m.storage_dict['annuity-factor'][s] +
					m.cap_sto_c_new[s] *
					m.storage_dict['inv-cost-c'][s] *
					m.storage_dict['annuity-factor'][s]
					for s in m.sto_tuples)
        else:
            return m.costs[cost_type] == \
                    sum(m.cap_pro_new[p] *
                        m.process_dict['inv-cost'][p] *
                        m.process_dict['annuity-factor'][p]
                        for p in m.pro_tuples_expansion) + \
                    sum(m.cap_sto_p_new[s] *
                        m.storage_dict['inv-cost-p'][s] *
                        m.storage_dict['annuity-factor'][s] +
                        m.cap_sto_c_new[s] *
                        m.storage_dict['inv-cost-c'][s] *
                        m.storage_dict['annuity-factor'][s]
                        for s in m.sto_tuples)

    elif cost_type == 'Fixed':
        if not m.transmission.empty:
            return m.costs[cost_type] == \
                    sum(m.cap_pro[p] * m.process_dict['fix-cost'][p]
                        for p in m.pro_tuples_expansion) + \
                    sum(m.process_dict['inst-cap'][(p)] * m.process_dict['fix-cost'][p]
                        for p in (m.pro_tuples-m.pro_tuples_expansion)) + \
                    sum(m.cap_tra[t] * m.transmission_dict['fix-cost'][t]
                        for t in m.tra_tuples) + \
                    sum(m.cap_sto_p[s] * m.storage_dict['fix-cost-p'][s] +
                        m.cap_sto_c[s] * m.storage_dict['fix-cost-c'][s]
                        for s in m.sto_tuples)
        else:
            return m.costs[cost_type] == \
                    sum(m.cap_pro[p] * m.process_dict['fix-cost'][p]
                        for p in m.pro_tuples) + \
                    sum(m.process_dict['inst-cap'][(p)] * m.process_dict['fix-cost'][p]
                        for p in m.pro_tuples-m.pro_tuples_expansion) + \
                    sum(m.cap_sto_p[s] * m.storage_dict['fix-cost-p'][s] +
                        m.cap_sto_c[s] * m.storage_dict['fix-cost-c'][s]
                        for s in m.sto_tuples)

    elif cost_type == 'Variable':
        if not m.transmission.empty:
            return m.costs[cost_type] == \
                    sum(m.tau_pro[(tm,) + p] * m.dt * m.weight *
                        m.process_dict['var-cost'][p]
                        for tm in m.tm
                        for p in m.pro_tuples) + \
                    sum(m.e_tra_in[(tm,) + t] * m.dt * m.weight *
                        m.transmission_dict['var-cost'][t]
                        for tm in m.tm
                        for t in m.tra_tuples) + \
                    sum(m.e_sto_con[(tm,) + s] * m.weight *
                        m.storage_dict['var-cost-c'][s] +
                        m.dt * m.weight *
                        (m.e_sto_in[(tm,) + s] + m.e_sto_out[(tm,) + s]) *
                        m.storage_dict['var-cost-p'][s]
                        for tm in m.tm
                        for s in m.sto_tuples)
        else:
            return m.costs[cost_type] == \
                    sum(m.tau_pro[(tm,) + p] * m.dt * m.weight *
                        m.process_dict['var-cost'][p]
                        for tm in m.tm
                        for p in m.pro_tuples) + \
                    sum(m.e_sto_con[(tm,) + s] * m.weight *
                        m.storage_dict['var-cost-c'][s] +
                        m.dt * m.weight *
                        (m.e_sto_in[(tm,) + s] + m.e_sto_out[(tm,) + s]) *
                        m.storage_dict['var-cost-p'][s]
                        for tm in m.tm
                        for s in m.sto_tuples)

    elif cost_type == 'Fuel':
        return m.costs[cost_type] == sum(
            m.e_co_stock[(tm,) + c] * m.dt * m.weight *
            m.commodity_dict['price'][c]
            for tm in m.tm for c in m.com_tuples
            if c[1] in m.com_stock)

    elif cost_type == 'Revenue':
        sell_tuples = commodity_subset(m.com_tuples, m.com_sell)

        try:
            return m.costs[cost_type] == -sum(
                m.e_co_sell[(tm,) + c] * m.weight * m.dt *
                m.buy_sell_price_dict[c[1], ][tm] *
                m.commodity_dict['price'][c]
                for tm in m.tm
                for c in sell_tuples)
        except KeyError:
            return m.costs[cost_type] == -sum(
                m.e_co_sell[(tm,) + c] * m.weight * m.dt *
                m.buy_sell_price_dict[c[1]][tm] *
                m.commodity_dict['price'][c]
                for tm in m.tm
                for c in sell_tuples)

    elif cost_type == 'Purchase':
        buy_tuples = commodity_subset(m.com_tuples, m.com_buy)

        try:
            return m.costs[cost_type] == sum(
                m.e_co_buy[(tm,) + c] * m.weight * m.dt *
                m.buy_sell_price_dict[c[1], ][tm] *
                m.commodity_dict['price'][c]
                for tm in m.tm
                for c in buy_tuples)
        except KeyError:
            return m.costs[cost_type] == sum(
                m.e_co_buy[(tm,) + c] * m.weight * m.dt *
                m.buy_sell_price_dict[c[1]][tm] *
                m.commodity_dict['price'][c]
                for tm in m.tm
                for c in buy_tuples)

    elif cost_type == 'Environmental':
        return m.costs[cost_type] == sum(
            - commodity_balance(m, tm, sit, com) *
            m.weight * m.dt *
            m.commodity_dict['price'][(sit, com, com_type)]
            for tm in m.tm
            for sit, com, com_type in m.com_tuples
            if com in m.com_env)

    else:
        raise NotImplementedError("Unknown cost type.")


def obj_rule(m):
    return pyomo.summation(m.costs)
