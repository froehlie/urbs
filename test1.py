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

# simulation timesteps
(offset, length) = (3500, 168)  
# time step selection
timesteps = range(offset, offset+length+1)
urbs.validate_input(data)	
# create model
m = urbs.create_model(data, timesteps)

print(m.sto_tuples)
print("p-exp: ",m.sto_tuples_p_expansion,"\n")
print("c-exp: ",m.sto_tuples_c_expansion,"\n")
print("Schnittmenge p-exp und c-exp:")
for s in m.sto_tuples_p_expansion.intersection(m.sto_tuples_c_expansion):
    print(s,"\n")
print("p-exp ohne c-exp:")
for s in m.sto_tuples_p_expansion.difference(m.sto_tuples_c_expansion):
    print(s,"\n")
print("c-exp ohne p-exp:")
for s in m.sto_tuples_c_expansion.difference(m.sto_tuples_p_expansion):
    print(s,"\n")
print("Alle ohne c-exp und p-exp:")
for s in m.sto_tuples-m.sto_tuples_c_expansion-m.sto_tuples_p_expansion:
    print(s,"\n")


"""# print storage and process
print(prob.process_dict['inst-cap'])
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
        print("no expansion")

sto = prob['storage']
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

