import pandas as pd
import os
import glob
from xlrd import XLRDError
import pyomo.core as pyomo
from datetime import date
from .features.modelhelper import *
from .identify import identify_mode

def read_input(input_files):
    """Read Excel input file and prepare URBS input dict.

    Reads an Excel spreadsheet that adheres to the structure shown in
    mimo-example.xlsx. Two preprocessing steps happen here:
    1. Column titles in 'Demand' and 'SupIm' are split, so that
    'Site.Commodity' becomes the MultiIndex column ('Site', 'Commodity').
    2. The attribute 'annuity-factor' is derived here from the columns 'wacc'
    and 'depreciation' for 'Process', 'Transmission' and 'Storage'.

    Args:
        filename: filename to an Excel spreadsheet with the required sheets
            'Commodity', 'Process', 'Transmission', 'Storage', 'Demand' and
            'SupIm'.

    Returns:
        a dict of 6 DataFrames

    Example:
        >>> data = read_excel('mimo-example.xlsx')
        >>> data['global_prop'].loc['CO2 limit', 'value']
        150000000
    """
    if input_files == 'Input':
        glob_input = os.path.join(input_files, '*.xlsx')
        input_files = sorted(glob.glob(glob_input))
    else:
        input_files = [input_files]

    gl = []
    sit = []
    com = []
    pro = []
    pro_com = []
    tra = []
    sto = []
    dem = []
    sup = []
    bsp = []
    ds = []
    ef = [] 

    # get mode
    mode = identify_mode(input_files[0])  
    print ("mode: ",mode) 

    for filename in input_files:
        # identify mode of input_file
        with pd.ExcelFile(filename) as xls:

            sheetnames = xls.sheet_names
            global_prop = xls.parse('Global').set_index(['Property'])
            # create support timeframe index
            if mode['int']:
                support_timeframe = ( 
                    global_prop.loc['Support timeframe']['value'])
                global_prop = (
                    global_prop.drop(['Support timeframe'])
                    .drop(['description'], axis=1))
            else:
                support_timeframe = date.today().year
            print(support_timeframe)
            global_prop = pd.concat([global_prop], keys=[support_timeframe],
                                    names=['support_timeframe'])
            gl.append(global_prop)
            site = xls.parse('Site').set_index(['Name'])
            site = pd.concat([site], keys=[support_timeframe],
                             names=['support_timeframe'])
            sit.append(site)
            commodity = (
                xls.parse('Commodity')
                   .set_index(['Site', 'Commodity', 'Type']))
            commodity = pd.concat([commodity], keys=[support_timeframe],
                                  names=['support_timeframe'])
            com.append(commodity)
            process = xls.parse('Process').set_index(['Site', 'Process'])
            process = pd.concat([process], keys=[support_timeframe],
                                names=['support_timeframe'])
            pro.append(process)
            process_commodity = (
                xls.parse('Process-Commodity')
                   .set_index(['Process', 'Commodity', 'Direction']))
            process_commodity = pd.concat([process_commodity],
                                          keys=[support_timeframe],
                                          names=['support_timeframe'])
            pro_com.append(process_commodity)
            demand = xls.parse('Demand').set_index(['t'])
            demand = pd.concat([demand], keys=[support_timeframe],
                               names=['support_timeframe'])
            dem.append(demand)
            supim = xls.parse('SupIm').set_index(['t'])
            supim = pd.concat([supim], keys=[support_timeframe],
                              names=['support_timeframe'])
            sup.append(supim)

            # collect data for the additional features 
            # Transmission, Storage, DSM
            if mode['tra']:
                transmission = (
                    xls.parse('Transmission')
                    .set_index(['Site In', 'Site Out',
                                'Transmission', 'Commodity']))
                transmission = (
                pd.concat([transmission], keys=[support_timeframe],
                            names=['support_timeframe']))
                tra.append(transmission)
            if mode['sto']:
                storage = (
                    xls.parse('Storage')
                    .set_index(['Site', 'Storage', 'Commodity']))
                storage = pd.concat([storage], keys=[support_timeframe],
                                    names=['support_timeframe'])
                sto.append(storage)  
            if mode['dsm']:
                dsm = xls.parse('DSM').set_index(['Site', 'Commodity'])
                dsm = pd.concat([dsm], keys=[support_timeframe],
                                names=['support_timeframe'])
                ds.append(dsm)
            if mode['bsp']:
                buy_sell_price = xls.parse('Buy-Sell-Price').set_index(['t'])
                buy_sell_price = pd.concat([buy_sell_price],
                                        keys=[support_timeframe],
                                        names=['support_timeframe'])
                bsp.append(buy_sell_price)
            if mode['eff']:
                eff_factor = (xls.parse('TimeVarEff').set_index(['t']))
                eff_factor = pd.concat([eff_factor], keys=[support_timeframe],
                                       names=['support_timeframe'])
                eff_factor.columns = split_columns(eff_factor.columns, '.')
                ef.append(eff_factor)

        # prepare input data
        # split columns by dots '.', so that 'DE.Elec' becomes the two-level
        # column index ('DE', 'Elec')
        demand.columns = split_columns(demand.columns, '.')
        supim.columns = split_columns(supim.columns, '.')
        buy_sell_price.columns = split_columns(buy_sell_price.columns, '.')

    if mode['int']:
        global_prop = pd.concat(gl)
        site = pd.concat(sit)
        commodity = pd.concat(com)
        process = pd.concat(pro)
        process_commodity = pd.concat(pro_com)  
        demand = pd.concat(dem)
        supim = pd.concat(sup)
        if mode['tra']:
            transmission = pd.concat(tra)
        if mode['sto']:
            storage = pd.concat(sto)
        if mode['dsm']:
            dsm = pd.concat(ds)
        if mode['bsp']:
            buy_sell_price = pd.concat(bsp)
        if mode['eff']:
            eff_factor = pd.concat(ef)


    data = {
        'global_prop': global_prop,
        'site': site,
        'commodity': commodity,
        'process': process,
        'process_commodity': process_commodity,
        'demand': demand,
        'supim': supim,
        }
    # write data for additional features into "data"
    if mode['tra']:
        data['transmission'] = transmission
    if mode['sto']:
        data['storage'] = storage
    if mode['dsm']:
        data['dsm'] = dsm
    if mode['bsp']:
        data['buy_sell_price'] = buy_sell_price
    if mode['eff']:
        data['eff_factor'] = eff_factor       

    # sort nested indexes to make direct assignments work
    for key in data:
        if isinstance(data[key].index, pd.core.index.MultiIndex):
            data[key].sort_index(inplace=True)
    return data, mode


# preparing the pyomo model
def pyomo_model_prep(data, mode, timesteps):
    m = pyomo.ConcreteModel()

    # Preparations
    # ============
    # Data import. Syntax to access a value within equation definitions looks
    # like this:
    #
    #     storage.loc[site, storage, commodity][attribute]
    #

    m.mode = mode
    m.timesteps = timesteps
    process = data['process']
    commodity = data["commodity"]
    # Converting Data frames to dict
    m.global_prop = data['global_prop'].drop('description', axis=1)
    m.global_prop_dict = m.global_prop.to_dict()
    m.site_dict = data["site"].to_dict()
    m.demand_dict = data["demand"].to_dict()
    m.supim_dict = data["supim"].to_dict()

    # additional features
    if m.mode['tra']:
        transmission = data['transmission']
    if m.mode['sto']:
        storage = data['storage']
    if m.mode['dsm']:
        m.dsm_dict = data["dsm"].to_dict()
    if m.mode['bsp']:
        m.buy_sell_price_dict = data["buy_sell_price"].to_dict()
    if m.mode['eff']: 
        m.eff_factor_dict = data["eff_factor"].to_dict()

    # Create columns of support timeframe values
    commodity['support_timeframe'] = (commodity.index.
                                        get_level_values('support_timeframe'))
    process['support_timeframe'] = (process.index.
                                    get_level_values('support_timeframe'))
    if m.mode['tra']:
        transmission['support_timeframe'] = (transmission.index.
                                        get_level_values
                                        ('support_timeframe'))
    if m.mode['sto']:
        storage['support_timeframe'] = (storage.index.
                                    get_level_values('support_timeframe'))
    
    # installed units for intertemporal planning
    m.inst_pro = process['inst-cap']
    m.inst_pro = m.inst_pro[m.inst_pro > 0]
    if m.mode['tra']:
        m.inst_tra = transmission['inst-cap']
        m.inst_tra = m.inst_tra[m.inst_tra > 0]
    if m.mode['sto']:
        m.inst_sto = storage['inst-cap-p']
        m.inst_sto = m.inst_sto[m.inst_sto > 0]

    # process input/output ratios
    m.r_in_dict = (data['process_commodity'].xs('In', level='Direction')
                   ['ratio'].to_dict())
    m.r_out_dict = (data['process_commodity'].xs('Out', level='Direction')
                    ['ratio'].to_dict())

    # process areas
    proc_area = data["process"]['area-per-cap']
    proc_area = proc_area[proc_area >= 0]
    m.proc_area_dict = proc_area.to_dict()

    # input ratios for partial efficiencies
    # only keep those entries whose values are
    # a) positive and
    # b) numeric (implicitely, as NaN or NV compare false against 0)
    r_in_min_fraction = data['process_commodity'].xs('In', level='Direction')
    r_in_min_fraction = r_in_min_fraction['ratio-min']
    r_in_min_fraction = r_in_min_fraction[r_in_min_fraction > 0]
    m.r_in_min_fraction_dict = r_in_min_fraction.to_dict()

    # output ratios for partial efficiencies
    # only keep those entries whose values are
    # a) positive and
    # b) numeric (implicitely, as NaN or NV compare false against 0)
    r_out_min_fraction = data['process_commodity'].xs('Out', level='Direction')
    r_out_min_fraction = r_out_min_fraction['ratio-min']
    r_out_min_fraction = r_out_min_fraction[r_out_min_fraction > 0]
    m.r_out_min_fraction_dict = r_out_min_fraction.to_dict()

    # storages with fixed initial state
    if m.mode['sto']:
        stor_init_bound = storage['init']
        m.stor_init_bound_dict = stor_init_bound[m.stor_init_bound >= 0].to_dict()

        # storages with fixed energy-to-power ratio
        sto_ep_ratio = storage['ep-ratio']
        m.sto_ep_ratio_dict = sto_ep_ratio[m.sto_ep_ratio >= 0].to_dict()

    
    # derive invcost factor from WACC and depreciation duration
    if m.mode['int']:
        # derive invest factor from WACC, depreciation and discount untility
        process['discount'] = (m.global_prop.xs('Discount rate', level=1)
                                .loc[m.global_prop.index.min()[0]]['value'])
        process['stf_min'] = m.global_prop.index.min()[0]
        process['stf_end'] = (m.global_prop.index.max()[0] +
                                m.global_prop.loc[(max(commodity.
                                                index.get_level_values
                                                ('support_timeframe').unique()),
                                                'Weight')]['value'] - 1)
        process['invcost-factor'] = (process.apply(lambda x:
                                    invcost_factor(x['depreciation'],
                                                    x['wacc'],
                                                    x['discount'],
                                                    x['support_timeframe'],
                                                    x['stf_min']),
                                    axis=1))

        # derive overpay-factor from WACC, depreciation and discount untility
        process['overpay-factor'] = (process.apply(lambda x:
                                    overpay_factor(x['depreciation'],
                                                    x['wacc'],
                                                    x['discount'],
                                                    x['support_timeframe'],
                                                    x['stf_min'],
                                                    x['stf_end']),
                                    axis=1))
        process.loc[(process['overpay-factor'] < 0) |
                    (process['overpay-factor']
                     .isnull()), 'overpay-factor'] = 0

        # Derive multiplier for all energy based costs
        commodity['stf_dist'] = (commodity['support_timeframe'].
                                apply(stf_dist, m=m))
        commodity['discount-factor'] = (commodity['support_timeframe'].
                                        apply(discount_factor, m=m))
        commodity['eff-distance'] = (commodity['stf_dist'].
                                    apply(effective_distance, m=m))
        commodity['cost_factor'] = (commodity['discount-factor'] *
                                        commodity['eff-distance'])
        process['stf_dist'] = (process['support_timeframe']
                                .apply(stf_dist, m=m))
        process['discount-factor'] = (process['support_timeframe'].
                                        apply(discount_factor, m=m))
        process['eff-distance'] = (process['stf_dist'].
                                    apply(effective_distance, m=m))
        process['cost_factor'] = (process['discount-factor'] *
                                        process['eff-distance'])


        # transmission mode
        if m.mode['tra']:
            transmission['discount'] = (
                m.global_prop.xs('Discount rate', level=1)
                .loc[m.global_prop.index.min()[0]]['value'])
            transmission['stf_min'] = m.global_prop.index.min()[0]
            transmission['stf_end'] = (m.global_prop.index.max()[0] +
                                        m.global_prop.loc[(max(commodity.
                                                        index.get_level_values
                                                        ('support_timeframe').
                                                        unique()), 'Weight')]
                                                        ['value'] - 1)            
            transmission['invcost-factor'] = (
                transmission.apply(lambda x:
                                        invcost_factor(
                                        x['depreciation'],
                                        x['wacc'],
                                        x['discount'],
                                        x['support_timeframe'],
                                        x['stf_min']),
                                        axis=1))
            transmission['overpay-factor'] = (
                transmission.apply(lambda x:
                                        overpay_factor(
                                        x['depreciation'],
                                        x['wacc'],
                                        x['discount'],
                                        x['support_timeframe'],
                                        x['stf_min'],
                                        x['stf_end']),
                                        axis=1))

            transmission.loc[(transmission['overpay-factor'] < 0) |
                                (transmission['overpay-factor'].isnull()),
                                'overpay-factor'] = 0
            transmission['stf_dist'] = (transmission['support_timeframe'].
                                        apply(stf_dist, m=m))
            transmission['discount-factor'] = (
                transmission['support_timeframe'].apply(discount_factor, m=m))
            transmission['eff-distance'] = (transmission['stf_dist'].
                                            apply(effective_distance, m=m))
            transmission['cost_factor'] = (transmission['discount-factor'] *
                                            transmission['eff-distance'])
        # storage mode
        if m.mode['sto']:
            storage['discount'] = (m.global_prop.xs('Discount rate', level=1)
                                    .loc[m.global_prop.index.min()[0]]['value'])
            storage['stf_min'] = m.global_prop.index.min()[0]
            storage['stf_end'] = (m.global_prop.index.max()[0] +
                                    m.global_prop.loc[(max(commodity.
                                                    index.get_level_values
                                                    ('support_timeframe')
                                                     .unique()),
                                                     'Weight')]['value'] - 1)
            storage['invcost-factor'] = (storage.apply(lambda x:
                                        invcost_factor(x['depreciation'],
                                                        x['wacc'],
                                                        x['discount'],
                                                        x['support_timeframe'],
                                                        x['stf_min']),
                                        axis=1))
            storage['overpay-factor'] = (
                storage.apply(lambda x:
                                overpay_factor(x['depreciation'],
                                                x['wacc'],
                                                x['discount'],
                                                x['support_timeframe'],
                                                x['stf_min'],
                                                x['stf_end']),
                                axis=1))

            storage.loc[(storage['overpay-factor'] < 0) |
                        (storage['overpay-factor'].isnull()),
                        'overpay-factor'] = 0

            storage['stf_dist'] = (storage['support_timeframe']
                                    .apply(stf_dist, m=m))
            storage['discount-factor'] = (storage['support_timeframe'].
                                            apply(discount_factor, m=m))
            storage['eff-distance'] = (storage['stf_dist'].
                                        apply(effective_distance, m=m))
            storage['cost_factor'] = (storage['discount-factor'] *
                                        storage['eff-distance']) 
    else:
        # for one year problems
        process['invcost-factor'] = (process.apply(lambda x:
                                       invcost_factor(x['depreciation'],
                                                      x['wacc']),
                                       axis=1))

        # cost factor will be set to 1 for non intertmporal problems
        commodity['cost_factor'] = 1
        process['cost_factor'] = 1

        # additional features
        if m.mode['tra']:
            transmission['invcost-factor'] = (
                    transmission.apply(lambda x:
                    invcost_factor(x['depreciation'], x['wacc']),
                    axis=1))
            transmission['cost_factor'] = 1
        if m.mode['sto']:
            storage['invcost-factor'] = (
                    storage.apply(lambda x:
                    invcost_factor(x['depreciation'], x['wacc']),
                    axis=1))
            storage['cost_factor'] = 1
        

    # Converting Data frames to dictionaries
    m.commodity_dict = commodity.to_dict()
    m.process_dict = process.to_dict()
    # additional features
    if m.mode['tra']:
        m.transmission_dict = transmission.to_dict()
    if m.mode['sto']:
        m.storage_dict = storage.to_dict()
    return m


def split_columns(columns, sep='.'):
    """Split columns by separator into MultiIndex.

    Given a list of column labels containing a separator string (default: '.'),
    derive a MulitIndex that is split at the separator string.

    Args:
        columns: list of column labels, containing the separator string
        sep: the separator string (default: '.')

    Returns:
        a MultiIndex corresponding to input, with levels split at separator

    Example:
        >>> split_columns(['DE.Elec', 'MA.Elec', 'NO.Wind'])
        MultiIndex(levels=[['DE', 'MA', 'NO'], ['Elec', 'Wind']],
                   labels=[[0, 1, 2], [0, 0, 1]])

    """
    if len(columns) == 0:
        return columns
    column_tuples = [tuple(col.split('.')) for col in columns]
    return pd.MultiIndex.from_tuples(column_tuples)


def get_input(prob, name):
    """Return input DataFrame of given name from urbs instance.

    These are identical to the key names returned by function `read_excel`.
    That means they are lower-case names and use underscores for word
    separation, e.g. 'process_commodity'.

    Args:
        prob: a urbs model instance
        name: an input DataFrame name ('commodity', 'process', ...)

    Returns:
        the corresponding input DataFrame

    """
    if hasattr(prob, name):
        # classic case: input data DataFrames are accessible via named
        # attributes, e.g. `prob.process`.
        return getattr(prob, name)
    elif hasattr(prob, '_data') and name in prob._data:
        # load case: input data is accessible via the input data cache dict
        return prob._data[name]
    else:
        # unknown
        raise ValueError("Unknown input DataFrame name!")
