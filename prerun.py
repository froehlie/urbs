import os
import prerun_core
from tkinter import *
from math import *
from tkinter import messagebox
import tkinter.font as tkFont

class eval:
	def __init__(self, master):
		self.master = master
		self.frame = Frame(self.master)
		self.master.title("Evaluate LCOE")
		# width x height + x_offset + y_offset:
		# self.master.geometry("500x500")
		self.master.resizable(0, 0)
		self.customFont = tkFont.Font(family="Arial", size=9)
		self.input_widgets()
		self.buttons()
		self.directory_path()

	def input_widgets(self):
		# input filename
		Label(self.master, text="Inputfile").grid(sticky=W, column=0, row=0, padx=5, pady=5)
		self.filename = Entry(self.master, width=40, font=self.customFont)
		self.filename.grid(column=1, row=0, padx=5, pady=5)
		self.filename_quote = """mimo-example.xlsx"""
		self.filename.insert(END, self.filename_quote)
		# input processes
		Label(self.master, text="Processes").grid(sticky=W, column=0, row=2, padx=5, pady=5)
		self.pro = Text(self.master, height=4, width=40, font=self.customFont)
		self.pro.grid(column=1, row=2, padx=5, pady=5)
		self.pro_quote = """Hydro plant, Wind park, Photovoltaics, Gas plant"""
		self.pro.insert(END, self.pro_quote)
		# input process chain
		Label(self.master, text="Process chain").grid(sticky=W, column=0, row=3, padx=5, pady=5)
		self.proch = Text(self.master, height=2, width=40, font=self.customFont)
		self.proch.grid(column=1, row=3, padx=5, pady=5)
		
	def buttons(self):
		self.start = Button(self.master, text='Start evaluation', command=self.input_data)
		self.start.grid(row=7, column=0,ipadx=5, padx=5, pady=5)
		self.quit = Button(self.master, text='Quit', command=self.master.quit)
		self.quit.grid(sticky=W, row=7, column=1,ipadx=5, padx=5, pady=5)
		
	def directory_path(self):
		# return path of result directory
		self.path = Label(self.master, anchor=W, justify=LEFT)
		self.path.grid(sticky=W, column=0, columnspan=2, row=5, padx=5, pady=5)
		
	def input_data(self):	
		input_file = str(self.filename.get())
		input_pros = str(self.pro.get('1.0', 'end-1c'))
		pchain = str(self.proch.get('1.0', 'end-1c'))	
		if not os.path.exists(input_file):
			messagebox.showwarning("Open file", "Cannot open this input file\n{}".format(input_file))
		else:
			result_path = prerun_core.run_evaluation(input_file, input_pros, pchain)
			self.path.configure(text="Result directory:\n{}".format(result_path))

def main(): 
    root = Tk()
    app = eval(root)
    root.mainloop()

if __name__ == '__main__':
    main()

