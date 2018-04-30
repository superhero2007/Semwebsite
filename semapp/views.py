from .mixins import GroupRequiredMixin

# Create your views here.
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

DataDir = 'semapp/data'

# for debug
# class APIView(object):
#  pass
# DataDir = 'data'

import datetime, time
import pandas as pd
import sys, os
import numpy as np
from pandas.tseries.offsets import BDay
import scipy.stats

EnterLong = 0.57
EnterShort = 0.43


class TradingView(GroupRequiredMixin, APIView):
    group_required = ['trading']
    def get(self, request, format=None):
        ah = pd.read_hdf(os.path.join(DataDir, 'account_history.hdf'), 'table')
        ah['Portfolio_daily_return'] = ah.PnlReturn
        ah['Portfolio_equity_curve'] = (1 + ah.CumPnl)

        benchmarks = [('SP500', 'S&P5'), ('SP400', 'SPMC'), ('SP600', 'S&P6')]

        for b, m_ticker in benchmarks:
            b_data = pd.read_hdf(os.path.join(DataDir, b + '.hdf'), 'table')
            ah[b + '_daily_return'] = ah.TradeDate.map(b_data.adj_close.pct_change())
            ah[b + '_equity_curve'] = (1 + ah[b + '_daily_return']).cumprod()

        stats_cols = ['Portfolio'] + [x[0] for x in benchmarks]
        stats = pd.DataFrame(columns=stats_cols)

        for c in stats_cols:
            daily_ret = ah[c + '_daily_return']
            stats.loc['Cumulative Return (bps)', c] = "{0:.0f}".format((ah[c + '_equity_curve'].iloc[-1] - 1) * 10000)
            stats.loc['Winning Days (%)', c] = "{0:.0%}".format((daily_ret > 0).mean())
            stats.loc['Min Return (bps)', c] = "{0:.0f}".format(daily_ret.min() * 10000)
            stats.loc['Max Return (bps)', c] = "{0:.0f}".format(daily_ret.max() * 10000)
            stats.loc['Mean Return (bps)', c] = "{0:.0f}".format(daily_ret.mean() * 10000)
            stats.loc['Std Dev Return (bps)', c] = "{0:.0f}".format(daily_ret.std() * 10000)
            stats.loc['Skew', c] = "{0:.1f}".format(scipy.stats.skew(daily_ret))
            stats.loc['Kurtosis', c] = "{0:.1f}".format(scipy.stats.kurtosis(daily_ret))
            stats.loc['Volatility - Annualized (%)', c] = "{0:.1%}".format(np.sqrt(252) * daily_ret.std())
            stats.loc['Sharpe - Annualized', c] = "{0:.1f}".format(np.sqrt(252) * daily_ret.mean() / daily_ret.std())
            stats.loc['Sortino - Annualized', c] = "{0:.1f}".format(
                np.sqrt(252) * daily_ret.mean() / daily_ret.clip(upper=0).std())
            drawdown_series, max_drawdown, drawdown_dur = self.create_drawdowns(ah[c + '_equity_curve'])
            stats.loc['Max Drawdown (bps)', c] = "{0:.0f}".format(max_drawdown * 10000)
            stats.loc['Max Drawdown Days', c] = "{0:.0f}".format(drawdown_dur)
        stats.index.name = 'Metric'

        StartingDate = ah.TradeDate.iloc[0]
        EndingDate = ah.TradeDate.iloc[-1]

        # convert timestamp to timetuple
        ah['TradeDate'] = ah['TradeDate'].apply(lambda x: time.mktime(x.timetuple()))

        stats.reset_index(inplace=True)

        # build context
        context = {'StartingDate': StartingDate.strftime("%m/%d/%Y"),
                   'EndingDate': EndingDate.strftime("%m/%d/%Y"),
                   'StartingNAV': '${:,}'.format(int(round(ah.SOD_Nav.iloc[0], 0))),
                   'EndingNAV': '${:,}'.format(int(round(ah.EOD_Nav.iloc[-1], 0))),
                   'TimeWeightedReturn': '{:.2%}'.format(ah.Portfolio_equity_curve.iloc[-1] - 1),
                   'chart_data_strategy': ah[['TradeDate', 'Portfolio_equity_curve']].values.tolist(),
                   'chart_data_benchmark': ah[['TradeDate', 'SP500_equity_curve']].values.tolist(),
                   'benchmark_name': 'SP500',
                   'stats': stats.to_dict(orient='records'),
                   'file_type': "html",
                   "title": "Dashboard"}

        return Response(context)

    def create_drawdowns(self, returns):
        # Calculate the cumulative returns curve
        # and set up the High Water Mark
        hwm = [0]

        # Create the drawdown and duration series
        idx = returns.index
        drawdown = pd.Series(index=idx)
        duration = pd.Series(index=idx)

        # Loop over the index range
        for t in range(1, len(idx)):
            hwm.append(max(hwm[t - 1], returns.ix[t]))
            drawdown.ix[t] = (hwm[t] - returns.ix[t]) / hwm[t]
            duration.ix[t] = (0 if drawdown.ix[t] == 0 else duration.ix[t - 1] + 1)

        return drawdown, drawdown.max(), duration.max()


class TradingExposuresView(GroupRequiredMixin,APIView):
    group_required = ['trading']
    def get(self, request, format=None):
        ## ticker matching doesn't work well. Needs to be converted to CUSIP
        pos = pd.read_hdf(os.path.join(DataDir, 'nav_portfolio.hdf'), 'table')
        pos.Symbol = pos.Symbol.str.replace(' US', '')

        sm = pd.read_hdf(os.path.join(DataDir, 'sec_master.hdf'), 'table')
        sm.ticker = sm.ticker.str.replace('.', '/')

        pos = pos.merge(sm, left_on='Symbol', right_on='ticker', how='left')
        daily_nav = pos.groupby('TradeDate').MarketValueBase.sum()

        pos['nav'] = pos.TradeDate.map(daily_nav)

        #######NEED TO FIX CASH ############
        pos['weight'] = pos.MarketValueBase / pos.nav
        pos['weight_abs'] = pos.weight.abs()

        gross_ind = pos.groupby(['TradeDate', 'zacks_x_sector_desc', 'zacks_m_ind_desc']).weight_abs.sum().to_frame(
            'Gross')
        net_ind = pos.groupby(['TradeDate', 'zacks_x_sector_desc', 'zacks_m_ind_desc']).weight.sum().to_frame(
            'Net_unadj')
        net_ind = net_ind.join(gross_ind)
        net_ind['Net'] = net_ind['Net_unadj'] / net_ind['Gross']
        net_ind['Net - 1wk delta'] = net_ind.groupby(level=['zacks_x_sector_desc', 'zacks_m_ind_desc'])['Net'].diff(5)
        net_ind['Net - 1mo delta'] = net_ind.groupby(level=['zacks_x_sector_desc', 'zacks_m_ind_desc'])['Net'].diff(20)
        net_ind.reset_index(level=['zacks_x_sector_desc', 'zacks_m_ind_desc'], drop=False, inplace=True)

        gross_sec = pos.groupby(['TradeDate', 'zacks_x_sector_desc']).weight_abs.sum().to_frame('Gross')
        net_sec = pos.groupby(['TradeDate', 'zacks_x_sector_desc']).weight.sum().to_frame('Net_unadj')
        net_sec = net_sec.join(gross_sec)
        net_sec['Net'] = net_sec['Net_unadj'] / net_sec['Gross']
        net_sec['Net - 1wk delta'] = net_sec.groupby(level=['zacks_x_sector_desc'])['Net'].diff(5)
        net_sec['Net - 1mo delta'] = net_sec.groupby(level=['zacks_x_sector_desc'])['Net'].diff(20)
        net_sec.reset_index(level=['zacks_x_sector_desc'], drop=False, inplace=True)
        net_sec['zacks_m_ind_desc'] = 'All'

        max_date = pos.TradeDate.max()

        exposures = pd.concat([net_ind.loc[max_date], net_sec.loc[max_date]], ignore_index=True)
        exposures = exposures.drop('Net_unadj', axis=1)

        # build context
        context = {'data': exposures.to_dict(orient='records')}

        return Response(context)


class SignalsLatestView(APIView):
    def get(self, request, format=None):
        filepath = os.path.join(DataDir, 'equities_signals_latest.hdf')
        signals = pd.read_hdf(filepath, 'table')

        # build context
        context = {'data': signals.to_dict(orient='records')}

        return Response(context)


class SignalsSecIndView(APIView):
    def get(self, request, format=None):
        filepath = os.path.join(DataDir, 'equities_signals_sec_ind.hdf')
        signals = pd.read_hdf(filepath, 'table')
        context = {'data': signals.to_dict(orient='records')}
        return Response(context)


class SignalsSectorTableView(APIView):
    def post(self, request, format=None):
        sector = request.data['sector']
        filepath = os.path.join(DataDir, 'equities_signals_full.hdf')
        signals = pd.read_hdf(filepath, 'table', where='zacks_x_sector_desc=="%s"' % sector)
        # build context
        context = {'data': signals.to_dict(orient='records')}

        return Response(context)


class SignalsIndustryTableView(APIView):
    def post(self, request, format=None):
        industry = request.data['industry']
        filepath = os.path.join(DataDir, 'equities_signals_full.hdf')
        signals = pd.read_hdf(filepath, 'table', where='zacks_m_ind_desc=="%s"' % industry)
        # build context
        context = {'data': signals.to_dict(orient='records')}
        return Response(context)


class SignalsTickerView(APIView):
    def post(self, request, format=None):
        ticker = request.data['ticker']
        filepath = os.path.join(DataDir, 'equities_signals_full.hdf')
        ticker = ticker.upper()
        signal_data_columns = ['data_date', 'market_cap', 'ticker', 'zacks_x_sector_desc', 'zacks_m_ind_desc', 'close',
                               'adj_close', 'SignalConfidence']

        signals = pd.read_hdf(filepath, 'table', where='ticker=="%s"' % ticker)[signal_data_columns]

        ## Check if stacked signal data exists
        if (not (len(signals))):
            return Response({'data': None})

        # build context
        context = {'data': signals.to_dict(orient='records')}

        return Response(context)

class CorrelationView(APIView):
    def get(self, request, aggregation, lookback, corr_threshold, graph=True, format=None):
        if not graph:
            dislocations = pd.read_csv(DataDir+'/correlation_network_files/dislocations_'+str(aggregation)+'minute_' + lookback + '_lookback.csv')
            dislocations = dislocations[dislocations.weight>=corr_threshold].reset_index(drop=True)

            dislocations = dislocations[['ticker1', 'ticker2', 'weight',
                                         'comp1_H_1day_abs_return', 'comp2_H_1day_abs_return','delta_1day',
                                         'comp1_H_3day_abs_return', 'comp2_H_3day_abs_return','delta_3day',
                                         'comp1_H_5day_abs_return', 'comp2_H_5day_abs_return','delta_5day']]
            
            context = {'data': dislocations.to_dict(orient='records')}
            return Response(context)

        df_corrmat = pd.read_csv('./correlation_network_files/corr_matrix_'+str(aggregation)+'minute_' + lookback + '_lookback.csv').set_index(keys=['Unnamed: 0'], drop=True)
        df_nodes = pd.read_csv('./correlation_network_files/node_info.csv')

        node_list = pd.DataFrame(df_corrmat.index.tolist()).reset_index(drop=False).rename(columns={'index':'node_id',0:'ticker'})

        df_list = df_corrmat.unstack()

        df_list = pd.DataFrame(df_list, columns=['weight'])
        df_list.index.names = ['ticker1','ticker2']
        df_list = df_list.reset_index(drop=False)    

        df_list = df_list[df_list.weight!=1].copy()

        df_list = pd.merge(df_list, node_list, left_on=['ticker1'], right_on=['ticker'], how='outer').drop(labels=['ticker1','ticker'], axis=1).rename(columns={'node_id':'node1'})
        df_list = pd.merge(df_list, node_list, left_on=['ticker2'], right_on=['ticker'], how='outer').drop(labels=['ticker2','ticker'], axis=1).rename(columns={'node_id':'node2'})
        df_list = df_list[['node1','node2','weight']].copy()

        df_list = df_list[(df_list.weight>=corr_threshold) | (df_list.weight<=-1*corr_threshold)].copy()

        edge_list = df_list[['node1','node2']].values.tolist()

        g = igraph.Graph()

        g.add_vertices(node_list.node_id.max()+1)
        g.add_edges(edge_list)
        weight_list = [abs(i) for i in df_list.weight.tolist()]
        g.es['weight'] = weight_list

        mst_edge_ids = g.spanning_tree(weights=weight_list, return_tree=False)
        mst_edges_list = [g.get_edgelist()[i] for i in mst_edge_ids]
        mst_edges_weights = [g.es['weight'][i] for i in mst_edge_ids]

        mst_edges = pd.DataFrame(mst_edges_list, columns=['node1','node2'])
        mst_edges = pd.merge(mst_edges, pd.DataFrame(mst_edges_weights, columns=['weight']), left_index=True, right_index=True)

        mst_edges = pd.merge(mst_edges, node_list, left_on='node1', right_on='node_id').drop(labels=['node_id','node1'], axis=1)
        mst_edges = pd.merge(mst_edges, node_list, left_on='node2', right_on='node_id').drop(labels=['node_id','node2'], axis=1)

        mst_edges = mst_edges.rename(columns={'ticker_x':'ticker1','ticker_y':'ticker2'})
        mst_edges = mst_edges[['ticker1','ticker2','weight']].copy()

        # mst_edges = pd.merge(mst_edges, df_nodes, left_on='ticker1', right_on='ticker').rename(columns={'comp_name':'comp_name1','Sector':'comp1_sector','Industry':'comp1_industry','Industry Group':'comp1_industry_group'}).drop(labels=['ticker'], axis=1)

        # mst_edges = pd.merge(mst_edges, df_nodes, left_on='ticker2', right_on='ticker').rename(columns={'comp_name':'comp_name2','Sector':'comp2_sector','Industry':'comp2_industry','Industry Group':'comp2_industry_group'}).drop(labels=['ticker'], axis=1)

        mst_nodes = list(set(mst_edges.ticker1.unique().tolist() + mst_edges.ticker2.unique().tolist()))
        mst_nodes = df_nodes[df_nodes.ticker.isin(mst_nodes)].reset_index(drop=True)

        # mst_edges.to_csv('./sp500_mst_edges_minute.csv', index=False)
        # mst_nodes.to_csv('./sp500_mst_nodes_minute.csv', index=False)

        return([mst_edges,mst_nodes])


class NetworkView(APIView):
    def get(self, request, format=None):
        data = {
            'my_nodes': [
                {
                    "Sector": "Computer and Technology",
                    "name": "AGILENT TECH",
                    "title": "Name: AGILENT TECH<br>Sec: Computer and Technology<br> ind: Electronics",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronics",
                    "label": "A",
                    "y": 1,
                    "x": 1,
                    "id": 1
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "METTLER-TOLEDO",
                    "title": "Name: METTLER-TOLEDO<br>Sec: Computer and Technology<br> ind: Miscellaneous Technology",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Miscellaneous Technology",
                    "label": "MTD",
                    "radius": 10,
                    "y": 2,
                    "x": 2,
                    "id": 2
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "WATERS CORP",
                    "title": "Name: WATERS CORP<br>Sec: Computer and Technology<br> ind: Miscellaneous Technology",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Miscellaneous Technology",
                    "label": "WAT",
                    "radius": 10,
                    "y": 4,
                    "x": 4,
                    "id": 4
                },
                {
                    "Sector": "Medical",
                    "name": "THERMO FISHER",
                    "title": "Name: THERMO FISHER<br>Sec: Medical<br> ind: Medical Products",
                    "color": {
                        "background": "PaleGoldenRod"
                    },
                    "industry": "Medical Products",
                    "label": "TMO",
                    "y": 5,
                    "x": 5,
                    "id": 5
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "PERKINELMER INC",
                    "title": "Name: PERKINELMER INC<br>Sec: Computer and Technology<br> ind: Miscellaneous Technology",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Miscellaneous Technology",
                    "label": "PKI",
                    "y": 7,
                    "x": 7,
                    "id": 7
                },
                {
                    "Sector": "Transportation",
                    "name": "AMER AIRLINES",
                    "title": "Name: AMER AIRLINES<br>Sec: Transportation<br> ind: Air Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Air Transportation",
                    "label": "AAL",
                    "y": 9,
                    "x": 9,
                    "id": 9
                },
                {
                    "Sector": "Transportation",
                    "name": "ALASKA AIR GRP",
                    "title": "Name: ALASKA AIR GRP<br>Sec: Transportation<br> ind: Air Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Air Transportation",
                    "label": "ALK",
                    "radius": 10,
                    "y": 10,
                    "x": 10,
                    "id": 10
                },
                {
                    "Sector": "Transportation",
                    "name": "SOUTHWEST AIR",
                    "title": "Name: SOUTHWEST AIR<br>Sec: Transportation<br> ind: Air Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Air Transportation",
                    "label": "LUV",
                    "radius": 10,
                    "y": 12,
                    "x": 12,
                    "id": 12
                },
                {
                    "Sector": "Transportation",
                    "name": "UNITED CONT HLD",
                    "title": "Name: UNITED CONT HLD<br>Sec: Transportation<br> ind: Air Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Air Transportation",
                    "label": "UAL",
                    "radius": 10,
                    "y": 14,
                    "x": 14,
                    "id": 14
                },
                {
                    "Sector": "Transportation",
                    "name": "DELTA AIR LINES",
                    "title": "Name: DELTA AIR LINES<br>Sec: Transportation<br> ind: Air Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Air Transportation",
                    "label": "DAL",
                    "radius": 10,
                    "y": 16,
                    "x": 16,
                    "id": 16
                },
                {
                    "Sector": "Medical",
                    "name": "AMERISOURCEBRGN",
                    "title": "Name: AMERISOURCEBRGN<br>Sec: Medical<br> ind: Medical Products",
                    "color": {
                        "background": "PaleGoldenRod"
                    },
                    "industry": "Medical Products",
                    "label": "ABC",
                    "y": 17,
                    "x": 17,
                    "id": 17
                },
                {
                    "Sector": "Medical",
                    "name": "CARDINAL HEALTH",
                    "title": "Name: CARDINAL HEALTH<br>Sec: Medical<br> ind: Medical Products",
                    "color": {
                        "background": "PaleGoldenRod"
                    },
                    "industry": "Medical Products",
                    "label": "CAH",
                    "radius": 10,
                    "y": 18,
                    "x": 18,
                    "id": 18
                },
                {
                    "Sector": "Medical",
                    "name": "MCKESSON CORP",
                    "title": "Name: MCKESSON CORP<br>Sec: Medical<br> ind: Medical Products",
                    "color": {
                        "background": "PaleGoldenRod"
                    },
                    "industry": "Medical Products",
                    "label": "MCK",
                    "radius": 10,
                    "y": 20,
                    "x": 20,
                    "id": 20
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "ANALOG DEVICES",
                    "title": "Name: ANALOG DEVICES<br>Sec: Computer and Technology<br> ind: Electronic/Semiconductors",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronic/Semiconductors",
                    "label": "ADI",
                    "y": 21,
                    "x": 21,
                    "id": 21
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "SKYWORKS SOLUTN",
                    "title": "Name: SKYWORKS SOLUTN<br>Sec: Computer and Technology<br> ind: Telecomm Equipment",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Telecomm Equipment",
                    "label": "SWKS",
                    "radius": 10,
                    "y": 22,
                    "x": 22,
                    "id": 22
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "MICROCHIP TECH",
                    "title": "Name: MICROCHIP TECH<br>Sec: Computer and Technology<br> ind: Electronic/Semiconductors",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronic/Semiconductors",
                    "label": "MCHP",
                    "y": 23,
                    "x": 23,
                    "id": 23
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "QORVO INC",
                    "title": "Name: QORVO INC<br>Sec: Computer and Technology<br> ind: Telecomm Equipment",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Telecomm Equipment",
                    "label": "QRVO",
                    "y": 25,
                    "x": 25,
                    "id": 25
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "XILINX INC",
                    "title": "Name: XILINX INC<br>Sec: Computer and Technology<br> ind: Electronic/Semiconductors",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronic/Semiconductors",
                    "label": "XLNX",
                    "radius": 10,
                    "y": 28,
                    "x": 28,
                    "id": 28
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "BROADCOM LTD",
                    "title": "Name: BROADCOM LTD<br>Sec: Computer and Technology<br> ind: Electronic/Semiconductors",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronic/Semiconductors",
                    "label": "AVGO",
                    "radius": 10,
                    "y": 30,
                    "x": 30,
                    "id": 30
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "LAM RESEARCH",
                    "title": "Name: LAM RESEARCH<br>Sec: Computer and Technology<br> ind: Miscellaneous Technology",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Miscellaneous Technology",
                    "label": "LRCX",
                    "radius": 10,
                    "y": 32,
                    "x": 32,
                    "id": 32
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "APPLD MATLS INC",
                    "title": "Name: APPLD MATLS INC<br>Sec: Computer and Technology<br> ind: Miscellaneous Technology",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Miscellaneous Technology",
                    "label": "AMAT",
                    "radius": 10,
                    "y": 34,
                    "x": 34,
                    "id": 34
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "TEXAS INSTRS",
                    "title": "Name: TEXAS INSTRS<br>Sec: Computer and Technology<br> ind: Electronic/Semiconductors",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronic/Semiconductors",
                    "label": "TXN",
                    "radius": 10,
                    "y": 36,
                    "x": 36,
                    "id": 36
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "MICRON TECH",
                    "title": "Name: MICRON TECH<br>Sec: Computer and Technology<br> ind: Electronic/Semiconductors",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronic/Semiconductors",
                    "label": "MU",
                    "radius": 10,
                    "y": 38,
                    "x": 38,
                    "id": 38
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "KLA-TENCOR CORP",
                    "title": "Name: KLA-TENCOR CORP<br>Sec: Computer and Technology<br> ind: Miscellaneous Technology",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Miscellaneous Technology",
                    "label": "KLAC",
                    "radius": 10,
                    "y": 40,
                    "x": 40,
                    "id": 40
                },
                {
                    "Sector": "Business Services",
                    "name": "AUTOMATIC DATA",
                    "title": "Name: AUTOMATIC DATA<br>Sec: Business Services<br> ind: Business Services",
                    "color": {
                        "background": "Crimson"
                    },
                    "industry": "Business Services",
                    "label": "ADP",
                    "y": 41,
                    "x": 41,
                    "id": 41
                },
                {
                    "Sector": "Business Services",
                    "name": "PAYCHEX INC",
                    "title": "Name: PAYCHEX INC<br>Sec: Business Services<br> ind: Business Services",
                    "color": {
                        "background": "Crimson"
                    },
                    "industry": "Business Services",
                    "label": "PAYX",
                    "radius": 10,
                    "y": 42,
                    "x": 42,
                    "id": 42
                },
                {
                    "Sector": "Utilities",
                    "name": "AMEREN CORP",
                    "title": "Name: AMEREN CORP<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "AEE",
                    "y": 43,
                    "x": 43,
                    "id": 43
                },
                {
                    "Sector": "Utilities",
                    "name": "EDISON INTL",
                    "title": "Name: EDISON INTL<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "EIX",
                    "radius": 10,
                    "y": 44,
                    "x": 44,
                    "id": 44
                },
                {
                    "Sector": "Utilities",
                    "name": "DUKE ENERGY CP",
                    "title": "Name: DUKE ENERGY CP<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "DUK",
                    "y": 45,
                    "x": 45,
                    "id": 45
                },
                {
                    "Sector": "Utilities",
                    "name": "CONSOL EDISON",
                    "title": "Name: CONSOL EDISON<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "ED",
                    "y": 47,
                    "x": 47,
                    "id": 47
                },
                {
                    "Sector": "Utilities",
                    "name": "DTE ENERGY CO",
                    "title": "Name: DTE ENERGY CO<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "DTE",
                    "y": 49,
                    "x": 49,
                    "id": 49
                },
                {
                    "Sector": "Utilities",
                    "name": "CMS ENERGY",
                    "title": "Name: CMS ENERGY<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "CMS",
                    "y": 51,
                    "x": 51,
                    "id": 51
                },
                {
                    "Sector": "Utilities",
                    "name": "EVERSOURCE EGY",
                    "title": "Name: EVERSOURCE EGY<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "ES",
                    "radius": 10,
                    "y": 54,
                    "x": 54,
                    "id": 54
                },
                {
                    "Sector": "Utilities",
                    "name": "ALLIANT ENGY CP",
                    "title": "Name: ALLIANT ENGY CP<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "LNT",
                    "radius": 10,
                    "y": 56,
                    "x": 56,
                    "id": 56
                },
                {
                    "Sector": "Utilities",
                    "name": "XCEL ENERGY INC",
                    "title": "Name: XCEL ENERGY INC<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "XEL",
                    "radius": 10,
                    "y": 58,
                    "x": 58,
                    "id": 58
                },
                {
                    "Sector": "Utilities",
                    "name": "EXELON CORP",
                    "title": "Name: EXELON CORP<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "EXC",
                    "radius": 10,
                    "y": 60,
                    "x": 60,
                    "id": 60
                },
                {
                    "Sector": "Utilities",
                    "name": "DOMINION ENERGY",
                    "title": "Name: DOMINION ENERGY<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "D",
                    "y": 61,
                    "x": 61,
                    "id": 61
                },
                {
                    "Sector": "Utilities",
                    "name": "AMER ELEC PWR",
                    "title": "Name: AMER ELEC PWR<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "AEP",
                    "y": 63,
                    "x": 63,
                    "id": 63
                },
                {
                    "Sector": "Utilities",
                    "name": "FIRSTENERGY CP",
                    "title": "Name: FIRSTENERGY CP<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "FE",
                    "radius": 10,
                    "y": 66,
                    "x": 66,
                    "id": 66
                },
                {
                    "Sector": "Utilities",
                    "name": "NEXTERA ENERGY",
                    "title": "Name: NEXTERA ENERGY<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "NEE",
                    "radius": 10,
                    "y": 68,
                    "x": 68,
                    "id": 68
                },
                {
                    "Sector": "Utilities",
                    "name": "AMER WATER WORK",
                    "title": "Name: AMER WATER WORK<br>Sec: Utilities<br> ind: Utility/Water Supply",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Water Supply",
                    "label": "AWK",
                    "y": 69,
                    "x": 69,
                    "id": 69
                },
                {
                    "Sector": "Utilities",
                    "name": "CENTERPOINT EGY",
                    "title": "Name: CENTERPOINT EGY<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "CNP",
                    "y": 71,
                    "x": 71,
                    "id": 71
                },
                {
                    "Sector": "Utilities",
                    "name": "NISOURCE INC",
                    "title": "Name: NISOURCE INC<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "NI",
                    "radius": 10,
                    "y": 74,
                    "x": 74,
                    "id": 74
                },
                {
                    "Sector": "Utilities",
                    "name": "PINNACLE WEST",
                    "title": "Name: PINNACLE WEST<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "PNW",
                    "radius": 10,
                    "y": 76,
                    "x": 76,
                    "id": 76
                },
                {
                    "Sector": "Utilities",
                    "name": "WEC ENERGY GRP",
                    "title": "Name: WEC ENERGY GRP<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "WEC",
                    "radius": 10,
                    "y": 78,
                    "x": 78,
                    "id": 78
                },
                {
                    "Sector": "Utilities",
                    "name": "SEMPRA ENERGY",
                    "title": "Name: SEMPRA ENERGY<br>Sec: Utilities<br> ind: Utility/Gas Distribution",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Gas Distribution",
                    "label": "SRE",
                    "radius": 10,
                    "y": 80,
                    "x": 80,
                    "id": 80
                },
                {
                    "Sector": "Utilities",
                    "name": "SOUTHERN CO",
                    "title": "Name: SOUTHERN CO<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "SO",
                    "y": 81,
                    "x": 81,
                    "id": 81
                },
                {
                    "Sector": "Utilities",
                    "name": "ENTERGY CORP",
                    "title": "Name: ENTERGY CORP<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "ETR",
                    "y": 83,
                    "x": 83,
                    "id": 83
                },
                {
                    "Sector": "Utilities",
                    "name": "PUBLIC SV ENTRP",
                    "title": "Name: PUBLIC SV ENTRP<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "PEG",
                    "radius": 10,
                    "y": 86,
                    "x": 86,
                    "id": 86
                },
                {
                    "Sector": "Utilities",
                    "name": "PPL CORP",
                    "title": "Name: PPL CORP<br>Sec: Utilities<br> ind: Utility/Electric Power",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Electric Power",
                    "label": "PPL",
                    "radius": 10,
                    "y": 88,
                    "x": 88,
                    "id": 88
                },
                {
                    "Sector": "Finance",
                    "name": "AFLAC INC",
                    "title": "Name: AFLAC INC<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "AFL",
                    "y": 89,
                    "x": 89,
                    "id": 89
                },
                {
                    "Sector": "Finance",
                    "name": "TORCHMARK CORP",
                    "title": "Name: TORCHMARK CORP<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "TMK",
                    "radius": 10,
                    "y": 90,
                    "x": 90,
                    "id": 90
                },
                {
                    "Sector": "Finance",
                    "name": "CHUBB LTD",
                    "title": "Name: CHUBB LTD<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "CB",
                    "y": 91,
                    "x": 91,
                    "id": 91
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "AMETEK INC",
                    "title": "Name: AMETEK INC<br>Sec: Computer and Technology<br> ind: Electronics",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronics",
                    "label": "AME",
                    "y": 93,
                    "x": 93,
                    "id": 93
                },
                {
                    "Sector": "Finance",
                    "name": "GALLAGHER ARTHU",
                    "title": "Name: GALLAGHER ARTHU<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "AJG",
                    "y": 95,
                    "x": 95,
                    "id": 95
                },
                {
                    "Sector": "Finance",
                    "name": "HARTFORD FIN SV",
                    "title": "Name: HARTFORD FIN SV<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "HIG",
                    "radius": 10,
                    "y": 98,
                    "x": 98,
                    "id": 98
                },
                {
                    "Sector": "Finance",
                    "name": "BERKSHIRE HTH-B",
                    "title": "Name: BERKSHIRE HTH-B<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "BRK.B",
                    "radius": 10,
                    "y": 100,
                    "x": 100,
                    "id": 100
                },
                {
                    "Sector": "Finance",
                    "name": "AMERIPRISE FINL",
                    "title": "Name: AMERIPRISE FINL<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "AMP",
                    "y": 101,
                    "x": 101,
                    "id": 101
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "PARKER HANNIFIN",
                    "title": "Name: PARKER HANNIFIN<br>Sec: Industrial PRODUCTS<br> ind: Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Machinery",
                    "label": "PH",
                    "radius": 10,
                    "y": 104,
                    "x": 104,
                    "id": 104
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "EATON CORP PLC",
                    "title": "Name: EATON CORP PLC<br>Sec: Industrial PRODUCTS<br> ind: Electrical Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Electrical Machinery",
                    "label": "ETN",
                    "radius": 10,
                    "y": 106,
                    "x": 106,
                    "id": 106
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "ROCKWELL AUTOMT",
                    "title": "Name: ROCKWELL AUTOMT<br>Sec: Industrial PRODUCTS<br> ind: Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Machinery",
                    "label": "ROK",
                    "radius": 10,
                    "y": 108,
                    "x": 108,
                    "id": 108
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "CATERPILLAR INC",
                    "title": "Name: CATERPILLAR INC<br>Sec: Industrial PRODUCTS<br> ind: Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Machinery",
                    "label": "CAT",
                    "y": 109,
                    "x": 109,
                    "id": 109
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "ILL TOOL WORKS",
                    "title": "Name: ILL TOOL WORKS<br>Sec: Industrial PRODUCTS<br> ind: Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Machinery",
                    "label": "ITW",
                    "radius": 10,
                    "y": 112,
                    "x": 112,
                    "id": 112
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "DOVER CORP",
                    "title": "Name: DOVER CORP<br>Sec: Industrial PRODUCTS<br> ind: Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Machinery",
                    "label": "DOV",
                    "y": 113,
                    "x": 113,
                    "id": 113
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "EMERSON ELEC CO",
                    "title": "Name: EMERSON ELEC CO<br>Sec: Industrial PRODUCTS<br> ind: Electrical Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Electrical Machinery",
                    "label": "EMR",
                    "y": 115,
                    "x": 115,
                    "id": 115
                },
                {
                    "Sector": "Multi-Sector Conglomerates",
                    "name": "HONEYWELL INTL",
                    "title": "Name: HONEYWELL INTL<br>Sec: Multi-Sector Conglomerates<br> ind: Conglomerates",
                    "color": {
                        "background": "GoldenRod"
                    },
                    "industry": "Conglomerates",
                    "label": "HON",
                    "y": 117,
                    "x": 117,
                    "id": 117
                },
                {
                    "Sector": "Finance",
                    "name": "WILLIS TWRS WAT",
                    "title": "Name: WILLIS TWRS WAT<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "WLTW",
                    "radius": 10,
                    "y": 120,
                    "x": 120,
                    "id": 120
                },
                {
                    "Sector": "Finance",
                    "name": "AON PLC",
                    "title": "Name: AON PLC<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "AON",
                    "y": 121,
                    "x": 121,
                    "id": 121
                },
                {
                    "Sector": "Construction",
                    "name": "UTD RENTALS INC",
                    "title": "Name: UTD RENTALS INC<br>Sec: Construction<br> ind: Building Products",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Building Products",
                    "label": "URI",
                    "radius": 10,
                    "y": 124,
                    "x": 124,
                    "id": 124
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "FLOWSERVE CORP",
                    "title": "Name: FLOWSERVE CORP<br>Sec: Industrial PRODUCTS<br> ind: Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Machinery",
                    "label": "FLS",
                    "radius": 10,
                    "y": 126,
                    "x": 126,
                    "id": 126
                },
                {
                    "Sector": "Multi-Sector Conglomerates",
                    "name": "LEUCADIA NATL",
                    "title": "Name: LEUCADIA NATL<br>Sec: Multi-Sector Conglomerates<br> ind: Conglomerates",
                    "color": {
                        "background": "GoldenRod"
                    },
                    "industry": "Conglomerates",
                    "label": "LUK",
                    "radius": 10,
                    "y": 128,
                    "x": 128,
                    "id": 128
                },
                {
                    "Sector": "Finance",
                    "name": "FRANKLIN RESOUR",
                    "title": "Name: FRANKLIN RESOUR<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "BEN",
                    "y": 129,
                    "x": 129,
                    "id": 129
                },
                {
                    "Sector": "Finance",
                    "name": "CAPITAL ONE FIN",
                    "title": "Name: CAPITAL ONE FIN<br>Sec: Finance<br> ind: Finance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Finance",
                    "label": "COF",
                    "radius": 10,
                    "y": 132,
                    "x": 132,
                    "id": 132
                },
                {
                    "Sector": "Finance",
                    "name": "CINCINNATI FINL",
                    "title": "Name: CINCINNATI FINL<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "CINF",
                    "radius": 10,
                    "y": 134,
                    "x": 134,
                    "id": 134
                },
                {
                    "Sector": "Finance",
                    "name": "E TRADE FINL CP",
                    "title": "Name: E TRADE FINL CP<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "ETFC",
                    "radius": 10,
                    "y": 136,
                    "x": 136,
                    "id": 136
                },
                {
                    "Sector": "Finance",
                    "name": "COMERICA INC",
                    "title": "Name: COMERICA INC<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "CMA",
                    "radius": 10,
                    "y": 138,
                    "x": 138,
                    "id": 138
                },
                {
                    "Sector": "Finance",
                    "name": "PEOPLES UTD FIN",
                    "title": "Name: PEOPLES UTD FIN<br>Sec: Finance<br> ind: Banks & Thrifts",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Banks & Thrifts",
                    "label": "PBCT",
                    "radius": 10,
                    "y": 140,
                    "x": 140,
                    "id": 140
                },
                {
                    "Sector": "Finance",
                    "name": "M&T BANK CORP",
                    "title": "Name: M&T BANK CORP<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "MTB",
                    "radius": 10,
                    "y": 142,
                    "x": 142,
                    "id": 142
                },
                {
                    "Sector": "Finance",
                    "name": "DISCOVER FIN SV",
                    "title": "Name: DISCOVER FIN SV<br>Sec: Finance<br> ind: Finance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Finance",
                    "label": "DFS",
                    "radius": 10,
                    "y": 144,
                    "x": 144,
                    "id": 144
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "STANLEY B&D INC",
                    "title": "Name: STANLEY B&D INC<br>Sec: Industrial PRODUCTS<br> ind: Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Machinery",
                    "label": "SWK",
                    "radius": 10,
                    "y": 146,
                    "x": 146,
                    "id": 146
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "SMITH (AO) CORP",
                    "title": "Name: SMITH (AO) CORP<br>Sec: Industrial PRODUCTS<br> ind: Electrical Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Electrical Machinery",
                    "label": "AOS",
                    "y": 147,
                    "x": 147,
                    "id": 147
                },
                {
                    "Sector": "Construction",
                    "name": "MASCO",
                    "title": "Name: MASCO<br>Sec: Construction<br> ind: Building Products",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Building Products",
                    "label": "MAS",
                    "radius": 10,
                    "y": 150,
                    "x": 150,
                    "id": 150
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "FORTUNE BRD H&S",
                    "title": "Name: FORTUNE BRD H&S<br>Sec: Industrial PRODUCTS<br> ind: Industrial Products/Services",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Industrial Products/Services",
                    "label": "FBHS",
                    "y": 151,
                    "x": 151,
                    "id": 151
                },
                {
                    "Sector": "Finance",
                    "name": "WELLS FARGO-NEW",
                    "title": "Name: WELLS FARGO-NEW<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "WFC",
                    "radius": 10,
                    "y": 154,
                    "x": 154,
                    "id": 154
                },
                {
                    "Sector": "Finance",
                    "name": "BLACKROCK INC",
                    "title": "Name: BLACKROCK INC<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "BLK",
                    "y": 155,
                    "x": 155,
                    "id": 155
                },
                {
                    "Sector": "Finance",
                    "name": "KEYCORP NEW",
                    "title": "Name: KEYCORP NEW<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "KEY",
                    "radius": 10,
                    "y": 158,
                    "x": 158,
                    "id": 158
                },
                {
                    "Sector": "Finance",
                    "name": "SYNCHRONY FIN",
                    "title": "Name: SYNCHRONY FIN<br>Sec: Finance<br> ind: Finance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Finance",
                    "label": "SYF",
                    "radius": 10,
                    "y": 160,
                    "x": 160,
                    "id": 160
                },
                {
                    "Sector": "Finance",
                    "name": "AMER EXPRESS CO",
                    "title": "Name: AMER EXPRESS CO<br>Sec: Finance<br> ind: Finance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Finance",
                    "label": "AXP",
                    "y": 161,
                    "x": 161,
                    "id": 161
                },
                {
                    "Sector": "Finance",
                    "name": "PRUDENTIAL FINL",
                    "title": "Name: PRUDENTIAL FINL<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "PRU",
                    "radius": 10,
                    "y": 164,
                    "x": 164,
                    "id": 164
                },
                {
                    "Sector": "Finance",
                    "name": "PRINCIPAL FINL",
                    "title": "Name: PRINCIPAL FINL<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "PFG",
                    "radius": 10,
                    "y": 166,
                    "x": 166,
                    "id": 166
                },
                {
                    "Sector": "Finance",
                    "name": "STATE ST CORP",
                    "title": "Name: STATE ST CORP<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "STT",
                    "radius": 10,
                    "y": 168,
                    "x": 168,
                    "id": 168
                },
                {
                    "Sector": "Finance",
                    "name": "SCHWAB(CHAS)",
                    "title": "Name: SCHWAB(CHAS)<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "SCHW",
                    "radius": 10,
                    "y": 170,
                    "x": 170,
                    "id": 170
                },
                {
                    "Sector": "Finance",
                    "name": "REGIONS FINL CP",
                    "title": "Name: REGIONS FINL CP<br>Sec: Finance<br> ind: Banks & Thrifts",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Banks & Thrifts",
                    "label": "RF",
                    "radius": 10,
                    "y": 172,
                    "x": 172,
                    "id": 172
                },
                {
                    "Sector": "Finance",
                    "name": "AFFIL MANAGERS",
                    "title": "Name: AFFIL MANAGERS<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "AMG",
                    "y": 173,
                    "x": 173,
                    "id": 173
                },
                {
                    "Sector": "Finance",
                    "name": "ZIONS BANCORP",
                    "title": "Name: ZIONS BANCORP<br>Sec: Finance<br> ind: Banks & Thrifts",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Banks & Thrifts",
                    "label": "ZION",
                    "radius": 10,
                    "y": 176,
                    "x": 176,
                    "id": 176
                },
                {
                    "Sector": "Finance",
                    "name": "GOLDMAN SACHS",
                    "title": "Name: GOLDMAN SACHS<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "GS",
                    "radius": 10,
                    "y": 178,
                    "x": 178,
                    "id": 178
                },
                {
                    "Sector": "Finance",
                    "name": "MORGAN STANLEY",
                    "title": "Name: MORGAN STANLEY<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "MS",
                    "radius": 10,
                    "y": 180,
                    "x": 180,
                    "id": 180
                },
                {
                    "Sector": "Finance",
                    "name": "RAYMOND JAS FIN",
                    "title": "Name: RAYMOND JAS FIN<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "RJF",
                    "radius": 10,
                    "y": 182,
                    "x": 182,
                    "id": 182
                },
                {
                    "Sector": "Finance",
                    "name": "BB&T CORP",
                    "title": "Name: BB&T CORP<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "BBT",
                    "radius": 10,
                    "y": 184,
                    "x": 184,
                    "id": 184
                },
                {
                    "Sector": "Finance",
                    "name": "JPMORGAN CHASE",
                    "title": "Name: JPMORGAN CHASE<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "JPM",
                    "radius": 10,
                    "y": 186,
                    "x": 186,
                    "id": 186
                },
                {
                    "Sector": "Finance",
                    "name": "SUNTRUST BKS",
                    "title": "Name: SUNTRUST BKS<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "STI",
                    "radius": 10,
                    "y": 188,
                    "x": 188,
                    "id": 188
                },
                {
                    "Sector": "Finance",
                    "name": "HUNTINGTON BANC",
                    "title": "Name: HUNTINGTON BANC<br>Sec: Finance<br> ind: Banks & Thrifts",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Banks & Thrifts",
                    "label": "HBAN",
                    "radius": 10,
                    "y": 190,
                    "x": 190,
                    "id": 190
                },
                {
                    "Sector": "Finance",
                    "name": "CBRE GROUP INC",
                    "title": "Name: CBRE GROUP INC<br>Sec: Finance<br> ind: Real Estate",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Real Estate",
                    "label": "CBG",
                    "radius": 10,
                    "y": 192,
                    "x": 192,
                    "id": 192
                },
                {
                    "Sector": "Finance",
                    "name": "MOODYS CORP",
                    "title": "Name: MOODYS CORP<br>Sec: Finance<br> ind: Finance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Finance",
                    "label": "MCO",
                    "radius": 10,
                    "y": 194,
                    "x": 194,
                    "id": 194
                },
                {
                    "Sector": "Finance",
                    "name": "US BANCORP",
                    "title": "Name: US BANCORP<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "USB",
                    "radius": 10,
                    "y": 196,
                    "x": 196,
                    "id": 196
                },
                {
                    "Sector": "Finance",
                    "name": "UNUM GROUP",
                    "title": "Name: UNUM GROUP<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "UNM",
                    "radius": 10,
                    "y": 198,
                    "x": 198,
                    "id": 198
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "PENTAIR PLC",
                    "title": "Name: PENTAIR PLC<br>Sec: Industrial PRODUCTS<br> ind: Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Machinery",
                    "label": "PNR",
                    "radius": 10,
                    "y": 200,
                    "x": 200,
                    "id": 200
                },
                {
                    "Sector": "Finance",
                    "name": "INVESCO LTD",
                    "title": "Name: INVESCO LTD<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "IVZ",
                    "y": 201,
                    "x": 201,
                    "id": 201
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "INGERSOLL RAND",
                    "title": "Name: INGERSOLL RAND<br>Sec: Industrial PRODUCTS<br> ind: Machinery",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Machinery",
                    "label": "IR",
                    "y": 203,
                    "x": 203,
                    "id": 203
                },
                {
                    "Sector": "Auto-Tires-Trucks",
                    "name": "PACCAR INC",
                    "title": "Name: PACCAR INC<br>Sec: Auto-Tires-Trucks<br> ind: Autos/Tires/Trucks",
                    "color": {
                        "background": "WhiteSmoke"
                    },
                    "industry": "Autos/Tires/Trucks",
                    "label": "PCAR",
                    "radius": 10,
                    "y": 206,
                    "x": 206,
                    "id": 206
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "TE CONNECT-LTD",
                    "title": "Name: TE CONNECT-LTD<br>Sec: Computer and Technology<br> ind: Electronics",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronics",
                    "label": "TEL",
                    "radius": 10,
                    "y": 208,
                    "x": 208,
                    "id": 208
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "AMPHENOL CORP-A",
                    "title": "Name: AMPHENOL CORP-A<br>Sec: Computer and Technology<br> ind: Electronics",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Electronics",
                    "label": "APH",
                    "y": 209,
                    "x": 209,
                    "id": 209
                },
                {
                    "Sector": "Finance",
                    "name": "T ROWE PRICE",
                    "title": "Name: T ROWE PRICE<br>Sec: Finance<br> ind: Investment Brokers/Managers",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Investment Brokers/Managers",
                    "label": "TROW",
                    "radius": 10,
                    "y": 212,
                    "x": 212,
                    "id": 212
                },
                {
                    "Sector": "Finance",
                    "name": "PNC FINL SVC CP",
                    "title": "Name: PNC FINL SVC CP<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "PNC",
                    "y": 213,
                    "x": 213,
                    "id": 213
                },
                {
                    "Sector": "Finance",
                    "name": "CITIGROUP INC",
                    "title": "Name: CITIGROUP INC<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "C",
                    "y": 215,
                    "x": 215,
                    "id": 215
                },
                {
                    "Sector": "Finance",
                    "name": "LINCOLN NATL-IN",
                    "title": "Name: LINCOLN NATL-IN<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "LNC",
                    "y": 217,
                    "x": 217,
                    "id": 217
                },
                {
                    "Sector": "Finance",
                    "name": "BANK OF NY MELL",
                    "title": "Name: BANK OF NY MELL<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "BK",
                    "y": 219,
                    "x": 219,
                    "id": 219
                },
                {
                    "Sector": "Finance",
                    "name": "LOEWS CORP",
                    "title": "Name: LOEWS CORP<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "L",
                    "radius": 10,
                    "y": 222,
                    "x": 222,
                    "id": 222
                },
                {
                    "Sector": "Finance",
                    "name": "BANK OF AMER CP",
                    "title": "Name: BANK OF AMER CP<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "BAC",
                    "y": 223,
                    "x": 223,
                    "id": 223
                },
                {
                    "Sector": "Finance",
                    "name": "CITIZENS FIN GP",
                    "title": "Name: CITIZENS FIN GP<br>Sec: Finance<br> ind: Banks & Thrifts",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Banks & Thrifts",
                    "label": "CFG",
                    "y": 225,
                    "x": 225,
                    "id": 225
                },
                {
                    "Sector": "Finance",
                    "name": "METLIFE INC",
                    "title": "Name: METLIFE INC<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "MET",
                    "radius": 10,
                    "y": 228,
                    "x": 228,
                    "id": 228
                },
                {
                    "Sector": "Finance",
                    "name": "AMER INTL GRP",
                    "title": "Name: AMER INTL GRP<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "AIG",
                    "y": 229,
                    "x": 229,
                    "id": 229
                },
                {
                    "Sector": "Finance",
                    "name": "FIFTH THIRD BK",
                    "title": "Name: FIFTH THIRD BK<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "FITB",
                    "radius": 10,
                    "y": 232,
                    "x": 232,
                    "id": 232
                },
                {
                    "Sector": "Auto-Tires-Trucks",
                    "name": "CUMMINS INC",
                    "title": "Name: CUMMINS INC<br>Sec: Auto-Tires-Trucks<br> ind: Autos/Tires/Trucks",
                    "color": {
                        "background": "WhiteSmoke"
                    },
                    "industry": "Autos/Tires/Trucks",
                    "label": "CMI",
                    "y": 233,
                    "x": 233,
                    "id": 233
                },
                {
                    "Sector": "Finance",
                    "name": "MARSH &MCLENNAN",
                    "title": "Name: MARSH &MCLENNAN<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "MMC",
                    "radius": 10,
                    "y": 236,
                    "x": 236,
                    "id": 236
                },
                {
                    "Sector": "Finance",
                    "name": "NORTHERN TRUST",
                    "title": "Name: NORTHERN TRUST<br>Sec: Finance<br> ind: Major Banks",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Major Banks",
                    "label": "NTRS",
                    "radius": 10,
                    "y": 238,
                    "x": 238,
                    "id": 238
                },
                {
                    "Sector": "Multi-Sector Conglomerates",
                    "name": "3M CO",
                    "title": "Name: 3M CO<br>Sec: Multi-Sector Conglomerates<br> ind: Conglomerates",
                    "color": {
                        "background": "GoldenRod"
                    },
                    "industry": "Conglomerates",
                    "label": "MMM",
                    "radius": 10,
                    "y": 240,
                    "x": 240,
                    "id": 240
                },
                {
                    "Sector": "Finance",
                    "name": "ALLSTATE CORP",
                    "title": "Name: ALLSTATE CORP<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "ALL",
                    "y": 241,
                    "x": 241,
                    "id": 241
                },
                {
                    "Sector": "Finance",
                    "name": "TRAVELERS COS",
                    "title": "Name: TRAVELERS COS<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "TRV",
                    "radius": 10,
                    "y": 244,
                    "x": 244,
                    "id": 244
                },
                {
                    "Sector": "Finance",
                    "name": "PROGRESSIVE COR",
                    "title": "Name: PROGRESSIVE COR<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "PGR",
                    "radius": 10,
                    "y": 246,
                    "x": 246,
                    "id": 246
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "MOHAWK INDS INC",
                    "title": "Name: MOHAWK INDS INC<br>Sec: Consumer Discretionary<br> ind: Home Furnishing/Appliance",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Home Furnishing/Appliance",
                    "label": "MHK",
                    "radius": 10,
                    "y": 248,
                    "x": 248,
                    "id": 248
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "ANDEAVOR CORP",
                    "title": "Name: ANDEAVOR CORP<br>Sec: Oils-Energy<br> ind: Oil/Miscellaneous",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Miscellaneous",
                    "label": "ANDV",
                    "y": 249,
                    "x": 249,
                    "id": 249
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "PHILLIPS 66",
                    "title": "Name: PHILLIPS 66<br>Sec: Oils-Energy<br> ind: Oil/Miscellaneous",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Miscellaneous",
                    "label": "PSX",
                    "radius": 10,
                    "y": 250,
                    "x": 250,
                    "id": 250
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "MARATHON PETROL",
                    "title": "Name: MARATHON PETROL<br>Sec: Oils-Energy<br> ind: Oil/Miscellaneous",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Miscellaneous",
                    "label": "MPC",
                    "y": 251,
                    "x": 251,
                    "id": 251
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "VALERO ENERGY",
                    "title": "Name: VALERO ENERGY<br>Sec: Oils-Energy<br> ind: Oil/Miscellaneous",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Miscellaneous",
                    "label": "VLO",
                    "radius": 10,
                    "y": 254,
                    "x": 254,
                    "id": 254
                },
                {
                    "Sector": "Medical",
                    "name": "ANTHEM INC",
                    "title": "Name: ANTHEM INC<br>Sec: Medical<br> ind: Medical Care",
                    "color": {
                        "background": "PaleGoldenRod"
                    },
                    "industry": "Medical Care",
                    "label": "ANTM",
                    "y": 255,
                    "x": 255,
                    "id": 255
                },
                {
                    "Sector": "Finance",
                    "name": "CIGNA CORP",
                    "title": "Name: CIGNA CORP<br>Sec: Finance<br> ind: Insurance",
                    "color": {
                        "background": "Wheat"
                    },
                    "industry": "Insurance",
                    "label": "CI",
                    "radius": 10,
                    "y": 256,
                    "x": 256,
                    "id": 256
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "APACHE CORP",
                    "title": "Name: APACHE CORP<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "APA",
                    "y": 257,
                    "x": 257,
                    "id": 257
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "HELMERICH&PAYNE",
                    "title": "Name: HELMERICH&PAYNE<br>Sec: Oils-Energy<br> ind: Oil Machinery/Services/Drilling",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil Machinery/Services/Drilling",
                    "label": "HP",
                    "radius": 10,
                    "y": 258,
                    "x": 258,
                    "id": 258
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "TECHNIPFMC PLC",
                    "title": "Name: TECHNIPFMC PLC<br>Sec: Oils-Energy<br> ind: Oil Machinery/Services/Drilling",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil Machinery/Services/Drilling",
                    "label": "FTI",
                    "y": 259,
                    "x": 259,
                    "id": 259
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "CONCHO RESOURCS",
                    "title": "Name: CONCHO RESOURCS<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "CXO",
                    "y": 261,
                    "x": 261,
                    "id": 261
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "HESS CORP",
                    "title": "Name: HESS CORP<br>Sec: Oils-Energy<br> ind: Oil/Integrated",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Integrated",
                    "label": "HES",
                    "radius": 10,
                    "y": 264,
                    "x": 264,
                    "id": 264
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "NOBLE ENERGY",
                    "title": "Name: NOBLE ENERGY<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "NBL",
                    "radius": 10,
                    "y": 266,
                    "x": 266,
                    "id": 266
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "OCCIDENTAL PET",
                    "title": "Name: OCCIDENTAL PET<br>Sec: Oils-Energy<br> ind: Oil/Integrated",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Integrated",
                    "label": "OXY",
                    "radius": 10,
                    "y": 268,
                    "x": 268,
                    "id": 268
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "MARATHON OIL CP",
                    "title": "Name: MARATHON OIL CP<br>Sec: Oils-Energy<br> ind: Oil/Integrated",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Integrated",
                    "label": "MRO",
                    "y": 269,
                    "x": 269,
                    "id": 269
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "NEWFIELD EXPL",
                    "title": "Name: NEWFIELD EXPL<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "NFX",
                    "y": 271,
                    "x": 271,
                    "id": 271
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "ANADARKO PETROL",
                    "title": "Name: ANADARKO PETROL<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "APC",
                    "y": 273,
                    "x": 273,
                    "id": 273
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "HALLIBURTON CO",
                    "title": "Name: HALLIBURTON CO<br>Sec: Oils-Energy<br> ind: Oil Machinery/Services/Drilling",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil Machinery/Services/Drilling",
                    "label": "HAL",
                    "y": 275,
                    "x": 275,
                    "id": 275
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "PIONEER NAT RES",
                    "title": "Name: PIONEER NAT RES<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "PXD",
                    "radius": 10,
                    "y": 278,
                    "x": 278,
                    "id": 278
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "EXXON MOBIL CRP",
                    "title": "Name: EXXON MOBIL CRP<br>Sec: Oils-Energy<br> ind: Oil/Integrated",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Integrated",
                    "label": "XOM",
                    "radius": 10,
                    "y": 280,
                    "x": 280,
                    "id": 280
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "SCHLUMBERGER LT",
                    "title": "Name: SCHLUMBERGER LT<br>Sec: Oils-Energy<br> ind: Oil Machinery/Services/Drilling",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil Machinery/Services/Drilling",
                    "label": "SLB",
                    "radius": 10,
                    "y": 282,
                    "x": 282,
                    "id": 282
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "CHEVRON CORP",
                    "title": "Name: CHEVRON CORP<br>Sec: Oils-Energy<br> ind: Oil/Integrated",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Integrated",
                    "label": "CVX",
                    "y": 283,
                    "x": 283,
                    "id": 283
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "CIMAREX ENERGY",
                    "title": "Name: CIMAREX ENERGY<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "XEC",
                    "radius": 10,
                    "y": 286,
                    "x": 286,
                    "id": 286
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "CONOCOPHILLIPS",
                    "title": "Name: CONOCOPHILLIPS<br>Sec: Oils-Energy<br> ind: Oil/Integrated",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Integrated",
                    "label": "COP",
                    "y": 287,
                    "x": 287,
                    "id": 287
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "CHESAPEAKE ENGY",
                    "title": "Name: CHESAPEAKE ENGY<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "CHK",
                    "y": 289,
                    "x": 289,
                    "id": 289
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "RANGE RESOURCES",
                    "title": "Name: RANGE RESOURCES<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "RRC",
                    "radius": 10,
                    "y": 292,
                    "x": 292,
                    "id": 292
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "CABOT OIL & GAS",
                    "title": "Name: CABOT OIL & GAS<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "COG",
                    "y": 293,
                    "x": 293,
                    "id": 293
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "EQT CORP",
                    "title": "Name: EQT CORP<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "EQT",
                    "radius": 10,
                    "y": 296,
                    "x": 296,
                    "id": 296
                },
                {
                    "Sector": "Utilities",
                    "name": "ONEOK INC",
                    "title": "Name: ONEOK INC<br>Sec: Utilities<br> ind: Utility/Gas Distribution",
                    "color": {
                        "background": "Lavender"
                    },
                    "industry": "Utility/Gas Distribution",
                    "label": "OKE",
                    "radius": 10,
                    "y": 298,
                    "x": 298,
                    "id": 298
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "KINDER MORGAN",
                    "title": "Name: KINDER MORGAN<br>Sec: Oils-Energy<br> ind: Oil & Gas Production/Pipeline",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil & Gas Production/Pipeline",
                    "label": "KMI",
                    "y": 299,
                    "x": 299,
                    "id": 299
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "NATL OILWELL VR",
                    "title": "Name: NATL OILWELL VR<br>Sec: Oils-Energy<br> ind: Oil Machinery/Services/Drilling",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil Machinery/Services/Drilling",
                    "label": "NOV",
                    "radius": 10,
                    "y": 302,
                    "x": 302,
                    "id": 302
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "EOG RES INC",
                    "title": "Name: EOG RES INC<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "EOG",
                    "y": 303,
                    "x": 303,
                    "id": 303
                },
                {
                    "Sector": "Oils-Energy",
                    "name": "DEVON ENERGY",
                    "title": "Name: DEVON ENERGY<br>Sec: Oils-Energy<br> ind: Oil/Exploration & Production",
                    "color": {
                        "background": "Lime"
                    },
                    "industry": "Oil/Exploration & Production",
                    "label": "DVN",
                    "y": 305,
                    "x": 305,
                    "id": 305
                },
                {
                    "Sector": "Basic Materials",
                    "name": "AIR PRODS & CHE",
                    "title": "Name: AIR PRODS & CHE<br>Sec: Basic Materials<br> ind: Chemicals",
                    "color": {
                        "background": "Magenta"
                    },
                    "industry": "Chemicals",
                    "label": "APD",
                    "y": 307,
                    "x": 307,
                    "id": 307
                },
                {
                    "Sector": "Basic Materials",
                    "name": "PRAXAIR INC",
                    "title": "Name: PRAXAIR INC<br>Sec: Basic Materials<br> ind: Chemicals",
                    "color": {
                        "background": "Magenta"
                    },
                    "industry": "Chemicals",
                    "label": "PX",
                    "radius": 10,
                    "y": 308,
                    "x": 308,
                    "id": 308
                },
                {
                    "Sector": "Basic Materials",
                    "name": "PPG INDS INC",
                    "title": "Name: PPG INDS INC<br>Sec: Basic Materials<br> ind: Chemicals",
                    "color": {
                        "background": "Magenta"
                    },
                    "industry": "Chemicals",
                    "label": "PPG",
                    "y": 309,
                    "x": 309,
                    "id": 309
                },
                {
                    "Sector": "Business Services",
                    "name": "APTIV PLC",
                    "title": "Name: APTIV PLC<br>Sec: Business Services<br> ind: Business Services",
                    "color": {
                        "background": "Crimson"
                    },
                    "industry": "Business Services",
                    "label": "APTV",
                    "y": 311,
                    "x": 311,
                    "id": 311
                },
                {
                    "Sector": "Auto-Tires-Trucks",
                    "name": "BORG WARNER INC",
                    "title": "Name: BORG WARNER INC<br>Sec: Auto-Tires-Trucks<br> ind: Autos/Tires/Trucks",
                    "color": {
                        "background": "WhiteSmoke"
                    },
                    "industry": "Autos/Tires/Trucks",
                    "label": "BWA",
                    "radius": 10,
                    "y": 312,
                    "x": 312,
                    "id": 312
                },
                {
                    "Sector": "Auto-Tires-Trucks",
                    "name": "GENERAL MOTORS",
                    "title": "Name: GENERAL MOTORS<br>Sec: Auto-Tires-Trucks<br> ind: Autos/Tires/Trucks",
                    "color": {
                        "background": "WhiteSmoke"
                    },
                    "industry": "Autos/Tires/Trucks",
                    "label": "GM",
                    "radius": 10,
                    "y": 314,
                    "x": 314,
                    "id": 314
                },
                {
                    "Sector": "Auto-Tires-Trucks",
                    "name": "FORD MOTOR CO",
                    "title": "Name: FORD MOTOR CO<br>Sec: Auto-Tires-Trucks<br> ind: Autos/Tires/Trucks",
                    "color": {
                        "background": "WhiteSmoke"
                    },
                    "industry": "Autos/Tires/Trucks",
                    "label": "F",
                    "radius": 10,
                    "y": 316,
                    "x": 316,
                    "id": 316
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "AUTOZONE INC",
                    "title": "Name: AUTOZONE INC<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "AZO",
                    "y": 317,
                    "x": 317,
                    "id": 317
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "O REILLY AUTO",
                    "title": "Name: O REILLY AUTO<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "ORLY",
                    "radius": 10,
                    "y": 318,
                    "x": 318,
                    "id": 318
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "CARNIVAL CORP",
                    "title": "Name: CARNIVAL CORP<br>Sec: Consumer Discretionary<br> ind: Leisure Services",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Leisure Services",
                    "label": "CCL",
                    "y": 319,
                    "x": 319,
                    "id": 319
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "NORWEGIAN CRUIS",
                    "title": "Name: NORWEGIAN CRUIS<br>Sec: Consumer Discretionary<br> ind: Leisure Services",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Leisure Services",
                    "label": "NCLH",
                    "radius": 10,
                    "y": 320,
                    "x": 320,
                    "id": 320
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "ROYAL CARIBBEAN",
                    "title": "Name: ROYAL CARIBBEAN<br>Sec: Consumer Discretionary<br> ind: Leisure Services",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Leisure Services",
                    "label": "RCL",
                    "radius": 10,
                    "y": 322,
                    "x": 322,
                    "id": 322
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "CADENCE DESIGN",
                    "title": "Name: CADENCE DESIGN<br>Sec: Computer and Technology<br> ind: Computer Software/Services",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Computer Software/Services",
                    "label": "CDNS",
                    "y": 323,
                    "x": 323,
                    "id": 323
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "SYNOPSYS INC",
                    "title": "Name: SYNOPSYS INC<br>Sec: Computer and Technology<br> ind: Computer Software/Services",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Computer Software/Services",
                    "label": "SNPS",
                    "radius": 10,
                    "y": 324,
                    "x": 324,
                    "id": 324
                },
                {
                    "Sector": "Basic Materials",
                    "name": "CF INDUS HLDGS",
                    "title": "Name: CF INDUS HLDGS<br>Sec: Basic Materials<br> ind: Agribusiness",
                    "color": {
                        "background": "Magenta"
                    },
                    "industry": "Agribusiness",
                    "label": "CF",
                    "y": 325,
                    "x": 325,
                    "id": 325
                },
                {
                    "Sector": "Basic Materials",
                    "name": "MOSAIC CO/THE",
                    "title": "Name: MOSAIC CO/THE<br>Sec: Basic Materials<br> ind: Agribusiness",
                    "color": {
                        "background": "Magenta"
                    },
                    "industry": "Agribusiness",
                    "label": "MOS",
                    "radius": 10,
                    "y": 326,
                    "x": 326,
                    "id": 326
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "CHURCH & DWIGHT",
                    "title": "Name: CHURCH & DWIGHT<br>Sec: Consumer Staples<br> ind: Soaps/Cosmetics",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Soaps/Cosmetics",
                    "label": "CHD",
                    "y": 327,
                    "x": 327,
                    "id": 327
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "CLOROX CO",
                    "title": "Name: CLOROX CO<br>Sec: Consumer Staples<br> ind: Soaps/Cosmetics",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Soaps/Cosmetics",
                    "label": "CLX",
                    "radius": 10,
                    "y": 328,
                    "x": 328,
                    "id": 328
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "KIMBERLY CLARK",
                    "title": "Name: KIMBERLY CLARK<br>Sec: Consumer Staples<br> ind: Consumer Products/Staples",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Consumer Products/Staples",
                    "label": "KMB",
                    "radius": 10,
                    "y": 330,
                    "x": 330,
                    "id": 330
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "CAMPBELL SOUP",
                    "title": "Name: CAMPBELL SOUP<br>Sec: Consumer Staples<br> ind: Food",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Food",
                    "label": "CPB",
                    "y": 331,
                    "x": 331,
                    "id": 331
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "KELLOGG CO",
                    "title": "Name: KELLOGG CO<br>Sec: Consumer Staples<br> ind: Food",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Food",
                    "label": "K",
                    "radius": 10,
                    "y": 332,
                    "x": 332,
                    "id": 332
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "GENL MILLS",
                    "title": "Name: GENL MILLS<br>Sec: Consumer Staples<br> ind: Food",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Food",
                    "label": "GIS",
                    "radius": 10,
                    "y": 334,
                    "x": 334,
                    "id": 334
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "MCCORMICK & CO",
                    "title": "Name: MCCORMICK & CO<br>Sec: Consumer Staples<br> ind: Food",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Food",
                    "label": "MKC",
                    "radius": 10,
                    "y": 336,
                    "x": 336,
                    "id": 336
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "MONDELEZ INTL",
                    "title": "Name: MONDELEZ INTL<br>Sec: Consumer Staples<br> ind: Food",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Food",
                    "label": "MDLZ",
                    "radius": 10,
                    "y": 338,
                    "x": 338,
                    "id": 338
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "SMUCKER JM",
                    "title": "Name: SMUCKER JM<br>Sec: Consumer Staples<br> ind: Food",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Food",
                    "label": "SJM",
                    "radius": 10,
                    "y": 340,
                    "x": 340,
                    "id": 340
                },
                {
                    "Sector": "Transportation",
                    "name": "CSX CORP",
                    "title": "Name: CSX CORP<br>Sec: Transportation<br> ind: Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Transportation",
                    "label": "CSX",
                    "y": 341,
                    "x": 341,
                    "id": 341
                },
                {
                    "Sector": "Transportation",
                    "name": "NORFOLK SOUTHRN",
                    "title": "Name: NORFOLK SOUTHRN<br>Sec: Transportation<br> ind: Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Transportation",
                    "label": "NSC",
                    "radius": 10,
                    "y": 342,
                    "x": 342,
                    "id": 342
                },
                {
                    "Sector": "Transportation",
                    "name": "UNION PAC CORP",
                    "title": "Name: UNION PAC CORP<br>Sec: Transportation<br> ind: Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Transportation",
                    "label": "UNP",
                    "radius": 10,
                    "y": 344,
                    "x": 344,
                    "id": 344
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "DOLLAR GENERAL",
                    "title": "Name: DOLLAR GENERAL<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "DG",
                    "y": 345,
                    "x": 345,
                    "id": 345
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "DOLLAR TREE INC",
                    "title": "Name: DOLLAR TREE INC<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "DLTR",
                    "radius": 10,
                    "y": 346,
                    "x": 346,
                    "id": 346
                },
                {
                    "Sector": "Medical",
                    "name": "QUEST DIAGNOSTC",
                    "title": "Name: QUEST DIAGNOSTC<br>Sec: Medical<br> ind: Medical Care",
                    "color": {
                        "background": "PaleGoldenRod"
                    },
                    "industry": "Medical Care",
                    "label": "DGX",
                    "y": 347,
                    "x": 347,
                    "id": 347
                },
                {
                    "Sector": "Medical",
                    "name": "LABORATORY CP",
                    "title": "Name: LABORATORY CP<br>Sec: Medical<br> ind: Medical Products",
                    "color": {
                        "background": "PaleGoldenRod"
                    },
                    "industry": "Medical Products",
                    "label": "LH",
                    "radius": 10,
                    "y": 348,
                    "x": 348,
                    "id": 348
                },
                {
                    "Sector": "Construction",
                    "name": "D R HORTON INC",
                    "title": "Name: D R HORTON INC<br>Sec: Construction<br> ind: Construction/Building Services",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Construction/Building Services",
                    "label": "DHI",
                    "y": 349,
                    "x": 349,
                    "id": 349
                },
                {
                    "Sector": "Construction",
                    "name": "PULTE GROUP ONC",
                    "title": "Name: PULTE GROUP ONC<br>Sec: Construction<br> ind: Construction/Building Services",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Construction/Building Services",
                    "label": "PHM",
                    "radius": 10,
                    "y": 350,
                    "x": 350,
                    "id": 350
                },
                {
                    "Sector": "Construction",
                    "name": "LENNAR CORP -A",
                    "title": "Name: LENNAR CORP -A<br>Sec: Construction<br> ind: Construction/Building Services",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Construction/Building Services",
                    "label": "LEN",
                    "y": 351,
                    "x": 351,
                    "id": 351
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "DISCOVERY COM-A",
                    "title": "Name: DISCOVERY COM-A<br>Sec: Consumer Discretionary<br> ind: Media",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Media",
                    "label": "DISCA",
                    "y": 353,
                    "x": 353,
                    "id": 353
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "DISCOVERY COM-C",
                    "title": "Name: DISCOVERY COM-C<br>Sec: Consumer Discretionary<br> ind: Media",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Media",
                    "label": "DISCK",
                    "radius": 10,
                    "y": 354,
                    "x": 354,
                    "id": 354
                },
                {
                    "Sector": "Basic Materials",
                    "name": "EASTMAN CHEM CO",
                    "title": "Name: EASTMAN CHEM CO<br>Sec: Basic Materials<br> ind: Chemicals",
                    "color": {
                        "background": "Magenta"
                    },
                    "industry": "Chemicals",
                    "label": "EMN",
                    "y": 355,
                    "x": 355,
                    "id": 355
                },
                {
                    "Sector": "Basic Materials",
                    "name": "LYONDELLBASEL-A",
                    "title": "Name: LYONDELLBASEL-A<br>Sec: Basic Materials<br> ind: Chemicals",
                    "color": {
                        "background": "Magenta"
                    },
                    "industry": "Chemicals",
                    "label": "LYB",
                    "radius": 10,
                    "y": 356,
                    "x": 356,
                    "id": 356
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "FASTENAL",
                    "title": "Name: FASTENAL<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "FAST",
                    "y": 357,
                    "x": 357,
                    "id": 357
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "GRAINGER W W",
                    "title": "Name: GRAINGER W W<br>Sec: Industrial PRODUCTS<br> ind: Industrial Products/Services",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Industrial Products/Services",
                    "label": "GWW",
                    "radius": 10,
                    "y": 358,
                    "x": 358,
                    "id": 358
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "FACEBOOK INC-A",
                    "title": "Name: FACEBOOK INC-A<br>Sec: Computer and Technology<br> ind: Computer Software/Services",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Computer Software/Services",
                    "label": "FB",
                    "y": 359,
                    "x": 359,
                    "id": 359
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "ALPHABET INC-A",
                    "title": "Name: ALPHABET INC-A<br>Sec: Computer and Technology<br> ind: Computer Software/Services",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Computer Software/Services",
                    "label": "GOOGL",
                    "radius": 10,
                    "y": 360,
                    "x": 360,
                    "id": 360
                },
                {
                    "Sector": "Business Services",
                    "name": "VISA INC-A",
                    "title": "Name: VISA INC-A<br>Sec: Business Services<br> ind: Business Services",
                    "color": {
                        "background": "Crimson"
                    },
                    "industry": "Business Services",
                    "label": "V",
                    "radius": 10,
                    "y": 362,
                    "x": 362,
                    "id": 362
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "MICROSOFT CORP",
                    "title": "Name: MICROSOFT CORP<br>Sec: Computer and Technology<br> ind: Computer Software/Services",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Computer Software/Services",
                    "label": "MSFT",
                    "y": 363,
                    "x": 363,
                    "id": 363
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "ALPHABET INC-C",
                    "title": "Name: ALPHABET INC-C<br>Sec: Computer and Technology<br> ind: Computer Software/Services",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Computer Software/Services",
                    "label": "GOOG",
                    "y": 365,
                    "x": 365,
                    "id": 365
                },
                {
                    "Sector": "Business Services",
                    "name": "MASTERCARD INC",
                    "title": "Name: MASTERCARD INC<br>Sec: Business Services<br> ind: Business Services",
                    "color": {
                        "background": "Crimson"
                    },
                    "industry": "Business Services",
                    "label": "MA",
                    "y": 367,
                    "x": 367,
                    "id": 367
                },
                {
                    "Sector": "Transportation",
                    "name": "FEDEX CORP",
                    "title": "Name: FEDEX CORP<br>Sec: Transportation<br> ind: Air Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Air Transportation",
                    "label": "FDX",
                    "y": 369,
                    "x": 369,
                    "id": 369
                },
                {
                    "Sector": "Transportation",
                    "name": "UTD PARCEL SRVC",
                    "title": "Name: UTD PARCEL SRVC<br>Sec: Transportation<br> ind: Air Transportation",
                    "color": {
                        "background": "Chocolate"
                    },
                    "industry": "Air Transportation",
                    "label": "UPS",
                    "radius": 10,
                    "y": 370,
                    "x": 370,
                    "id": 370
                },
                {
                    "Sector": "Construction",
                    "name": "FLUOR CORP-NEW",
                    "title": "Name: FLUOR CORP-NEW<br>Sec: Construction<br> ind: Construction/Building Services",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Construction/Building Services",
                    "label": "FLR",
                    "y": 371,
                    "x": 371,
                    "id": 371
                },
                {
                    "Sector": "Construction",
                    "name": "JACOBS ENGIN GR",
                    "title": "Name: JACOBS ENGIN GR<br>Sec: Construction<br> ind: Construction/Building Services",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Construction/Building Services",
                    "label": "JEC",
                    "radius": 10,
                    "y": 372,
                    "x": 372,
                    "id": 372
                },
                {
                    "Sector": "Construction",
                    "name": "QUANTA SERVICES",
                    "title": "Name: QUANTA SERVICES<br>Sec: Construction<br> ind: Construction/Building Services",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Construction/Building Services",
                    "label": "PWR",
                    "radius": 10,
                    "y": 374,
                    "x": 374,
                    "id": 374
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "TWENTY-FIRST CF",
                    "title": "Name: TWENTY-FIRST CF<br>Sec: Consumer Discretionary<br> ind: Media",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Media",
                    "label": "FOX",
                    "y": 375,
                    "x": 375,
                    "id": 375
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "MATTEL INC",
                    "title": "Name: MATTEL INC<br>Sec: Consumer Discretionary<br> ind: Other Consumer Discretionary",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Other Consumer Discretionary",
                    "label": "MAT",
                    "radius": 10,
                    "y": 376,
                    "x": 376,
                    "id": 376
                },
                {
                    "Sector": "Aerospace",
                    "name": "GENL DYNAMICS",
                    "title": "Name: GENL DYNAMICS<br>Sec: Aerospace<br> ind: Aerospace/Defense",
                    "color": {
                        "background": "Peru"
                    },
                    "industry": "Aerospace/Defense",
                    "label": "GD",
                    "y": 377,
                    "x": 377,
                    "id": 377
                },
                {
                    "Sector": "Aerospace",
                    "name": "NORTHROP GRUMMN",
                    "title": "Name: NORTHROP GRUMMN<br>Sec: Aerospace<br> ind: Aerospace/Defense",
                    "color": {
                        "background": "Peru"
                    },
                    "industry": "Aerospace/Defense",
                    "label": "NOC",
                    "radius": 10,
                    "y": 378,
                    "x": 378,
                    "id": 378
                },
                {
                    "Sector": "Aerospace",
                    "name": "L3 TECHNOLOGIES",
                    "title": "Name: L3 TECHNOLOGIES<br>Sec: Aerospace<br> ind: Aerospace/Defense",
                    "color": {
                        "background": "Peru"
                    },
                    "industry": "Aerospace/Defense",
                    "label": "LLL",
                    "y": 379,
                    "x": 379,
                    "id": 379
                },
                {
                    "Sector": "Aerospace",
                    "name": "RAYTHEON CO",
                    "title": "Name: RAYTHEON CO<br>Sec: Aerospace<br> ind: Aerospace/Defense",
                    "color": {
                        "background": "Peru"
                    },
                    "industry": "Aerospace/Defense",
                    "label": "RTN",
                    "radius": 10,
                    "y": 382,
                    "x": 382,
                    "id": 382
                },
                {
                    "Sector": "Aerospace",
                    "name": "LOCKHEED MARTIN",
                    "title": "Name: LOCKHEED MARTIN<br>Sec: Aerospace<br> ind: Aerospace/Defense",
                    "color": {
                        "background": "Peru"
                    },
                    "industry": "Aerospace/Defense",
                    "label": "LMT",
                    "y": 383,
                    "x": 383,
                    "id": 383
                },
                {
                    "Sector": "Medical",
                    "name": "HCA HOLDINGS",
                    "title": "Name: HCA HOLDINGS<br>Sec: Medical<br> ind: Medical Care",
                    "color": {
                        "background": "PaleGoldenRod"
                    },
                    "industry": "Medical Care",
                    "label": "HCA",
                    "y": 385,
                    "x": 385,
                    "id": 385
                },
                {
                    "Sector": "Medical",
                    "name": "UNIVL HLTH SVCS",
                    "title": "Name: UNIVL HLTH SVCS<br>Sec: Medical<br> ind: Medical Care",
                    "color": {
                        "background": "PaleGoldenRod"
                    },
                    "industry": "Medical Care",
                    "label": "UHS",
                    "radius": 10,
                    "y": 386,
                    "x": 386,
                    "id": 386
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "HOME DEPOT",
                    "title": "Name: HOME DEPOT<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "HD",
                    "y": 387,
                    "x": 387,
                    "id": 387
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "LOWES COS",
                    "title": "Name: LOWES COS<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "LOW",
                    "radius": 10,
                    "y": 388,
                    "x": 388,
                    "id": 388
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "HILTON WW HLDG",
                    "title": "Name: HILTON WW HLDG<br>Sec: Consumer Discretionary<br> ind: Leisure Services",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Leisure Services",
                    "label": "HLT",
                    "y": 389,
                    "x": 389,
                    "id": 389
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "WYNDHAM WORLDWD",
                    "title": "Name: WYNDHAM WORLDWD<br>Sec: Consumer Discretionary<br> ind: Leisure Services",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Leisure Services",
                    "label": "WYN",
                    "radius": 10,
                    "y": 390,
                    "x": 390,
                    "id": 390
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "MARRIOTT INTL-A",
                    "title": "Name: MARRIOTT INTL-A<br>Sec: Consumer Discretionary<br> ind: Leisure Services",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Leisure Services",
                    "label": "MAR",
                    "y": 391,
                    "x": 391,
                    "id": 391
                },
                {
                    "Sector": "Basic Materials",
                    "name": "INTL PAPER",
                    "title": "Name: INTL PAPER<br>Sec: Basic Materials<br> ind: Paper",
                    "color": {
                        "background": "Magenta"
                    },
                    "industry": "Paper",
                    "label": "IP",
                    "y": 393,
                    "x": 393,
                    "id": 393
                },
                {
                    "Sector": "Basic Materials",
                    "name": "WESTROCK CO",
                    "title": "Name: WESTROCK CO<br>Sec: Basic Materials<br> ind: Paper",
                    "color": {
                        "background": "Magenta"
                    },
                    "industry": "Paper",
                    "label": "WRK",
                    "radius": 10,
                    "y": 394,
                    "x": 394,
                    "id": 394
                },
                {
                    "Sector": "Industrial PRODUCTS",
                    "name": "PACKAGING CORP",
                    "title": "Name: PACKAGING CORP<br>Sec: Industrial PRODUCTS<br> ind: Containers & Glass",
                    "color": {
                        "background": "GreenYellow"
                    },
                    "industry": "Containers & Glass",
                    "label": "PKG",
                    "y": 395,
                    "x": 395,
                    "id": 395
                },
                {
                    "Sector": "Business Services",
                    "name": "INTERPUBLIC GRP",
                    "title": "Name: INTERPUBLIC GRP<br>Sec: Business Services<br> ind: Business Services",
                    "color": {
                        "background": "Crimson"
                    },
                    "industry": "Business Services",
                    "label": "IPG",
                    "y": 397,
                    "x": 397,
                    "id": 397
                },
                {
                    "Sector": "Business Services",
                    "name": "OMNICOM GRP",
                    "title": "Name: OMNICOM GRP<br>Sec: Business Services<br> ind: Business Services",
                    "color": {
                        "background": "Crimson"
                    },
                    "industry": "Business Services",
                    "label": "OMC",
                    "radius": 10,
                    "y": 398,
                    "x": 398,
                    "id": 398
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "NORDSTROM INC",
                    "title": "Name: NORDSTROM INC<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "JWN",
                    "y": 399,
                    "x": 399,
                    "id": 399
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "KOHLS CORP",
                    "title": "Name: KOHLS CORP<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "KSS",
                    "radius": 10,
                    "y": 400,
                    "x": 400,
                    "id": 400
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "MACYS INC",
                    "title": "Name: MACYS INC<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "M",
                    "radius": 10,
                    "y": 402,
                    "x": 402,
                    "id": 402
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "COCA COLA CO",
                    "title": "Name: COCA COLA CO<br>Sec: Consumer Staples<br> ind: Beverages",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Beverages",
                    "label": "KO",
                    "y": 403,
                    "x": 403,
                    "id": 403
                },
                {
                    "Sector": "Consumer Staples",
                    "name": "PEPSICO INC",
                    "title": "Name: PEPSICO INC<br>Sec: Consumer Staples<br> ind: Beverages",
                    "color": {
                        "background": "Orange"
                    },
                    "industry": "Beverages",
                    "label": "PEP",
                    "radius": 10,
                    "y": 404,
                    "x": 404,
                    "id": 404
                },
                {
                    "Sector": "Construction",
                    "name": "MARTIN MRT-MATL",
                    "title": "Name: MARTIN MRT-MATL<br>Sec: Construction<br> ind: Building Products",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Building Products",
                    "label": "MLM",
                    "y": 405,
                    "x": 405,
                    "id": 405
                },
                {
                    "Sector": "Construction",
                    "name": "VULCAN MATLS CO",
                    "title": "Name: VULCAN MATLS CO<br>Sec: Construction<br> ind: Building Products",
                    "color": {
                        "background": "LightSlateGray"
                    },
                    "industry": "Building Products",
                    "label": "VMC",
                    "radius": 10,
                    "y": 406,
                    "x": 406,
                    "id": 406
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "NEWS CORP-B",
                    "title": "Name: NEWS CORP-B<br>Sec: Consumer Discretionary<br> ind: Media",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Media",
                    "label": "NWS",
                    "y": 407,
                    "x": 407,
                    "id": 407
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "NEWS CORP NEW-A",
                    "title": "Name: NEWS CORP NEW-A<br>Sec: Consumer Discretionary<br> ind: Media",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Media",
                    "label": "NWSA",
                    "radius": 10,
                    "y": 408,
                    "x": 408,
                    "id": 408
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "PVH CORP",
                    "title": "Name: PVH CORP<br>Sec: Consumer Discretionary<br> ind: Apparel",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Apparel",
                    "label": "PVH",
                    "y": 409,
                    "x": 409,
                    "id": 409
                },
                {
                    "Sector": "Consumer Discretionary",
                    "name": "V F CORP",
                    "title": "Name: V F CORP<br>Sec: Consumer Discretionary<br> ind: Apparel",
                    "color": {
                        "background": "MintCream"
                    },
                    "industry": "Apparel",
                    "label": "VFC",
                    "radius": 10,
                    "y": 410,
                    "x": 410,
                    "id": 410
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "ROSS STORES",
                    "title": "Name: ROSS STORES<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "ROST",
                    "y": 411,
                    "x": 411,
                    "id": 411
                },
                {
                    "Sector": "Retail-Wholesale",
                    "name": "TJX COS INC NEW",
                    "title": "Name: TJX COS INC NEW<br>Sec: Retail-Wholesale<br> ind: Non-Food Retail/Wholesale",
                    "color": {
                        "background": "Gold"
                    },
                    "industry": "Non-Food Retail/Wholesale",
                    "label": "TJX",
                    "radius": 10,
                    "y": 412,
                    "x": 412,
                    "id": 412
                },
                {
                    "Sector": "Business Services",
                    "name": "REPUBLIC SVCS",
                    "title": "Name: REPUBLIC SVCS<br>Sec: Business Services<br> ind: Business Services",
                    "color": {
                        "background": "Crimson"
                    },
                    "industry": "Business Services",
                    "label": "RSG",
                    "y": 413,
                    "x": 413,
                    "id": 413
                },
                {
                    "Sector": "Business Services",
                    "name": "WASTE MGMT-NEW",
                    "title": "Name: WASTE MGMT-NEW<br>Sec: Business Services<br> ind: Business Services",
                    "color": {
                        "background": "Crimson"
                    },
                    "industry": "Business Services",
                    "label": "WM",
                    "radius": 10,
                    "y": 414,
                    "x": 414,
                    "id": 414
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "AT&T INC",
                    "title": "Name: AT&T INC<br>Sec: Computer and Technology<br> ind: Telecomm Services",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Telecomm Services",
                    "label": "T",
                    "y": 415,
                    "x": 415,
                    "id": 415
                },
                {
                    "Sector": "Computer and Technology",
                    "name": "VERIZON COMM",
                    "title": "Name: VERIZON COMM<br>Sec: Computer and Technology<br> ind: Telecomm Services",
                    "color": {
                        "background": "LightBlue"
                    },
                    "industry": "Telecomm Services",
                    "label": "VZ",
                    "radius": 10,
                    "y": 416,
                    "x": 416,
                    "id": 416
                }
            ],
            'my_edges': [
                {
                    "from": 1,
                    "width": 6.2888854109973105,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.628888541099731,
                    "to": 2,
                    "id": 1
                },
                {
                    "from": 2,
                    "width": 6.018871346304521,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6018871346304521,
                    "to": 4,
                    "id": 2
                },
                {
                    "from": 5,
                    "width": 6.252836250865661,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6252836250865661,
                    "to": 4,
                    "id": 3
                },
                {
                    "from": 7,
                    "width": 6.287197140713916,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6287197140713916,
                    "to": 4,
                    "id": 4
                },
                {
                    "from": 9,
                    "width": 6.446897082564825,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6446897082564825,
                    "to": 10,
                    "id": 5
                },
                {
                    "from": 10,
                    "width": 6.096177324243296,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6096177324243296,
                    "to": 12,
                    "id": 6
                },
                {
                    "from": 10,
                    "width": 6.138089668884358,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6138089668884358,
                    "to": 14,
                    "id": 7
                },
                {
                    "from": 10,
                    "width": 6.408098998824853,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6408098998824853,
                    "to": 16,
                    "id": 8
                },
                {
                    "from": 17,
                    "width": 6.627134007678503,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6627134007678503,
                    "to": 18,
                    "id": 9
                },
                {
                    "from": 17,
                    "width": 6.986708894157667,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6986708894157667,
                    "to": 20,
                    "id": 10
                },
                {
                    "from": 21,
                    "width": 6.081273841772683,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6081273841772683,
                    "to": 22,
                    "id": 11
                },
                {
                    "from": 23,
                    "width": 6.118862236259317,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6118862236259317,
                    "to": 22,
                    "id": 12
                },
                {
                    "from": 25,
                    "width": 6.894614268482966,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6894614268482966,
                    "to": 22,
                    "id": 13
                },
                {
                    "from": 21,
                    "width": 6.0863219651711065,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6086321965171106,
                    "to": 28,
                    "id": 14
                },
                {
                    "from": 21,
                    "width": 6.143726816445511,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6143726816445512,
                    "to": 30,
                    "id": 15
                },
                {
                    "from": 21,
                    "width": 6.235230442223747,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6235230442223747,
                    "to": 32,
                    "id": 16
                },
                {
                    "from": 21,
                    "width": 6.453406732287573,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6453406732287573,
                    "to": 34,
                    "id": 17
                },
                {
                    "from": 32,
                    "width": 6.450593641888128,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6450593641888128,
                    "to": 36,
                    "id": 18
                },
                {
                    "from": 34,
                    "width": 6.280918893256801,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.62809188932568,
                    "to": 38,
                    "id": 19
                },
                {
                    "from": 34,
                    "width": 7.023218306982279,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7023218306982278,
                    "to": 40,
                    "id": 20
                },
                {
                    "from": 41,
                    "width": 7.080441041679659,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7080441041679659,
                    "to": 42,
                    "id": 21
                },
                {
                    "from": 43,
                    "width": 6.37528470433166,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6375284704331661,
                    "to": 44,
                    "id": 22
                },
                {
                    "from": 45,
                    "width": 6.274321031592835,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6274321031592834,
                    "to": 44,
                    "id": 23
                },
                {
                    "from": 47,
                    "width": 6.301624873404049,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6301624873404049,
                    "to": 44,
                    "id": 24
                },
                {
                    "from": 49,
                    "width": 6.404718216836796,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6404718216836797,
                    "to": 44,
                    "id": 25
                },
                {
                    "from": 51,
                    "width": 6.491598685931534,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6491598685931534,
                    "to": 44,
                    "id": 26
                },
                {
                    "from": 44,
                    "width": 6.414271242423737,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6414271242423737,
                    "to": 54,
                    "id": 27
                },
                {
                    "from": 44,
                    "width": 6.505181249152133,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6505181249152133,
                    "to": 56,
                    "id": 28
                },
                {
                    "from": 44,
                    "width": 6.512160142231924,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6512160142231924,
                    "to": 58,
                    "id": 29
                },
                {
                    "from": 54,
                    "width": 6.456840772296904,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6456840772296905,
                    "to": 60,
                    "id": 30
                },
                {
                    "from": 61,
                    "width": 6.4188107448455956,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6418810744845596,
                    "to": 60,
                    "id": 31
                },
                {
                    "from": 63,
                    "width": 6.462513290922725,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6462513290922726,
                    "to": 60,
                    "id": 32
                },
                {
                    "from": 63,
                    "width": 6.011617933084507,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6011617933084507,
                    "to": 66,
                    "id": 33
                },
                {
                    "from": 60,
                    "width": 6.126000157772538,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6126000157772538,
                    "to": 68,
                    "id": 34
                },
                {
                    "from": 69,
                    "width": 6.007458498800837,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6007458498800837,
                    "to": 68,
                    "id": 35
                },
                {
                    "from": 71,
                    "width": 6.065328478648176,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6065328478648176,
                    "to": 68,
                    "id": 36
                },
                {
                    "from": 60,
                    "width": 6.287599322716511,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6287599322716511,
                    "to": 74,
                    "id": 37
                },
                {
                    "from": 60,
                    "width": 6.393001230709988,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6393001230709988,
                    "to": 76,
                    "id": 38
                },
                {
                    "from": 60,
                    "width": 6.450603759707699,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6450603759707698,
                    "to": 78,
                    "id": 39
                },
                {
                    "from": 69,
                    "width": 6.026215293340994,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6026215293340994,
                    "to": 80,
                    "id": 40
                },
                {
                    "from": 81,
                    "width": 6.346996247174346,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6346996247174346,
                    "to": 80,
                    "id": 41
                },
                {
                    "from": 83,
                    "width": 6.462321190658507,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6462321190658507,
                    "to": 80,
                    "id": 42
                },
                {
                    "from": 69,
                    "width": 6.168841327321656,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6168841327321656,
                    "to": 86,
                    "id": 43
                },
                {
                    "from": 68,
                    "width": 6.2490508494198895,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6249050849419889,
                    "to": 88,
                    "id": 44
                },
                {
                    "from": 89,
                    "width": 6.545538051851424,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6545538051851424,
                    "to": 90,
                    "id": 45
                },
                {
                    "from": 91,
                    "width": 6.020109394092695,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6020109394092695,
                    "to": 90,
                    "id": 46
                },
                {
                    "from": 93,
                    "width": 6.02292215117973,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.602292215117973,
                    "to": 90,
                    "id": 47
                },
                {
                    "from": 95,
                    "width": 6.205374521157986,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6205374521157986,
                    "to": 90,
                    "id": 48
                },
                {
                    "from": 91,
                    "width": 6.082314915922332,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6082314915922332,
                    "to": 98,
                    "id": 49
                },
                {
                    "from": 93,
                    "width": 6.03469630303929,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.603469630303929,
                    "to": 100,
                    "id": 50
                },
                {
                    "from": 101,
                    "width": 6.027301995944655,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6027301995944655,
                    "to": 100,
                    "id": 51
                },
                {
                    "from": 93,
                    "width": 6.046922216171721,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6046922216171721,
                    "to": 104,
                    "id": 52
                },
                {
                    "from": 93,
                    "width": 6.056010273018249,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6056010273018249,
                    "to": 106,
                    "id": 53
                },
                {
                    "from": 93,
                    "width": 6.0621150308294425,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6062115030829442,
                    "to": 108,
                    "id": 54
                },
                {
                    "from": 109,
                    "width": 6.01552148241937,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.601552148241937,
                    "to": 108,
                    "id": 55
                },
                {
                    "from": 93,
                    "width": 6.094355530072658,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6094355530072658,
                    "to": 112,
                    "id": 56
                },
                {
                    "from": 113,
                    "width": 6.047152559688724,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6047152559688724,
                    "to": 112,
                    "id": 57
                },
                {
                    "from": 115,
                    "width": 6.072647015247616,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6072647015247616,
                    "to": 112,
                    "id": 58
                },
                {
                    "from": 117,
                    "width": 6.507738897879762,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6507738897879762,
                    "to": 112,
                    "id": 59
                },
                {
                    "from": 95,
                    "width": 6.230427275946438,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6230427275946437,
                    "to": 120,
                    "id": 60
                },
                {
                    "from": 121,
                    "width": 6.4654619308129115,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6465461930812911,
                    "to": 120,
                    "id": 61
                },
                {
                    "from": 109,
                    "width": 6.073198252532698,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6073198252532699,
                    "to": 124,
                    "id": 62
                },
                {
                    "from": 115,
                    "width": 6.151169209521741,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6151169209521741,
                    "to": 126,
                    "id": 63
                },
                {
                    "from": 100,
                    "width": 6.001440217931022,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6001440217931022,
                    "to": 128,
                    "id": 64
                },
                {
                    "from": 129,
                    "width": 6.064552063783716,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6064552063783716,
                    "to": 128,
                    "id": 65
                },
                {
                    "from": 100,
                    "width": 6.040391691789042,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6040391691789042,
                    "to": 132,
                    "id": 66
                },
                {
                    "from": 100,
                    "width": 6.047526743618184,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6047526743618185,
                    "to": 134,
                    "id": 67
                },
                {
                    "from": 100,
                    "width": 6.072052192681205,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6072052192681205,
                    "to": 136,
                    "id": 68
                },
                {
                    "from": 100,
                    "width": 6.216666244063795,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6216666244063795,
                    "to": 138,
                    "id": 69
                },
                {
                    "from": 129,
                    "width": 6.058461059380987,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6058461059380986,
                    "to": 140,
                    "id": 70
                },
                {
                    "from": 129,
                    "width": 6.077811526049822,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6077811526049822,
                    "to": 142,
                    "id": 71
                },
                {
                    "from": 129,
                    "width": 6.101583574874098,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6101583574874099,
                    "to": 144,
                    "id": 72
                },
                {
                    "from": 104,
                    "width": 6.048803022573167,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6048803022573167,
                    "to": 146,
                    "id": 73
                },
                {
                    "from": 147,
                    "width": 6.0144903773556955,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6014490377355696,
                    "to": 146,
                    "id": 74
                },
                {
                    "from": 147,
                    "width": 6.610602676396474,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6610602676396474,
                    "to": 150,
                    "id": 75
                },
                {
                    "from": 151,
                    "width": 7.588750626792188,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7588750626792188,
                    "to": 150,
                    "id": 76
                },
                {
                    "from": 136,
                    "width": 6.016743675635753,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6016743675635753,
                    "to": 154,
                    "id": 77
                },
                {
                    "from": 155,
                    "width": 6.094939564528209,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6094939564528209,
                    "to": 154,
                    "id": 78
                },
                {
                    "from": 155,
                    "width": 6.112539818575592,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6112539818575592,
                    "to": 158,
                    "id": 79
                },
                {
                    "from": 140,
                    "width": 6.082406699115856,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6082406699115855,
                    "to": 160,
                    "id": 80
                },
                {
                    "from": 161,
                    "width": 6.030039129682052,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6030039129682052,
                    "to": 160,
                    "id": 81
                },
                {
                    "from": 161,
                    "width": 6.007802183993101,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6007802183993101,
                    "to": 164,
                    "id": 82
                },
                {
                    "from": 161,
                    "width": 6.012256887566199,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6012256887566199,
                    "to": 166,
                    "id": 83
                },
                {
                    "from": 161,
                    "width": 6.019347800616435,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6019347800616435,
                    "to": 168,
                    "id": 84
                },
                {
                    "from": 161,
                    "width": 6.026390251840166,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6026390251840166,
                    "to": 170,
                    "id": 85
                },
                {
                    "from": 161,
                    "width": 6.044472164299972,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6044472164299972,
                    "to": 172,
                    "id": 86
                },
                {
                    "from": 173,
                    "width": 6.005158059876029,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6005158059876029,
                    "to": 172,
                    "id": 87
                },
                {
                    "from": 161,
                    "width": 6.079303093297503,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6079303093297503,
                    "to": 176,
                    "id": 88
                },
                {
                    "from": 161,
                    "width": 6.081670645195022,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6081670645195022,
                    "to": 178,
                    "id": 89
                },
                {
                    "from": 161,
                    "width": 6.1350414483072635,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6135041448307264,
                    "to": 180,
                    "id": 90
                },
                {
                    "from": 161,
                    "width": 6.142426566133947,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6142426566133947,
                    "to": 182,
                    "id": 91
                },
                {
                    "from": 161,
                    "width": 6.208777310011917,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6208777310011917,
                    "to": 184,
                    "id": 92
                },
                {
                    "from": 173,
                    "width": 6.013556348905897,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6013556348905897,
                    "to": 186,
                    "id": 93
                },
                {
                    "from": 173,
                    "width": 6.020575680980368,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6020575680980368,
                    "to": 188,
                    "id": 94
                },
                {
                    "from": 173,
                    "width": 6.055738114591788,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6055738114591789,
                    "to": 190,
                    "id": 95
                },
                {
                    "from": 173,
                    "width": 6.064585197015023,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6064585197015023,
                    "to": 192,
                    "id": 96
                },
                {
                    "from": 173,
                    "width": 6.067875045951004,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6067875045951003,
                    "to": 194,
                    "id": 97
                },
                {
                    "from": 173,
                    "width": 6.098815327024994,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6098815327024993,
                    "to": 196,
                    "id": 98
                },
                {
                    "from": 173,
                    "width": 6.211574144084637,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6211574144084637,
                    "to": 198,
                    "id": 99
                },
                {
                    "from": 166,
                    "width": 6.0314936464429225,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6031493646442923,
                    "to": 200,
                    "id": 100
                },
                {
                    "from": 201,
                    "width": 6.012215303719303,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6012215303719304,
                    "to": 200,
                    "id": 101
                },
                {
                    "from": 203,
                    "width": 6.116466628580449,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6116466628580449,
                    "to": 200,
                    "id": 102
                },
                {
                    "from": 201,
                    "width": 6.0751205799866135,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6075120579986614,
                    "to": 206,
                    "id": 103
                },
                {
                    "from": 201,
                    "width": 6.107520223071638,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6107520223071637,
                    "to": 208,
                    "id": 104
                },
                {
                    "from": 209,
                    "width": 6.613596524023162,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6613596524023162,
                    "to": 208,
                    "id": 105
                },
                {
                    "from": 186,
                    "width": 6.022161380886935,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6022161380886935,
                    "to": 212,
                    "id": 106
                },
                {
                    "from": 213,
                    "width": 6.016656627062931,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6016656627062931,
                    "to": 212,
                    "id": 107
                },
                {
                    "from": 215,
                    "width": 6.03237371913292,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.603237371913292,
                    "to": 212,
                    "id": 108
                },
                {
                    "from": 217,
                    "width": 6.048949495009844,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6048949495009844,
                    "to": 212,
                    "id": 109
                },
                {
                    "from": 219,
                    "width": 6.14213983261319,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.614213983261319,
                    "to": 212,
                    "id": 110
                },
                {
                    "from": 178,
                    "width": 6.099153580766968,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6099153580766968,
                    "to": 222,
                    "id": 111
                },
                {
                    "from": 223,
                    "width": 6.131841203850725,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6131841203850725,
                    "to": 222,
                    "id": 112
                },
                {
                    "from": 225,
                    "width": 6.195962736588191,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6195962736588191,
                    "to": 222,
                    "id": 113
                },
                {
                    "from": 222,
                    "width": 6.100764793775539,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6100764793775539,
                    "to": 228,
                    "id": 114
                },
                {
                    "from": 229,
                    "width": 6.105712927804996,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6105712927804996,
                    "to": 228,
                    "id": 115
                },
                {
                    "from": 229,
                    "width": 6.017161536581784,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6017161536581784,
                    "to": 232,
                    "id": 116
                },
                {
                    "from": 233,
                    "width": 6.034204893803135,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6034204893803136,
                    "to": 203,
                    "id": 117
                },
                {
                    "from": 121,
                    "width": 7.171859517406498,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7171859517406498,
                    "to": 236,
                    "id": 118
                },
                {
                    "from": 144,
                    "width": 6.237640609339906,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6237640609339906,
                    "to": 238,
                    "id": 119
                },
                {
                    "from": 112,
                    "width": 6.271025495646593,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6271025495646593,
                    "to": 240,
                    "id": 120
                },
                {
                    "from": 241,
                    "width": 6.40982512393175,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6409825123931749,
                    "to": 91,
                    "id": 121
                },
                {
                    "from": 241,
                    "width": 6.278671114514079,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6278671114514079,
                    "to": 244,
                    "id": 122
                },
                {
                    "from": 241,
                    "width": 6.806902817238151,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6806902817238151,
                    "to": 246,
                    "id": 123
                },
                {
                    "from": 150,
                    "width": 6.306565069394074,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6306565069394073,
                    "to": 248,
                    "id": 124
                },
                {
                    "from": 249,
                    "width": 6.322525981077462,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6322525981077461,
                    "to": 250,
                    "id": 125
                },
                {
                    "from": 251,
                    "width": 6.737620622797392,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6737620622797392,
                    "to": 250,
                    "id": 126
                },
                {
                    "from": 250,
                    "width": 6.540542176250797,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6540542176250798,
                    "to": 254,
                    "id": 127
                },
                {
                    "from": 255,
                    "width": 6.3775784372398014,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6377578437239801,
                    "to": 256,
                    "id": 128
                },
                {
                    "from": 257,
                    "width": 6.040393323067801,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6040393323067801,
                    "to": 258,
                    "id": 129
                },
                {
                    "from": 259,
                    "width": 6.107133089614432,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6107133089614432,
                    "to": 258,
                    "id": 130
                },
                {
                    "from": 261,
                    "width": 6.118964804011576,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6118964804011575,
                    "to": 258,
                    "id": 131
                },
                {
                    "from": 259,
                    "width": 6.032287758623473,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6032287758623472,
                    "to": 264,
                    "id": 132
                },
                {
                    "from": 258,
                    "width": 6.101848725569605,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6101848725569605,
                    "to": 266,
                    "id": 133
                },
                {
                    "from": 266,
                    "width": 6.0051662690813075,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6005166269081308,
                    "to": 268,
                    "id": 134
                },
                {
                    "from": 269,
                    "width": 6.068484860039102,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6068484860039102,
                    "to": 268,
                    "id": 135
                },
                {
                    "from": 271,
                    "width": 6.221378084491804,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6221378084491804,
                    "to": 268,
                    "id": 136
                },
                {
                    "from": 273,
                    "width": 6.233646987405662,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6233646987405662,
                    "to": 268,
                    "id": 137
                },
                {
                    "from": 275,
                    "width": 6.376647243759357,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6376647243759357,
                    "to": 268,
                    "id": 138
                },
                {
                    "from": 268,
                    "width": 6.0213953543937615,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6021395354393762,
                    "to": 278,
                    "id": 139
                },
                {
                    "from": 268,
                    "width": 6.069002350390606,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6069002350390605,
                    "to": 280,
                    "id": 140
                },
                {
                    "from": 278,
                    "width": 6.041831101391826,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6041831101391826,
                    "to": 282,
                    "id": 141
                },
                {
                    "from": 283,
                    "width": 6.096637725666438,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6096637725666438,
                    "to": 282,
                    "id": 142
                },
                {
                    "from": 282,
                    "width": 6.078438316085891,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6078438316085891,
                    "to": 286,
                    "id": 143
                },
                {
                    "from": 287,
                    "width": 6.080826171269379,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6080826171269379,
                    "to": 283,
                    "id": 144
                },
                {
                    "from": 289,
                    "width": 6.102258104619666,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6102258104619666,
                    "to": 287,
                    "id": 145
                },
                {
                    "from": 289,
                    "width": 6.1690804131874435,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6169080413187443,
                    "to": 292,
                    "id": 146
                },
                {
                    "from": 293,
                    "width": 6.246476820582416,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6246476820582416,
                    "to": 292,
                    "id": 147
                },
                {
                    "from": 293,
                    "width": 6.543684517211706,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6543684517211706,
                    "to": 296,
                    "id": 148
                },
                {
                    "from": 264,
                    "width": 6.003901815153245,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6003901815153245,
                    "to": 298,
                    "id": 149
                },
                {
                    "from": 299,
                    "width": 6.525958480442048,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6525958480442048,
                    "to": 298,
                    "id": 150
                },
                {
                    "from": 264,
                    "width": 6.0371884299781,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.60371884299781,
                    "to": 302,
                    "id": 151
                },
                {
                    "from": 303,
                    "width": 6.064535982074459,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6064535982074459,
                    "to": 302,
                    "id": 152
                },
                {
                    "from": 305,
                    "width": 6.1286054869678654,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6128605486967865,
                    "to": 302,
                    "id": 153
                },
                {
                    "from": 307,
                    "width": 6.8290637143112445,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6829063714311244,
                    "to": 308,
                    "id": 154
                },
                {
                    "from": 309,
                    "width": 6.1731395415942245,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6173139541594225,
                    "to": 308,
                    "id": 155
                },
                {
                    "from": 311,
                    "width": 6.155652554661428,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6155652554661428,
                    "to": 312,
                    "id": 156
                },
                {
                    "from": 312,
                    "width": 6.1142874483812815,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6114287448381281,
                    "to": 314,
                    "id": 157
                },
                {
                    "from": 312,
                    "width": 6.237910173236654,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6237910173236654,
                    "to": 316,
                    "id": 158
                },
                {
                    "from": 317,
                    "width": 7.460499112550469,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7460499112550469,
                    "to": 318,
                    "id": 159
                },
                {
                    "from": 319,
                    "width": 7.185894010000901,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7185894010000901,
                    "to": 320,
                    "id": 160
                },
                {
                    "from": 320,
                    "width": 7.400627390054053,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7400627390054053,
                    "to": 322,
                    "id": 161
                },
                {
                    "from": 323,
                    "width": 6.902550745143269,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6902550745143269,
                    "to": 324,
                    "id": 162
                },
                {
                    "from": 325,
                    "width": 6.71609473408229,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.671609473408229,
                    "to": 326,
                    "id": 163
                },
                {
                    "from": 327,
                    "width": 6.311990989272253,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6311990989272254,
                    "to": 328,
                    "id": 164
                },
                {
                    "from": 328,
                    "width": 6.402580475346873,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6402580475346873,
                    "to": 330,
                    "id": 165
                },
                {
                    "from": 331,
                    "width": 6.150101375510021,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6150101375510021,
                    "to": 332,
                    "id": 166
                },
                {
                    "from": 331,
                    "width": 6.672223664550106,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6672223664550107,
                    "to": 334,
                    "id": 167
                },
                {
                    "from": 334,
                    "width": 6.0598930192754015,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6059893019275402,
                    "to": 336,
                    "id": 168
                },
                {
                    "from": 334,
                    "width": 6.084669404411224,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6084669404411225,
                    "to": 338,
                    "id": 169
                },
                {
                    "from": 334,
                    "width": 6.115473580934939,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6115473580934939,
                    "to": 340,
                    "id": 170
                },
                {
                    "from": 341,
                    "width": 6.555303266566766,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6555303266566767,
                    "to": 342,
                    "id": 171
                },
                {
                    "from": 342,
                    "width": 7.331666398870597,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7331666398870598,
                    "to": 344,
                    "id": 172
                },
                {
                    "from": 345,
                    "width": 7.34557054997684,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.734557054997684,
                    "to": 346,
                    "id": 173
                },
                {
                    "from": 347,
                    "width": 6.789692445918339,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6789692445918339,
                    "to": 348,
                    "id": 174
                },
                {
                    "from": 349,
                    "width": 7.796083265929685,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7796083265929685,
                    "to": 350,
                    "id": 175
                },
                {
                    "from": 351,
                    "width": 7.476700931044624,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7476700931044624,
                    "to": 350,
                    "id": 176
                },
                {
                    "from": 353,
                    "width": 9.814666315270651,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.9814666315270651,
                    "to": 354,
                    "id": 177
                },
                {
                    "from": 355,
                    "width": 6.087522244731835,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6087522244731834,
                    "to": 356,
                    "id": 178
                },
                {
                    "from": 357,
                    "width": 6.408872815542107,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6408872815542107,
                    "to": 358,
                    "id": 179
                },
                {
                    "from": 359,
                    "width": 6.3009797589741465,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6300979758974147,
                    "to": 360,
                    "id": 180
                },
                {
                    "from": 360,
                    "width": 6.193379114970511,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6193379114970511,
                    "to": 362,
                    "id": 181
                },
                {
                    "from": 363,
                    "width": 6.163719850306176,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6163719850306176,
                    "to": 362,
                    "id": 182
                },
                {
                    "from": 365,
                    "width": 6.2198753249858205,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6219875324985821,
                    "to": 362,
                    "id": 183
                },
                {
                    "from": 367,
                    "width": 6.038139435240041,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6038139435240041,
                    "to": 363,
                    "id": 184
                },
                {
                    "from": 369,
                    "width": 6.419699336266519,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6419699336266519,
                    "to": 370,
                    "id": 185
                },
                {
                    "from": 371,
                    "width": 6.892104051264738,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6892104051264738,
                    "to": 372,
                    "id": 186
                },
                {
                    "from": 372,
                    "width": 6.3038658289654395,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6303865828965439,
                    "to": 374,
                    "id": 187
                },
                {
                    "from": 375,
                    "width": 9.892980476599094,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.9892980476599095,
                    "to": 376,
                    "id": 188
                },
                {
                    "from": 377,
                    "width": 6.095933233384583,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6095933233384583,
                    "to": 378,
                    "id": 189
                },
                {
                    "from": 379,
                    "width": 6.082417933086511,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.608241793308651,
                    "to": 378,
                    "id": 190
                },
                {
                    "from": 377,
                    "width": 6.252475923356915,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6252475923356915,
                    "to": 382,
                    "id": 191
                },
                {
                    "from": 383,
                    "width": 7.004610871295735,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7004610871295734,
                    "to": 382,
                    "id": 192
                },
                {
                    "from": 385,
                    "width": 6.512080763537606,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6512080763537605,
                    "to": 386,
                    "id": 193
                },
                {
                    "from": 387,
                    "width": 7.018282366105161,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7018282366105162,
                    "to": 388,
                    "id": 194
                },
                {
                    "from": 389,
                    "width": 6.540475018935808,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6540475018935809,
                    "to": 390,
                    "id": 195
                },
                {
                    "from": 391,
                    "width": 6.420451096899752,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6420451096899752,
                    "to": 390,
                    "id": 196
                },
                {
                    "from": 393,
                    "width": 7.248078585496117,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7248078585496117,
                    "to": 394,
                    "id": 197
                },
                {
                    "from": 395,
                    "width": 6.775341815309055,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6775341815309055,
                    "to": 394,
                    "id": 198
                },
                {
                    "from": 397,
                    "width": 7.723072747318184,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7723072747318185,
                    "to": 398,
                    "id": 199
                },
                {
                    "from": 399,
                    "width": 6.717055286442209,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6717055286442208,
                    "to": 400,
                    "id": 200
                },
                {
                    "from": 399,
                    "width": 6.869473885690692,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6869473885690691,
                    "to": 402,
                    "id": 201
                },
                {
                    "from": 403,
                    "width": 7.48966116126221,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.748966116126221,
                    "to": 404,
                    "id": 202
                },
                {
                    "from": 405,
                    "width": 8.335750233028831,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.8335750233028831,
                    "to": 406,
                    "id": 203
                },
                {
                    "from": 407,
                    "width": 9.524628311605634,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.9524628311605634,
                    "to": 408,
                    "id": 204
                },
                {
                    "from": 409,
                    "width": 6.093876563859876,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6093876563859876,
                    "to": 410,
                    "id": 205
                },
                {
                    "from": 411,
                    "width": 6.413898385045876,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.6413898385045875,
                    "to": 412,
                    "id": 206
                },
                {
                    "from": 413,
                    "width": 8.075488255121318,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.8075488255121318,
                    "to": 414,
                    "id": 207
                },
                {
                    "from": 415,
                    "width": 7.080712780494637,
                    "color": {
                        "color": "black"
                    },
                    "title": 0.7080712780494637,
                    "to": 416,
                    "id": 208
                }
            ]
        }

        return Response(data)
