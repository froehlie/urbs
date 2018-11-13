import pandas as pd


def identify_mode(filename):
    """ Identify the urbs mode that is needed for running the current xslx file
    
    Minimum mode: only one site, no transmission, no storage, no DSM, no expansion
    optional features:
    Transmission
    Storage
    DSM
    Intertemporal
    Expansion
    
    Args:
        data: a dict of 6 DataFrames with the keys 'commodity', 'process',
            'transmission', 'storage', 'demand' and 'supim'.
    
    Returns:
        result: a bool vector which defines the urbs mode"""

    # create modes
    mode = {
        'tra': False,
        'sto': False,
        'dsm': False,
        'int': False
        }

    with pd.ExcelFile(filename) as xls:
        # Intertemporal mode
        if 'Support timeframe' in xls.parse('Global') \
                                        .set_index('Property').value:
            mode['int'] = True
        # Transmission mode
        if 'Transmission' in xls.sheet_names \
            and not xls.parse('Transmission').set_index(['Site In', 
                            'Site Out', 'Transmission', 'Commodity']).empty:
            mode['tra'] = True
        # Storage mode
        if 'Storage' in xls.sheet_names \
        and not xls.parse('Storage').set_index(['Site', 'Storage', 
                                                'Commodity']).empty:
            mode['sto'] = True
        # Demand side management mode
        if 'DSM' in xls.sheet_names \
        and not xls.parse('DSM').set_index(['Site', 'Commodity']).empty:
            mode['dsm'] = True

    return mode