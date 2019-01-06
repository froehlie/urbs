import pandas as pd


def identify_mode(filename):
    """ Identify the urbs mode that is needed for running the current Input

        The different modes/features are:
            Intertemporal
            Transmission
            Storage
            DSM
            Buy Sell (Price)
            Time Variable efficiency

    Args:
        the input excel file, in case of intertemporal planning the first excel
        file in the Input folder

    Returns:
        mode dictionary: contains bool values that define the urbs mode

    """

    # create modes
    mode = {
        'int': False,   # intertemporal
        'tra': False,   # transmission
        'sto': False,   # storage
        'dsm': False,   # demand site management
        'bsp': False,   # buy sell price
        'tve': False    # time variable efficiency
        }

    with pd.ExcelFile(filename) as xls:
        # Intertemporal mode
        if 'Support timeframe' in xls.parse('Global') \
                                        .set_index('Property').value:
            mode['int'] = True
        # Transmission mode
        if 'Transmission' in xls.sheet_names \
            and not xls.parse('Transmission').set_index(
                ['Site In', 'Site Out', 'Transmission', 'Commodity']).empty:
            mode['tra'] = True
        # Storage mode
        if 'Storage' in xls.sheet_names \
            and not xls.parse('Storage').set_index(
                ['Site', 'Storage', 'Commodity']).empty:
            mode['sto'] = True
        # Demand side management mode
        if 'DSM' in xls.sheet_names \
                and not xls.parse('DSM').set_index(
                ['Site', 'Commodity']).empty:
            mode['dsm'] = True
        # Buy sell price mode
        if 'Buy-Sell-Price' in xls.sheet_names \
                and not xls.parse('Buy-Sell-Price').set_index(['t']).empty:
            mode['bsp'] = True
        if 'TimeVarEff' in xls.sheet_names \
                and not xls.parse('TimeVarEff').set_index(['t']).empty:
            mode['tve'] = True

    return mode
