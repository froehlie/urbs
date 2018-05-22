import os
import pandas as pd
import pyomo.environ
import shutil
import urbs
from datetime import datetime
from pyomo.opt.base import SolverFactory

input_file = 'mimo-example.xlsx'
data = urbs.read_excel(input_file)
#print(data)

# Check whether input file has only one site i.e. no transmission constraints are needed
print (data['site'])
size = data['site'].size
no_transmission = None
if size == 1:
	no_transmission = True
	print("We have only one site i.e. no transmission")
else:
	print("We have", size, "sites")

# simulation timesteps
(offset, length) = (3500, 168)  
# time step selection
timesteps = range(offset, offset+length+1)
urbs.validate_input(data)	
# create model
prob = urbs.create_model(data, timesteps)
# print storage and process
"""print(prob.process_dict['inst-cap'])
print(prob.process_dict['cap-up'])
pro_inst_cap = prob.process_dict['inst-cap']
pro_cap_up = prob.process_dict['cap-up']

for key in prob.pro_tuples:
    print(pro_inst_cap[key], pro_cap_up[key])
    if pro_inst_cap[key] < pro_cap_up[key]:
        print("expansion")
    else:
        print("no expansion")

for key in (prob.pro_tuples-prob.pro_tuples_expansion):
    print(pro_inst_cap[key], pro_cap_up[key])
    if pro_inst_cap[key] < pro_cap_up[key]:
        print("expansion")
    else:
        print("no expansion")"""

print(prob.transmission_dict)		

"""sto = prob['storage']
pro = prob['process']
print(sto)
print(pro)

#get data to compare installed capacities to low and up in order to see whether expansion is needed
sto_inst_cap_c = sto['inst-cap-c']
sto_cap_lo_c = sto['cap-lo-c']
sto_cap_up_c = sto['cap-up-c']
sto_inst_cap_p = sto['inst-cap-p']
sto_cap_lo_p = sto['cap-lo-p']
sto_cap_up_p = sto['cap-up-p']
pro_inst_cap = pro['inst-cap']
pro_cap_lo = pro['cap-lo']
pro_cap_up = pro['cap-up']"""

