# -*- encode: utf-8 -*-

from PyQt5 import QtWidgets as qtw, QtCore as qtc, QtGui as qtgui
import design

from strategy import TestStrategy, bt_strategy, make_stats
import bt
from ffn import fmtp

import pandas as pd
import re
from os import makedirs
from os.path import dirname, exists, join
import sys


class HRPApp(qtw.QMainWindow, design.Ui_mainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.startDatePicker.setEnabled(False)
        self.endDatePicker.setEnabled(False)

        self.startDatePicker.setDate(qtc.QDate.currentDate())
        self.endDatePicker.setDate(qtc.QDate.currentDate())

        self.startDateCBox.stateChanged.connect(lambda: self.startDatePicker.setEnabled(self.startDateCBox.checkState()))
        self.endDateCBox.stateChanged.connect(lambda: self.endDatePicker.setEnabled(self.endDateCBox.checkState()))

        self.estPeriodSpin.setMinimum(1)
        self.rollPeriodSpin.setMinimum(1)

        ptypes = ['days', 'weeks', 'months', 'years']
        self.estTypeCombo.addItems(ptypes)
        self.estTypeCombo.setCurrentIndex(0)
        self.rollTypeCombo.addItems(ptypes)
        self.rollTypeCombo.setCurrentIndex(0)

        self._strategies = []
        self.strategyListModel = qtgui.QStandardItemModel()
        self.strategyList.setModel(self.strategyListModel)

        self.dataFileButton.clicked.connect(self.select_data_path)
        self.addStrategyBtn.clicked.connect(self.add_strategy)
        self.removeStrategyBtn.clicked.connect(self.remove_strategy)
        self.reportFileBtn.clicked.connect(self.select_report_dir)

    def select_data_path(self):
        dataPath = qtw.QFileDialog.getOpenFileUrl(self, caption='Select Data File')[0]

        if not dataPath.isEmpty():
            self.dataFileEdit.setText(dataPath.path()[1:])

    def select_report_dir(self):
        dataPath = qtw.QFileDialog.getExistingDirectoryUrl(self, caption='Select directory for report')

        if not dataPath.isEmpty():
            self.reportFileEdit.setText(dataPath.path()[1:])

    def add_strategy(self):
        strategy = TestStrategy()

        strategy.est_plen = self.estPeriodSpin.value()
        strategy.est_ptype = self.estTypeCombo.currentText()
        strategy.roll_plen = self.estPeriodSpin.value()
        strategy.roll_ptype = self.rollTypeCombo.currentText()

        if strategy not in self._strategies:
            self._strategies.append(strategy)
            self.strategyListModel.appendRow(qtgui.QStandardItem(str(strategy)))

    def remove_strategy(self):

        if len(self.strategyList.selectedIndexes()) and self._strategies:
            idx = self.strategyList.selectedIndexes()[0].row()
            del self._strategies[idx]
            self.strategyListModel.removeRow(idx)

    def run_test(self):

        try:
            data = None
            if self.dataFileEdit.text():

                date_column = self.dateColumnEdit.text() if self.dateColumnEdit.text() else 'Date'
                date_format = self.dateFormatEdit.text() if self.dateFormatEdit.text() else '%Y-%m-%d'

                data = pd.read_excel(self.dataFileEdit.text())
                data = data.set_index(pd.DatetimeIndex(pd.to_datetime(data[date_column], format=date_format)))
                data = data.drop(date_column, axis=1)

                data = data.sort_index()
                data = data.fillna(method='pad')

                idxs = None
                if self.startDatePicker.text():
                    idxs = data.index >= self.startDatePicker.text()
                if self.endDatePicker.text():
                    idxs = data.index <= self.endDatePicker.text() if idxs is None else (idxs) & (data.index <= self.endDatePicker.text())
                if idxs is not None:
                    data = data.loc[idxs]

            if len(self._strategies) and data:
                    backtests = [bt_strategy(s, data, float(self.capitalEdit.text())) for s in self._strategies]
                    res = bt.run(*backtests)
                    stats = make_stats(res)
                    bdf = {b.name: pd.concat((b.weights, b.positions, b.turnover), axis=1) for b in backtests}
                    pattern = re.compile('.*>')
                    columns = ['W_' + pattern.sub('', c) for c in backtests[0].weights.columns]
                    columns.extend(['POS_' + pattern.sub('', c) for c in backtests[0].positions.columns])
                    columns.append('Turnover')

                    out_dir = self.reportFileEdit.text() if self.reportFileEdit.text() else dirname(__file__)
                    if not exists(out_dir):
                        makedirs(out_dir)

                    writer = pd.ExcelWriter(join(out_dir, 'hrp_results.xlsx'))
                    stats.to_excel(writer, 'Stats')
                    res.prices.to_excel(writer, 'Prices')
                    res.lookback_returns.applymap(fmtp).to_excel(writer, 'Lookback')
                    for name, df in bdf.items():
                        df.columns = columns
                        df.to_excel(writer, name)

                    writer.save()
            else:
                qtw.QMessageBox.critical(self, "No strategies", "Add strategies")
        except:
            qtw.QMessageBox.critical(self, 'Something wrong T_T', str(sys.exc_info()))