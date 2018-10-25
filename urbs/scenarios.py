# SCENARIO GENERATORS
# In this script a variety of scenario generator functions are defined to
# facilitate scenario definitions.

# !IMPORTANT NOTE!
# All texts must be explicitely typed in as a string, e.g. 'Campus'.


def scenario_base(data):
    return data


# Global quantities

def sc_CO2limit(stf, value):
    # Used to set global CO2 limit

    def scenario(data):
        data['global_prop'].loc[(stf, 'CO2 limit'), 'value'] = value
        return data

    scenario.__name__ = 'scenario_CO2-limit-' + '{:04}'.format(value)
    return scenario


def sc_wacc(value):
    # Set wacc

    def scenario(data):
        data['process'].loc[:, 'wacc'] = value
        data['transmission'].loc[:, 'wacc'] = value
        data['storage'].loc[:, 'wacc'] = value
        return data

    scenario.__name__ = 'scenario_wacc-' + '{:03}'.format(value)
    return scenario


# Commodity

def sc_1comprop(stf, site, com, type, property, value):
    # variation of 1 property of 1 given commodity

    def scenario(data):
        data['commodity'].loc[(stf, site, com, type), property] = value
        return data

    scenario.__name__ = ('scenario_' + str(stf) + site + com + property +
                         '{:04}'.format(value)
                         )
    return scenario


def sc_2comprop(stf1, stf2, site1, site2, com1, com2, type1, type2, property1,
                property2, value1, value2):
    # variation of 2 properties of 2 given process

    def scenario(data):
        data['commodity'].loc[(stf1, site1, com1, type1), property1] = value1
        data['commodity'].loc[(stf2, site2, com2, type2), property2] = value2
        return data

    scenario.__name__ = ('scenario_' + str(stf1) + str(stf2) + site1 + com1 +
                         property1 + '{:04}'.format(value1) + site2 + com2 +
                         property2 + '{:04}'.format(value2)
                         )
    return scenario


# Process

def sc_1proprop(stf, site, process, property, value):
    # variation of 1 property of 1 given process

    def scenario(data):
        data['process'].loc[(stf, site, process), property] = value
        return data

    scenario.__name__ = ('scenario_' + str(stf) + site + process + property +
                         '{:04}'.format(value)
                         )
    return scenario


def sc_2proprop(stf1, stf2, site1, site2, process1, process2, property1,
                property2, value1, value2):
    # variation of 2 properties of 2 given process

    def scenario(data):
        data['process'].loc[(stf1, site1, process1), property1] = value1
        data['process'].loc[(stf2, site2, process2), property2] = value2
        return data

    scenario.__name__ = ('scenario_' + str(stf1) + site1 + process1 +
                         property1 + '{:04}'.format(value1) + str(stf2) +
                         site2 + process2 + property2 + '{:04}'.format(value2)
                         )
    return scenario


# Process commodities

def sc_1procomprop(stf, process, com, dir, property, value):
    # variation of 1 property of 1 given process-commodity

    def scenario(data):
        data['process-commodity'].loc[(stf, process, com, dir), property] = value
        return data

    scenario.__name__ = ('scenario_' + str(stf) + process + com + dir +
                         property + '{:04}'.format(value)
                         )
    return scenario


def sc_2procomprop(process1, process2, com1, com2, dir1, dir2, property1,
                   property2, value1, value2):
    # variation of 2 properties of 2 given process-commodity

    def scenario(data):
        data['process-commodity'].loc[(site1, process1), property1] = value1
        data['process-commodity'].loc[(site2, process2), property2] = value2
        return data

    scenario.__name__ = ('scenario_' + process1 + com1 + dir1 + property1 +
                         '{:04}'.format(value1) + process2 + com2 + dir2 +
                         property2 + '{:04}'.format(value2)
                         )
    return scenario


# Storage

def sc_1stoprop(site, sto, com, property, value):
    # variation of 1 property of 1 given storage

    def scenario(data):
        data['storage'].loc[(site, sto, com), property] = value
        return data

    scenario.__name__ = ('scenario_' + site + sto + com + property +
                         '{:04}'.format(value)
                         )
    return scenario


def sc_2stoprop(site1, site2, sto1, sto2, com1, com2, property1,
                property2, value1, value2):
    # variation of 2 properties of 2 given storages

    def scenario(data):
        data['process-commodity'].loc[(site1, sto1, com1), property1] = value1
        data['process-commodity'].loc[(site2, sto2, com2), property2] = value2
        return data

    scenario.__name__ = ('scenario_' + site1 + sto1 + com1 + property1 +
                         '{:04}'.format(value1) + site2 + sto2 + com2 +
                         property2 + '{:04}'.format(value2)
                         )
    return scenario
