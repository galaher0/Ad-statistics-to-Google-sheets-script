# -*- coding: utf-8 -*-

import tkcalendar as tkc
import tkinter as tk
import yaml
from calendar import monthrange
from collections import OrderedDict
from datetime import date
from loguru import logger
from os import path
from backend import Backend


class Row:
	"""
	Controls widgets relating to a campaign
	"""

	def __init__(self, parent, row_number, has_client_id, init_state=None):

		# Main variables
		self.period = ['Тек. месяц', 'Даты']
		
		self.spent_var = tk.BooleanVar(
			value=(init_state['spent'] if init_state else False)
			)
		self.impressions_var = tk.BooleanVar(
			value=(init_state['impressions'] if init_state else False)
			)
		self.clicks_var = tk.BooleanVar(
			value=(init_state['clicks'] if init_state else False)
			)
		self.reach_var = tk.BooleanVar(
			value=(init_state['reach'] if init_state else False)
			)
		self.views_var = tk.BooleanVar(
			value=(init_state['views'] if init_state else False)
			)
		self.period_var = tk.StringVar(
			value=(init_state['period'] if init_state else self.period[0])
			)
		
		# Widgets
		self.widgets = {
			1: tk.Entry(parent, width=50),
			2: tk.Checkbutton(parent, variable=self.spent_var),
			3: tk.Checkbutton(parent, variable=self.impressions_var),
			4: tk.Checkbutton(parent, variable=self.clicks_var),
			5: tk.Checkbutton(parent, variable=self.reach_var),
			6: tk.Checkbutton(parent, variable=self.views_var),
			7: tk.OptionMenu(parent, self.period_var, *self.period, 
				command=lambda value: self.dates_block_edit(value)),
			8: tkc.DateEntry(parent, date_pattern="dd.mm.y", locale='ru_RU', 
				day=1),
			9: tkc.DateEntry(parent, date_pattern="dd.mm.y", locale='ru_RU', 
				day=self.ldom())
		}

		if has_client_id:
			self.widgets.update({0: tk.Entry(parent, width=50)})

		# Initializing Entry and DateEntry fields
		if init_state:
			self.widgets[1].insert(0, init_state['id'])

			self.widgets[8].set_date(init_state['dates'][0])
			self.widgets[9].set_date(init_state['dates'][1])

			if has_client_id:
				self.widgets[0].insert(0, init_state['client_id'])
				self.widgets[0].config(state='disabled')

			# Disabling editing mode
			for i in range(1, 8):
				self.widgets[i].config(state='disabled')

		self.widgets[8].config(state='disabled')
		self.widgets[9].config(state='disabled')

		self.grid(row_number)

	def dates_block_edit(self, value):
		'''
		Disables editing dates unless a specific option 'Даты' is chosen
		'''
		logger.info(f"Call to block dates editing with {value}")

		self.widgets[8].config(state='normal')
		self.widgets[9].config(state='normal')

		if value == self.period[0]:

			self.widgets[8].set_date(date.today().replace(day = 1))
			self.widgets[9].set_date(date.today().replace(day = self.ldom()))

			self.widgets[8].config(state='disabled')
			self.widgets[9].config(state='disabled')

	def del_placeholder(self, event):
		'''
		Deletes tkinter Entry defualt text on click
		'''
		if self.has_default_text:
			self.widgets[1].delete(0, END)
			self.has_default_text = False

	def get(self):
		'''
		Collects all user entered data
		'''
		return {
			'client_id': self.widgets[0].get().strip() 
				if 0 in self.widgets else None,
			'id': self.widgets[1].get().strip(),
			'spent': self.spent_var.get(),
			'impressions': self.impressions_var.get(),
			'clicks': self.clicks_var.get(),
			'reach': self.reach_var.get(),
			'views': self.views_var.get(),
			'period': self.period_var.get(),
			'dates': [
				self.widgets[8].get_date(),
				self.widgets[9].get_date()
			]
		}	

	def grid(self, row):
		'''Places a Row class object to the particular row in the parent grid'''

		for i in self.widgets:
			if i == 0:
				self.widgets[i].grid(row=row, column=i, sticky='nsew', padx=6, pady=2)
			else:
				self.widgets[i].grid(row=row, column=i, sticky='nsew', pady=2)

	def forget(self):
		'''Removes Row widgets from GUI'''
		for i in self.widgets:
			self.widgets[i].grid_forget()

	def start_column(self):
		'''Returns starting column index'''
		return next(iter(self.widgets))

	def __len__(self):
		'''Returns an index of the last column occupied by a Row'''
		return max(self.widgets.keys())

	def ldom(self):
		'''Returns the last day of the current month'''
		return monthrange(date.today().year, date.today().month)[1]


class ColumnRow:
	'''Displays column names depending on the platform'''

	def __init__(self, parent, has_client_id):
		if not has_client_id:
			self.column_names = [
				"ID кампании", "Потрачено", "Показы", "Клики", 
				"Охват", "Просмотры", "Период", "Начало", "Конец"
			]
			for column_idx in range(len(self.column_names)):
				tk.Label(

					parent, 
					text=self.column_names[column_idx], 
					padx=2, 
					pady=2
				
				).grid(

					row=0, 
					column=column_idx+1, 
					padx=2,
					pady=2,
					sticky='nsew'

				)
			parent.grid_columnconfigure(column_idx, weight=1)
		else:
			self.column_names = [
				"ID клиента", "ID кампании", "Потрачено", "Показы", "Клики", 
				"Охват", "Просмотры", "Период", "Начало", "Конец"
			]
			for column_idx in range(len(self.column_names)):
				tk.Label(

					parent, 
					text=self.column_names[column_idx], 
					padx=2, 
					pady=2
				
				).grid(

					row=0, 
					column=column_idx, 
					padx=2,
					pady=2,
					sticky='nsew'

				)
			parent.grid_columnconfigure(column_idx, weight=1)


class GSpreadWin(tk.Toplevel):
	'''Controls widgets and settings for Google Spreadsheet'''

	def __init__(self, backend_obj, *args, **kwargs):
		super().__init__(*args, **kwargs)
		logger.info("Google Spreadsheet window call")

		self.backend = backend_obj
		
		self.config(padx=10, pady=10)
		self.title("Настройки Google таблицы")
		self.gs_config = self.backend.get_gs_config()

		# MAIN WIDGETS

		self.id_input = tk.Entry(self, width=50)

		self.sheets_dd_var = tk.StringVar(value=self.gs_config.get('sheet_name', ''))

		# column confirm widgets
		self.date_lbl = tk.Label(self, text="Дата")
		self.fb_result_lbl = tk.Label(self, text="Конверсии в FB")
		self.spent_lbl = tk.Label(self, text="Потрачено")
		self.impressions_lbl = tk.Label(self, text="Показы")
		self.clicks_lbl = tk.Label(self, text="Клики")
		self.reach_lbl = tk.Label(self, text="Охват")
		# self.views_lbl = tk.Label(self, text="Просмотры")

		self.date_dd_var = tk.StringVar(value=self.gs_config.get('columns', {'date': {'name': ''}})['date']['name'])
		self.fb_result_dd_var = tk.StringVar(value=self.gs_config.get('columns', {'result': {'name': ''}})['result']['name'])
		self.spent_dd_var = tk.StringVar(value=self.gs_config.get('columns', {'spent': {'name': ''}})['spent']['name'])
		self.impressions_dd_var = tk.StringVar(value=self.gs_config.get('columns', {'impressions': {'name': ''}})['impressions']['name'])
		self.clicks_dd_var = tk.StringVar(value=self.gs_config.get('columns', {'clicks': {'name': ''}})['clicks']['name'])
		self.reach_dd_var = tk.StringVar(value=self.gs_config.get('columns', {'reach': {'name': ''}})['reach']['name'])
		# self.views_dd_var = tk.StringVar(value=self.gs_config.get('columns', {'views': {'name': ''}})['views']['name'])

		# Different flows for known and unknown Google Spreadsheets settings (id, sheet name, columns)
		if 'spreadsheet_id' in self.gs_config:
			
			self.id_lbl = tk.Label(self, text="ID Google таблицы:")
			self.id_lbl.grid(sticky="W", row=1, column=0, pady=2)

			self.id_input.insert(0, self.gs_config['spreadsheet_id'])
			self.id_input.config(state='disabled') 
			self.id_input.grid(sticky="W", row=2, column=0)

			if 'sheet_name' in self.gs_config:
				
				self.sheet_lbl = tk.Label(self, text="Лист:")
				self.sheet_lbl.grid(sticky="W", row=3, column=0, pady=2)

				self.sheets_dd = tk.OptionMenu(self, self.sheets_dd_var, self.gs_config['sheet_name'])
				self.sheets_dd.config(state='disabled')
				self.sheets_dd.grid(sticky="WE", row=4, column=0)

				if 'columns' in self.gs_config:

					self.columns_lbl = tk.Label(self, text="Названия столбцов для каждого показателя:")

					self.date_dd = tk.OptionMenu(self, self.date_dd_var, self.gs_config['columns']['date']['name'])
					self.fb_result_dd = tk.OptionMenu(self, self.fb_result_dd_var, self.gs_config['columns']['result']['name'])
					self.spent_dd = tk.OptionMenu(self, self.spent_dd_var, self.gs_config['columns']['spent']['name'])
					self.impressions_dd = tk.OptionMenu(self, self.impressions_dd_var, self.gs_config['columns']['impressions']['name'])
					self.clicks_dd = tk.OptionMenu(self, self.clicks_dd_var, self.gs_config['columns']['clicks']['name'])
					self.reach_dd = tk.OptionMenu(self, self.reach_dd_var, self.gs_config['columns']['reach']['name'])
					# self.views_dd = tk.OptionMenu(self, self.views_dd_var, self.gs_config['columns']['views']['name'])

					self.grid_column_choice()

				else:

					self.get_columns_names_step()

			else:

				self.id_check_step()

		else:
			self.id_lbl = tk.Label(self, text="Введите ID Google таблицы")
			self.id_lbl.grid(sticky="W", row=1, column=0)

			self.id_input.grid(sticky="W", row=2, column=0, pady=2)

			self.id_confirm_btn = tk.Button(
				self, 
				text="Далее", 
				command=self.id_check_step)
			self.id_confirm_btn.grid(row=2, column=1, padx=5, pady=2)

			self.id_warning_lbl = tk.Label(self, text="Неверный ID")

		self.gs_ok_btn = tk.Button(self, text="OK", command=self.destroy)
		self.gs_ok_btn.grid(row=14, column=0, pady=2)

		self.change_btn = tk.Button(self, text="Изменить", command=self.change_settings)
		self.change_btn.grid(sticky="W", row=14, column=1, pady=2)

	def change_settings(self):
		'''
		Hides all input widgets except for GS id to start GS settings configuration
		all over
		'''
		for row in range(14):
			for col in range(2):
				if self.grid_slaves(row=row, column=col):
					self.grid_slaves(row=row, column=col)[0].grid_forget()

		self.id_lbl = tk.Label(self, text="Введите ID Google таблицы")
		self.id_lbl.grid(sticky="W", row=1, column=0)

		self.id_input.grid(sticky="W", row=2, column=0, pady=2)
		self.id_input.config(state='normal')

		self.id_confirm_btn = tk.Button(
			self, 
			text="Далее", 
			command=self.id_check_step)
		self.id_confirm_btn.grid(row=2, column=1, padx=5, pady=2)

		self.id_warning_lbl = tk.Label(self, text="Неверный ID")

	def id_check_step(self):
		'''Validates user Google Spreadsheet id input and constructs necessary 
		widgets to allow user to input sheet name'''

		self.id_warning_lbl.grid_forget()
		gs_id = self.id_input.get().strip()

		if not gs_id or len(gs_id) < 10:
			self.id_warning_lbl.grid(row=3, column=0, pady=2)
		else:
			self.sheets = self.backend.get_gs_sheets_list(gs_id)
			if self.sheets == 'Error':
				self.id_warning_lbl.grid(row=3, column=0, pady=2)
			else:
				self.id_confirm_btn.grid_forget()
				self.sheet_lbl = tk.Label(self, text="Выберите лист с данными:")
				self.sheet_lbl.grid(row=3, column=0, pady=2)
				
				self.sheets_dd = tk.OptionMenu(self, self.sheets_dd_var, *self.sheets)
				self.sheets_dd.grid(sticky="ew", row=4, column=0, pady=2)
				
				self.sheet_confirm_btn = tk.Button(
					self, 
					text="Далее",
					command=self.get_columns_names_step
				)
				self.sheet_confirm_btn.grid(sticky="W", row=4, column=1, padx=5, pady=2)

	def get_columns_names_step(self):
		'''Gets sheet name input and sends it to backend to receive columns names
		and then constructs widgets to allow user to choose where to store ad indicators'''

		self.sheet_confirm_btn.grid_forget()
		sheet_name = self.sheets_dd_var.get()
		column_list = self.backend.get_columns(sheet_name)

		self.columns_lbl = tk.Label(self, text="Отметьте названия столбцов для каждого показателя:")

		self.date_dd = tk.OptionMenu(self, self.date_dd_var, *column_list)
		self.fb_result_dd = tk.OptionMenu(self, self.fb_result_dd_var, *column_list)
		self.spent_dd = tk.OptionMenu(self, self.spent_dd_var, *column_list)
		self.impressions_dd = tk.OptionMenu(self, self.impressions_dd_var, *column_list)
		self.clicks_dd = tk.OptionMenu(self, self.clicks_dd_var, *column_list)
		self.reach_dd = tk.OptionMenu(self, self.reach_dd_var, *column_list)
		# self.views_dd = tk.OptionMenu(self, self.views_dd_var, *column_list)

		self.grid_column_choice()

		self.confirm_settings_btn = tk.Button(self, text="Подтвердить", command=self.confirm_gs_settings)
		self.confirm_settings_btn.grid(row=14, column=0)

	def grid_column_choice(self):
		'''Grids widgets regarding spreadsheet columns to write settings'''

		self.columns_lbl.grid(sticky="W", row=5, column=0, pady=2)
		
		self.date_lbl.grid(sticky="W", row=6, column=0)
		self.fb_result_lbl.grid(sticky="W", row=7, column=0)
		self.spent_lbl.grid(sticky="W", row=8, column=0)
		self.impressions_lbl.grid(sticky="W", row=9, column=0)
		self.clicks_lbl.grid(sticky="W", row=10, column=0)
		self.reach_lbl.grid(sticky="W", row=11, column=0)
		# self.views_lbl.grid(sticky="W", row=12, column=0)

		self.date_dd.grid(sticky="W", row=6, column=1)
		self.fb_result_dd.grid(sticky="W", row=7, column=1)
		self.spent_dd.grid(sticky="W", row=8, column=1)
		self.impressions_dd.grid(sticky="W", row=9, column=1)
		self.clicks_dd.grid(sticky="W", row=10, column=1)
		self.reach_dd.grid(sticky="W", row=11, column=1)
		# self.views_dd.grid(sticky="W", row=12, column=1)

	def confirm_gs_settings(self):
		'''Action binded to settings confirm button: makes sure that all options 
		are selected by the user and sends input to backend process to store'''

		self.columns_warning_lbl = tk.Label(self, text="Не все столбцы выбраны")
		self.columns_warning_lbl.grid_forget()
		column_choice = {
			'date': self.date_dd_var.get(),
			'result': self.fb_result_dd_var.get(),
			'spent': self.spent_dd_var.get(),
			'impressions': self.impressions_dd_var.get(),
			'clicks': self.clicks_dd_var.get(),
			'reach': self.reach_dd_var.get(),
			# 'views': self.views_dd_var.get()
		}
		if not all(column_choice.values()):
			self.columns_warning_lbl.grid(row=13, column=0)
		else:
			logger.debug(f'column_choice: {column_choice}')
			self.backend.send_column_choice(column_choice)
			tk.Label(self, text="Настройки сохранены").grid(row=12, column=0)
			self.confirm_settings_btn.grid_forget()


class Limitations(tk.Toplevel):
	'''Contains necessary info about current program limitations and assumptions'''

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.config(padx=10, pady=10)
		self.title("Ограничения программы")
		tk.Label(self, text="- После первого запуска с данной кампанией нельзя менять ее ряд в Гугл таблице").pack()
		tk.Label(self, text="- Если столбцы меняются местами, нужно заново пройти процесс настройки Гугл таблицы").pack()
		tk.Label(self, text="- Если нет инета, прога не запустится").pack()
		tk.Label(self, text="- Программа предполагает, что названия столбцов находятся в первом ряду Гугл таблицы").pack()
		tk.Label(self, text="- Пользователь должен быть авторизован на всех платформах в бразузере Google Chrome").pack()


class Results_window(tk.Toplevel):
	'''Shows result of ad parsing to the user'''

	def __init__(self, ad_data, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.config(padx=10, pady=10)
		self.title("Результаты работы программы")

		self.column_names = [
				"ID кампании", "Конверсии", "Потрачено", "Показы", 
				"Клики", "Охват", 
				# "Просмотры"
			]
		tk.Label(
			self, text="Данные, записанные в Google таблицу:"
		).grid(row=0, column=0, columnspan=len(self.column_names))
		for idx, name in enumerate(self.column_names):
			tk.Label(
				self, text=name, padx=2, pady=2
			).grid(
				row=1, column=idx+1, padx=2, pady=2, sticky='nsew'
			)

		col_n = {
			'result': 2,
			'spent': 3,
			'impressions': 4,
			'clicks': 5,
			'reach': 6,
			# 'views': 7
		}

		row_count = 2
		for pf_name in ad_data:
			if ad_data[pf_name]:
				n = len(ad_data[pf_name])
				tk.Label(
					self, text=pf_name
				).grid(row=row_count, column=0, rowspan=n)
				for camp_id in ad_data[pf_name]:
					tk.Label(self, text=camp_id).grid(row=row_count, column=1)
					for indicator in ad_data[pf_name][camp_id]:
						tk.Label(
							self, text=ad_data[pf_name][camp_id][indicator]
						).grid(row=row_count, column=col_n[indicator])
					row_count += 1

		self.ok_btn = tk.Button(self, text="OK", width=20, command=self.destroy)
		self.ok_btn.grid(row=row_count, column=0, columnspan=len(self.column_names), pady=2)


class PlatformFrame(tk.Frame):
	'''Controls widgets relating to a particular Ad Platform'''

	def __init__(self, *args, name, row, init_states=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.configure(bg='grey')
		self.columnconfigure((0,1), weight=1)
		self.name = name

		# Whether it is needed to display additional Client ID column
		self.has_client_id = True if name in ['Facebook', 'MyTarget'] else False

		self.DEL_BTN_COL = 10

		# Frame with Platform Name
		self.name_frame = tk.Frame(self)
		tk.Label(self.name_frame, text=self.name, 
			padx=2, pady=2).pack(padx=2, pady=2, expand=True)
		self.name_frame.grid(row=0, column=0, sticky='nsew', padx=2)

		# Frame with Campaign Rows
		self.rows_frame = tk.Frame(self)
		ColumnRow(self.rows_frame, self.has_client_id)

		self.campaigns = OrderedDict()

		if init_states:
			for i, init_state in enumerate(init_states):
				self.campaigns[i+1] = Row(self.rows_frame, i+1, self.has_client_id, 
											init_state=init_state)
				tk.Button(
					
					self.rows_frame, 
					text='Удалить', 
					command=lambda x=i+1: self.delete_row(x)
				
				).grid(row=i+1, column=self.DEL_BTN_COL)

		tk.Button(

			self.rows_frame, 
			text=f'Добавить кампанию {self.name}', 
			command=self.append_row

		).grid(
				
			row=1+len(self.campaigns), 
			column=0, 
			columnspan=self.DEL_BTN_COL, 
			sticky="nsew", 
			pady=2
			
		)

		self.rows_frame.grid(row=0, column=1, sticky="nsew")
		# Gridding Frames immedeately on initialization
		self.grid(row=row, column=0, sticky="nsew", pady=2, padx=2)

	def append_row(self):
		'''
		Creates data container and widgets for newly added campaign row
		'''
		logger.info(f"Appending row to {self.name}")

		last_key = next(reversed(self.campaigns)) if self.campaigns else 0
		columns, rows = self.rows_frame.grid_size()
		if rows-1 == last_key+1:
			self.rows_frame.grid_slaves(row=last_key+1, column=0)[0].grid_forget()
		self.campaigns[last_key+1] = Row(self.rows_frame, last_key+1, self.has_client_id)
		tk.Button(
					
			self.rows_frame, 
			text='Удалить', 
			command=lambda x=last_key+1: self.delete_row(x)
		
		).grid(row=last_key+1, column=self.DEL_BTN_COL)

		if rows-1 == last_key+1:
			tk.Button(

				self.rows_frame, 
				text=f'Добавить кампанию {self.name}', 
				command=self.append_row

			).grid(
					
				row=last_key+2, 
				column=0, 
				columnspan=self.DEL_BTN_COL, 
				sticky="nsew", 
				pady=2
				
			)

	def delete_row(self, row):
		'''
		Deletes data container and widgets for unnecessary campaign row
		'''
		logger.info(f"Deleting {row} row in {self.name} block")

		self.campaigns[row].forget()
		self.rows_frame.grid_slaves(row=row, column=self.DEL_BTN_COL)[0].grid_forget()
		self.campaigns.pop(row)

	def get(self):
		'''
		Collects data from all Platforms rows
		'''
		return {
			self.name: [self.campaigns[i].get() for i in self.campaigns]
		}


class Program(tk.Tk):
	"""
	Main GUI container
	"""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# MENU AND APPEARANCE SETUP
		logger.info("GUI init")
		self.title("Auto Basya")
		self.configure(bg="grey")
		self.columnconfigure((0,), weight=1)
		self.main_menu = tk.Menu(self)
		self.config(menu=self.main_menu)
		self.options_menu = tk.Menu(self.main_menu, tearoff=0)
		self.set_options_menu()

		self.backend = Backend()
		
		# MAIN VARIABLES
		
		self.pf_names = self.backend.get_pf_names()
		self.pf_count = len(self.pf_names)
		
		self.path_to_config = 'campaigns_config.yml'

		self.input_data = self.load_config()

		self.rows = {
			pf: row for row, pf in enumerate(self.pf_names)
		}
		self.vars = {
			pf: tk.BooleanVar(value=(pf in self.input_data)) 
			for pf in self.pf_names
		}
		self.frames = {
			pf: PlatformFrame(self, name=pf, row=self.rows[pf], init_states=self.input_data[pf])
			for pf in self.input_data
		}

		# WELCOME MESSAGE
		self.welcome_lbl = None
		if not self.input_data:
			logger.info('Welcome Message')
			self.welcome_lbl = tk.Label(
				self,
				text=u"Добро пожаловать в Авто Басю.\n\nПохоже, что это первый запуск программы (либо не было сохранено ни одной кампании).\n\nЧтобы приступить к работе, зайдите в\nНастройки > Платформы,\nчтобы выбрать платформы, с которыми предстоит работать, а также в\nНастройки > Google Таблица\nчтобы внести параметры Google таблицы, в которую предстоит экспортировать данные.", 
				padx=10, pady=10
			)
			self.welcome_lbl.grid(row=0, column=0, padx=20, pady=30)
		
		# must be in the end of init
		self.set_footer()

	def set_options_menu(self):
		'''
		Options menu setup
		'''
		logger.info("options menu setup")

		self.main_menu.add_cascade(label="Настройки", menu=self.options_menu)
		self.options_menu.add_command(label="Платформы", 
			command=self.pf_window)
		self.options_menu.add_command(label="Google Таблица", 
			command=lambda: GSpreadWin(self.backend))
		self.options_menu.add_command(label="Ограничения", 
			command=Limitations)

	def pf_window(self):
		'''
		Open platforms' checklist setting window
		'''
		logger.info("platforms window call")
		
		pf_window = tk.Toplevel(padx=10, pady=10)
		pf_window.title("Платформы")
		
		# Subject to change to grid
		tip = tk.Label(pf_window, 
			text="Отметьте галочкой платформы, \nиз которых требуется экспортировать данные"
			).pack()

		pf_checkboxes = tk.Frame(pf_window)

		MAX_ROWS = 8
		i = 0
		for column in range(8):
			if i < self.pf_count:
				for row in range(MAX_ROWS):
					if i < self.pf_count:
						tk.Checkbutton(
							pf_checkboxes, 
							text=self.pf_names[i],
							variable=self.vars[self.pf_names[i]],
							command=lambda x=self.pf_names[i]: self.show_hide_pf(x),
						).grid(sticky="w", row=row, column=column)
						i += 1

		pf_checkboxes.pack(fill='both', expand=True)

		platforms_ok_btn = tk.Button(
			pf_window, 
			text="OK", 
			command=pf_window.destroy
			).pack(pady=10)

	def show_hide_pf(self, pf):
		'''
		Clears table for info inserting from widgets
		'''
		if self.vars[pf].get():
			logger.info(f"Call to create {pf} frame")
			if self.welcome_lbl:
				self.welcome_lbl.grid_forget()
			self.frames.update({pf: PlatformFrame(self, name=pf, row=self.rows[pf])})
		else:
			logger.info(f"Call to delete {pf} frame")
			self.frames[pf].grid_forget()
			self.frames.pop(pf)

	def save_values(self):
		'''
		Saves entered info to internal dict
		'''
		logger.info('Call to save input')
		self.input_data.clear()
		for pf in self.pf_names:
			if self.vars[pf].get():
				self.input_data.update(self.frames[pf].get())
		logger.info(f'Input {self.input_data} saved to internal dict')

	def save_config(self):
		'''Saves campaign parsing parameters to disk'''

		logger.info('Call to save config file')
		with open(self.path_to_config, 'w', encoding='utf-8') as f:
			yaml.dump(self.input_data, f, allow_unicode=True)
		logger.info('Input saved to disk')

	def load_config(self):
		'''Loads campaign parsing parameters'''

		logger.info('Call to load config')
		if path.exists(self.path_to_config):
			with open(self.path_to_config, 'r', encoding='utf-8') as y:
				conf = yaml.safe_load(y)
			logger.info(f'Config loaded {conf}')
			return conf
		logger.info('Returning empty config')
		return {}

	def set_footer(self):
		'''
		Sets up footer of the GUI with two buttons
		'''
		
		self.footer = tk.Frame(self)
		save_start_btn = tk.Button(self.footer, text="Сохранить и Запустить",
			command=self.save_start_process_btn, padx=5)
		save_btn = tk.Button(self.footer, text="Сохранить",
			command=self.save_btn, padx=5)
		save_btn.grid(row=0, column=1, sticky='E', padx=5, pady=10)
		save_start_btn.grid(row=0, column=2, sticky='E', padx=5, pady=10)
		self.footer.columnconfigure((0,), weight=1)
		self.footer.grid(row=self.pf_count, column=0, pady=2, sticky='nsew') 

	def set_progress_bar(self):
		'''
		Sets up progress bar to track the execution of the main process 
		in the backend
		'''
		# TO DO
		pass

	def save_start_process_btn(self):
		logger.info('Saving values to dict and to disk')
		self.save_values()
		self.save_config()
		self.set_progress_bar()
		logger.info('Running main backend process')
		logger.debug(f"Data given to backend: {self.input_data}")
		self.gs_warning = tk.Label(self.footer, text="Не заданы настройки Google таблицы")
		if self.backend.gs_setting_complete():
			self.gs_warning.grid_forget()
			self.backend.run(self.input_data)
		else:
			self.gs_warning.grid(row=0, column=0, sticky='E', padx=5, pady=10)

		Results_window(self.backend.get_result())

	def save_btn(self):
		logger.info('Saving values to dict and to disk')
		self.save_values()
		self.save_config()

	def run(self):
		self.mainloop()
