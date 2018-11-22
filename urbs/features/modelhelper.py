from .transmission import transmission_balance
from .storage import storage_balance

def invcost_factor(n, i, j=None, year_built=None, stf_min=None):
    """Investment cost factor formula.
    Evaluates the factor multiplied to the invest costs
    for depreciation duration and interest rate.
    Args:
        n: depreciation period (years)
        i: interest rate (e.g. 0.06 means 6 %)
        year_built: year utility is built
        j: discount rate for intertmeporal planning
    """
    # invcost factor for non intertemporal planning
    if j == None:
        if i == 0:
            return 1 / n
        else:
            return (1+i)**n * i / ((1+i)**n - 1)
    elif j == 0:
        if i == 0:
            return 1
        else:
            return n * ((1+i) ** n * i)/((1+i) ** n - 1)
    else:
        if i == 0:
            return ((1+j) ** (1-(year_built-stf_min)) *
                    ((1+j) ** n - 1) / (n * j * (1+j) ** n))
        else:
            return ((1+j) ** (1-(year_built-stf_min)) *
                    (i * (1+i) ** n * ((1+j) ** n - 1)) /
                    (j * (1+j) ** n * ((1+i) ** n - 1)))


def overpay_factor(n, i, j, year_built, stf_min, stf_end):
    """Overpay value factor formula.
    Evaluates the factor multiplied to the invest costs
    for all annuity payments of a unit after the end of the
    optimization period.
    Args:
        n: depreciation period (years)
        i: interest rate (e.g. 0.06 means 6 %)
        year_built: year utility is built
        j: discount rate for intertmeporal planning
        k: operational time after simulation horizon
    """

    k = (year_built + n) - stf_end - 1

    if j == 0:
        if i == 0:
            return k / n
        else:
            return k * ((1+i) ** n * i)/((1+i) ** n - 1)
    else:
        if i == 0:
            return ((1+j) ** (1-(year_built-stf_min)) *
                    ((1+j) ** k - 1) / (n * j * (1+j) ** n))
        else:
            return ((1+j) ** (1-(year_built-stf_min)) *
                    (i * (1+i) ** n * ((1+j) ** k - 1)) /
                    (j * (1+j) ** n * ((1+i) ** n - 1)))


# Energy related costs
def stf_dist(stf, m):
    """Calculates the distance between the modeled support timeframes.
    """
    sorted_stf = sorted(list(m.commodity.index.
                             get_level_values('support_timeframe').unique()))
    dist = []

    for s in sorted_stf:
        if s == max(sorted_stf):
            dist.append(m.global_prop.loc[(s, 'Weight')]['value'])
        else:
            dist.append(sorted_stf[sorted_stf.index(s) + 1] - s)

    return dist[sorted_stf.index(stf)]


def discount_factor(stf, m):
    """Discount for any payment made in the year stf
    """
    j = (m.global_prop.xs('Discount rate', level=1)
         .loc[m.global_prop.index.min()[0]]['value'])

    return (1+j) ** (1-(stf-m.global_prop.index.min()[0]))


def effective_distance(dist, m):
    """Factor for variable, fuel, purchase, sell, and fix costs.
    Calculated by repetition of modeled stfs and discount utility.
    """
    j = (m.global_prop.xs('Discount rate', level=1)
         .loc[m.global_prop.index.min()[0]]['value'])

    if j == 0:
        return dist
    else:
        return (1-(1+j) ** (-dist)) / j


def commodity_balance(m, tm, stf, sit, com):
    """Calculate commodity balance at given timestep.
    For a given commodity co and timestep tm, calculate the balance of
    consumed (to process/storage/transmission, counts positive) and provided
    (from process/storage/transmission, counts negative) commodity flow. Used
    as helper function in create_model for constraints on demand and stock
    commodities.
    Args:
        m: the model object
        tm: the timestep
        site: the site
        com: the commodity
    Returns
        balance: net value of consumed (positive) or provided (negative) power
    """
    balance = (sum(m.e_pro_in[(tm, stframe, site, process, com)]
                   # usage as input for process increases balance
                   for stframe, site, process in m.pro_tuples
                   if site == sit and stframe == stf and
                   (stframe, process, com) in m.r_in_dict) -
               sum(m.e_pro_out[(tm, stframe, site, process, com)]
                   # output from processes decreases balance
                   for stframe, site, process in m.pro_tuples
                   if site == sit and stframe == stf and
                   (stframe, process, com) in m.r_out_dict))
    if m.mode['tra']:
        balance += transmission_balance(m, tm, stf, sit, com)
    if m.mode['sto']:    
        balance += storage_balance(m, tm, stf, sit, com)

    return balance

def commodity_subset(com_tuples, type_name):
    """ Unique list of commodity names for given type.
    Args:
        com_tuples: a list of (site, commodity, commodity type) tuples
        type_name: a commodity type or a list of a commodity types
    Returns:
        The set (unique elements/list) of commodity names of the desired type
    """
    if type(type_name) is str:
        # type_name: ('Stock', 'SupIm', 'Env' or 'Demand')
        return set(com for stf, sit, com, com_type in com_tuples
                   if com_type == type_name)
    else:
        # type(type_name) is a class 'pyomo.base.sets.SimpleSet'
        # type_name: ('Buy')=>('Elec buy', 'Heat buy')
        return set((stf, sit, com, com_type) for stf, sit, com, com_type
                   in com_tuples if com in type_name)

def op_pro_tuples(pro_tuple, m):
    """ Tuples for operational status of units (processes, transmissions,
    storages) for intertemporal planning.
    Only such tuples where the unit is still operational until the next
    support time frame are valid.
    """
    op_pro = []
    sorted_stf = sorted(list(m.stf))

    for (stf, sit, pro) in pro_tuple:
        for stf_later in sorted_stf:
            index_helper = sorted_stf.index(stf_later)
            if stf_later == max(sorted_stf):
                if (stf_later +
                   m.global_prop.loc[(max(sorted_stf), 'Weight'), 'value'] - 1
                   <= stf + m.process.loc[(stf, sit, pro), 'depreciation']):
                    op_pro.append((sit, pro, stf, stf_later))
            elif (sorted_stf[index_helper+1] <=
                  stf + m.process.loc[(stf, sit, pro), 'depreciation'] and
                  stf <= stf_later):
                op_pro.append((sit, pro, stf, stf_later))
            else:
                pass

    return op_pro

def inst_pro_tuples(m):
    """ Tuples for operational status of already installed units
    (processes, transmissions, storages) for intertemporal planning.
    Only such tuples where the unit is still operational until the next
    support time frame are valid.
    """
    inst_pro = []
    sorted_stf = sorted(list(m.stf))

    for (stf, sit, pro) in m.inst_pro.index:
        for stf_later in sorted_stf:
            index_helper = sorted_stf.index(stf_later)
            if stf_later == max(m.stf):
                if (stf_later +
                   m.global_prop.loc[(max(sorted_stf), 'Weight'), 'value'] - 1
                   < min(m.stf) + m.process.loc[(stf, sit, pro),
                                                'lifetime']):
                    inst_pro.append((sit, pro, stf_later))
            elif (sorted_stf[index_helper+1] <=
                  min(m.stf) + m.process.loc[(stf, sit, pro),
                                             'lifetime']):
                inst_pro.append((sit, pro, stf_later))

    return inst_pro
