import sys
import os
import math
import matplotlib.pyplot as plt
import pandas as pd
import pyomo.environ
import pyomo.core as pyomo
import shutil
import xlrd
from openpyxl import load_workbook
from xlrd import XLRDError
from datetime import datetime

def run_evaluation(input_file, input_pros, pchain):

# In[49]:

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

	def calc_annuity(r, n):
		q = 1 + r
		a = ((q ** n) * (q - 1)) / ((q ** n) - 1)
		return a


	# In[175]:

	def calc_LCOE(invc, fixc, varc, fuelc, co2c, eff, total_eff, FLH, r, n):
		# calculate annuity investment costs
		invc_a = invc * calc_annuity(r, n)
		# calculate LOCE
		LCOE = (((invc_a + fixc) / FLH) + varc + ((fuelc + co2c) / eff)) * (eff / total_eff)
		return LCOE


	# In[161]:

	def calc_result(site, pro, LCOE_reg, LCOE_con, mc):
		
		icost = mprocess.loc[(site, pro), 'inv-cost']
		fixcost = mprocess.loc[(site, pro), 'fix-cost']
		varcost = mprocess.loc[(site, pro), 'var-cost']
		wacc = mprocess.loc[(site, pro), 'wacc']
		dep = mprocess.loc[(site, pro), 'depreciation']
		eff = process_commodity.loc[(pro, mc, 'Out'),'ratio']
		total_eff = float(ratio_out.loc[pro].sum())

		pcom = pro_com.loc[pro, 'Commodity']
		fuelcost = com_price.loc[(site, pcom), 'price']
		if (pro in pchain) & (fuelcost == 0):
			try: fuelcost = LCOE_reg.loc[:, pchain[pchain.index(pro)-1]] 
			except:
				try: fuelcost = LCOE_con.loc[:, pchain[pchain.index(pro)-1]]
				except: 
					try: fuelcost = result_site.loc[:, pchain[pchain.index(pro)-1]]
					except: fuelcost = 0
		
		if pro in ratio_outco2.index:
			co2cost = ratio_outco2.loc[pro, 'ratio']
		else:
			co2cost = 0

		if (com_type.loc[pcom, 'Type'] == "SupIm"):
			FLH = msupim.loc[(site, pcom), 'FLH']
			
			result_reg = calc_LCOE(icost, fixcost, varcost, fuelcost, co2cost, eff, total_eff, FLH, wacc, dep)
			LCOE_reg.append({pro: result_reg, 'FLH': int(FLH)})
			return LCOE_reg

		else:
			FLH = range(1,8761)

			result_con = pd.DataFrame({pro: calc_LCOE(icost, fixcost, varcost, fuelcost, co2cost, eff, total_eff, FLH, wacc, dep)})
			LCOE_con.insert(0, pro, result_con)
			return LCOE_con


	# In[138]:

	def prepare_result_directory():
		""" create a time stamped directory within the result folder """
		# timestamp for result directory
		now = datetime.now().strftime('%Y%m%dT%H%M')

		# create result directory if not existent
		result_name = os.path.splitext(input_file)[0]  # cut away file extension
		result_dir = os.path.join('evaluate_LCOE', '{}-{}'.format(result_name, now))
		if not os.path.exists(result_dir):
			os.makedirs(result_dir)

		return result_dir


	# In[139]:

	def plot_site():
			# plot figure of current site
			
			# initialize x-axis and legend
			hour_con = list(range(1, 8761))
			hour_reg = list(LCOE_reg.index)
			legend = list(result_mc.columns)
			
			# plot reg and con LCOE in one plot
			if len(LCOE_con.columns) != 0:
				plt.plot(hour_con, LCOE_con)
				
			if len(LCOE_reg.columns) != 0:
				plt.plot(hour_reg, LCOE_reg, 'o')
			
			plt.title('LCOE - {}'.format(mc))
			plt.xlabel('hour')
			plt.ylabel('LCOE [€/MWh]')
			plt.xlim([1,8760])
			plt.ylim([0,(result_site.min().max()*3)])
			plt.rcParams['legend.numpoints'] = 1
			plt.legend(legend, fontsize=8)
			
			# save plot of each side to specific path        
			result_dir = prepare_result_directory()  # name + time stamp
			plt.savefig('{}\LCOE_{}_{}.png'.format(result_dir, mc, site), dpi=400)
			plt.close()

	# In[140]:

	def result_export(file):
		
		result_dir = prepare_result_directory()
		
		if os.path.exists('{}\LCOE.xlsx'.format(result_dir, site)):
			with pd.ExcelWriter('{}\LCOE.xlsx'.format(result_dir, site), engine='openpyxl') as writer:
				writer.book = load_workbook('{}\LCOE.xlsx'.format(result_dir, site))
				file.to_excel(writer, sheet_name=site)
		else:
			writer = pd.ExcelWriter('{}\LCOE.xlsx'.format(result_dir, site), engine='xlsxwriter')
			file.to_excel(writer, sheet_name=site)
			writer.save()


	# In[141]:

	def multiindex(columns, mc):
		columns = list(columns)
		column_tuples = [(mc, col) for col in columns]
		return pd.MultiIndex.from_tuples(column_tuples)	

		
	with pd.ExcelFile(input_file) as xls:
		try:
			site = xls.parse('Site').set_index(['Name'])
			commodity = (
				xls.parse('Commodity').set_index(['Site', 'Commodity']))
			process = xls.parse('Process').set_index(['Site', 'Process'])
			process_commodity = (
				xls.parse('Process-Commodity')
				   .set_index(['Process', 'Commodity', 'Direction']))
			transmission = (
				xls.parse('Transmission')
				   .set_index(['Site In', 'Site Out',
							   'Transmission', 'Commodity']))
			storage = (
				xls.parse('Storage').set_index(['Site', 'Storage', 'Commodity']))
			demand = xls.parse('Demand').set_index(['t'])
			supim = xls.parse('SupIm').set_index(['t'])
			buy_sell_price = xls.parse('Buy-Sell-Price').set_index(['t'])
			dsm = xls.parse('DSM').set_index(['Site', 'Commodity'])
		except XLRDError:
			sys.exit("One or more main sheets are missing in your Input-file. Compare it with mimo-example.xlsx!")
		try:
			hacks = xls.parse('Hacks').set_index(['Name'])
		except XLRDError:
			hacks = None

	# prepare input data
	# split columns by dots '.', so that 'DE.Elec' becomes the two-level
	# column index ('DE', 'Elec')
	demand.columns = split_columns(demand.columns, '.')
	supim.columns = split_columns(supim.columns, '.')
	buy_sell_price.columns = split_columns(buy_sell_price.columns, '.')

	data = {
		'site': site,
		'commodity': commodity,
		'process': process,
		'process_commodity': process_commodity,
		'transmission': transmission,
		'storage': storage,
		'demand': demand,
		'supim': supim,
		'buy_sell_price': buy_sell_price,
		'dsm': dsm}
	if hacks is not None:
		data['hacks'] = hacks

	# sort nested indexes to make direct assignments work
	for key in data:
		if isinstance(data[key].index, pd.core.index.MultiIndex):
			data[key].sortlevel(inplace=True)


	# In[50]:

	# get used sites and "main" commoditys
	msites = list(demand.columns.levels[0])
	mcom = list(demand.columns.levels[1])


	# In[164]:

	# get required supim data
	msupim = supim[msites].sum().to_frame().rename(columns={0:'FLH'})

	# get required demand data
	mdemand = demand[msites].sum().to_frame().rename(columns={0:'Demand'})

	# get required process data 
	mpara = ['inv-cost', 'fix-cost', 'var-cost', 'wacc', 'depreciation']
	mprocess = process.loc[msites, mpara]

	# get commodity type - SupIm, Stock
	com_type = commodity.loc[msites, 'Type'].to_frame().reset_index(['Site', 'Commodity'])
	com_type = com_type[(com_type['Type'] == "SupIm") | (com_type['Type'] == "Stock")].fillna(0)
	com_type = com_type.drop(labels=['Site'], axis = 1)
	com_type = com_type.drop_duplicates(['Commodity'], keep='last').set_index('Commodity')
	com = list(com_type.index)
	com2 = mcom + com

	# get required process-commodity data
	ratio_in = process_commodity.loc[(slice(None), com, 'In'), :]['ratio'].to_frame()
	ratio_out = process_commodity.loc[(slice(None), com2, 'Out'), :]['ratio'].to_frame()

	# get processes from input
	pros = list(ratio_in.index.levels[0])
	input_pros = input_pros.split(', ')

	# get related commodity for each process
	pro_com = ratio_in.reset_index(['Direction', 'Commodity']).drop(['Direction', 'ratio'], axis = 1)

	# process chain inputs and intermediate commodity
	pchain = pchain.split(', ')
	if pchain == ['']: x = 0
	else: x = len(pchain)

	# get CO2 ratios
	ratio_outco2 = process_commodity.xs(('CO2', 'Out'), level=['Commodity','Direction'])['ratio'].to_frame()

	# get commodity price
	com_price = commodity.loc[msites, 'price'].to_frame().rename(columns={0:'price'}).fillna(0)


	# In[176]:

	# calculation for commoditys with electricity output
	for site in msites:
		# reset process chain counter for next site
		p = 0
		result_site = pd.DataFrame()
		result_site_suf = pd.DataFrame()    
		
		for mc in mcom:
			# initialize result Dataframe
			LCOE_con = pd.DataFrame()
			LCOE_reg = []
			
			for pro in input_pros:
				if pro not in pros:
					print("{} is not a valid Process! Valid inputs are: {}".format(pro, pros))
					break
				
				elif pro in (mprocess.ix[site].index.get_level_values(0)):     
					if mc in ratio_out.ix[pro].index.get_level_values(0):
						calc_result(site, pro, LCOE_reg, LCOE_con, mc)
						if (p < (x-2)) & (pro in pchain): p = p + 1
					
					elif (pro in pchain[p:x]) & (pchain != ['']):   
						if (pro in pchain[p:x]) & (mc in ratio_out.ix[pchain[p+1]].index.get_level_values(0)):
							calc_result(site, pro, LCOE_reg, LCOE_con, pro_com.get_value(pchain[p+1], 'Commodity'))                
							if p < (x-2): p = p + 1
							
					else:
						continue
			
			if len(LCOE_reg) != 0:
				LCOE_reg = pd.DataFrame(LCOE_reg).set_index('FLH')
			else:
				LCOE_reg = pd.DataFrame()
				
			if len(LCOE_con) != 0:
				LCOE_con.index.name = 'FLH'
			
			# combine results (renewable, conventional processes) of current site 
			result_mc = pd.concat([LCOE_con, LCOE_reg], axis=1)
			result_mc_suf = result_mc.add_suffix('_{}'.format(mc))
			result_site = pd.concat([result_site, result_mc], axis=1)
			result_site_suf = pd.concat([result_site_suf, result_mc_suf], axis=1).fillna(0)
			
			# plot each site as png-file
			if not result_mc.empty:
				plot_site()
		
		# export result of each site to LCOE.xlsx
		result_export(result_site_suf)

	return prepare_result_directory()