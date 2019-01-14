import pandas as pd
    
def identify_mode(data):
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

    # if number of support timeframes > 1
    if len(data['global_prop'].index.levels[0]) > 1:
        mode['int'] = True
    if not data['transmission'].empty:
        mode['tra'] = True
    if not data['storage'].empty:
        mode['sto'] = True
    if not data['dsm'].empty:
        mode['dsm'] = True
    if not data['buy_sell_price'].empty:
        mode['bsp'] = True
    if not data['eff_factor'].empty:
        mode['tve'] = True


    print(mode)
    return mode
