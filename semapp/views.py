from .mixins import GroupRequiredMixin
from rest_framework.response import Response
from rest_framework.views import APIView

import datetime, time
import pandas as pd
import sys, os
import numpy as np
import re
from pandas.tseries.offsets import BDay
import scipy.stats
import igraph
try: 
    from .semutils.analytics.portfolio.metrics import calculate_drawdowns
except:
    from semutils.analytics.portfolio.metrics import calculate_drawdowns

APP_ROOT = os.path.realpath(os.path.dirname(__file__))
DataDir = os.path.join(APP_ROOT, 'data')

# #for debug
# from .mixins import GroupRequiredMixin
# class APIView(object):
#  pass
# DataDir = 'data_prod'



class TradingView(GroupRequiredMixin, APIView):
    group_required = ['trading']

    def get(self, request, format=None):
        ah = pd.read_parquet(os.path.join(DataDir, 'account_history.parquet'))
        ah['Portfolio_daily_return'] = ah.PnlReturn
        ah['Portfolio_equity_curve'] = (1 + ah.CumPnl)

        benchmarks = ['SP500','SP400','SP600']

        for b in benchmarks:
            b_data = pd.read_parquet(os.path.join(DataDir, b + '.parquet'))
            ah[b + '_daily_return'] = ah.TradeDate.map(b_data.IDX_PRICE.pct_change())
            ah[b + '_equity_curve'] = (1 + ah[b + '_daily_return']).cumprod()

        stats_cols = ['Portfolio'] + [x for x in benchmarks]
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
            drawdown_series, max_drawdown, drawdown_dur, max_drawdown_dur = calculate_drawdowns(ah[c + '_equity_curve'])
            stats.loc['Max Drawdown (bps)', c] = "{0:.0f}".format(max_drawdown * 10000)
            stats.loc['Max Drawdown Days', c] = "{0:.0f}".format(max_drawdown_dur)
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


class TradingExposuresView(GroupRequiredMixin, APIView):
    group_required = ['trading']

    def get(self, request, format=None):
        ## ticker matching doesn't work well. Needs to be converted to CUSIP
        pos = pd.read_parquet(os.path.join(DataDir, 'nav_portfolio.parquet'))
        pos = pos.drop(['Sector'],axis=1)
        sm = pd.read_parquet(os.path.join(DataDir, 'sec_master.parquet'))

        pos = pos.merge(sm, on='sec_id', how='left')
        daily_nav = pos.groupby('data_date').MarketValueBase.sum()

        pos['nav'] = pos.data_date.map(daily_nav)

        #######NEED TO FIX CASH ############
        pos['weight'] = pos.MarketValueBase / pos.nav
        pos['weight_abs'] = pos.weight.abs()

        gross_ind = pos.groupby(['data_date', 'Sector', 'Industry']).weight_abs.sum().to_frame(
            'Gross')
        net_ind = pos.groupby(['data_date', 'Sector', 'Industry']).weight.sum().to_frame(
            'Net_unadj')
        net_ind = net_ind.join(gross_ind)
        net_ind['Net'] = net_ind['Net_unadj'] / net_ind['Gross']
        net_ind['Net - 1wk delta'] = net_ind.groupby(level=['Sector', 'Industry'])['Net'].diff(
            5).fillna(0)
        net_ind['Net - 1mo delta'] = net_ind.groupby(level=['Sector', 'Industry'])['Net'].diff(
            20).fillna(0)
        net_ind.reset_index(level=['Sector', 'Industry'], drop=False, inplace=True)

        gross_sec = pos.groupby(['data_date', 'Sector']).weight_abs.sum().to_frame('Gross')
        net_sec = pos.groupby(['data_date', 'Sector']).weight.sum().to_frame('Net_unadj')
        net_sec = net_sec.join(gross_sec)
        net_sec['Net'] = net_sec['Net_unadj'] / net_sec['Gross']
        net_sec['Net - 1wk delta'] = net_sec.groupby(level=['Sector'])['Net'].diff(5).fillna(0)
        net_sec['Net - 1mo delta'] = net_sec.groupby(level=['Sector'])['Net'].diff(20).fillna(0)
        net_sec.reset_index(level=['Sector'], drop=False, inplace=True)
        net_sec['Industry'] = 'All'

        max_date = pos.data_date.max()

        exposures = pd.concat([net_ind.loc[max_date], net_sec.loc[max_date]], ignore_index=True)
        exposures = exposures.drop('Net_unadj', axis=1)

        # build context
        context = {'data': exposures.to_dict(orient='records')}

        return Response(context)


class SignalsLatestView(APIView):
    def get(self, request, format=None):
        filepath = os.path.join(DataDir, 'equities_signals_latest.parquet')
        signals = pd.read_parquet(filepath)
        signals = signals[
            ['data_date', 'ticker', 'market_cap', 'Sector', 'Industry', 'SignalConfidence',
             'SignalDirection']]
        signals.market_cap.fillna(0, inplace=True)

        signals = signals[signals.Sector.notnull()]
        # build context
        context = {'data': signals.to_dict(orient='records')}

        return Response(context)


class SignalsSecIndView(APIView):
    def get(self, request, format=None):
        filepath = os.path.join(DataDir, 'equities_signals_sec_ind.parquet')
        signals = pd.read_parquet(filepath)
        signals = signals[~signals.Sector.isin(['', 'Index'])]
        context = {'data': signals.to_dict(orient='records')}
        return Response(context)


class SignalsSectorTableView(APIView):
    def post(self, request, format=None):
        sector = request.data['sector']
        filepath = os.path.join(DataDir, 'equities_signals_latest.parquet')
        signals = pd.read_parquet(filepath)  # , where='Sector=="%s"' % sector)
        signals = signals[signals.Sector == sector]
        # build context
        context = {'data': signals.to_dict(orient='records')}

        return Response(context)


class SignalsIndustryTableView(APIView):
    def post(self, request, format=None):
        industry = request.data['industry']
        filepath = os.path.join(DataDir, 'equities_signals_latest.parquet')
        signals = pd.read_parquet(filepath)  # , where='Industry=="%s"' % industry)
        signals = signals[signals.Industry == industry]
        # build context
        context = {'data': signals.to_dict(orient='records')}
        return Response(context)


class SignalsTickerView(APIView):
    def post(self, request, format=None):
        ticker = request.data['ticker']

        include_it_data = request.data['include_it_data']
        ticker = ticker.upper()

        ## find company name and cik
        sm = pd.read_parquet(os.path.join(DataDir, 'sec_master.parquet'))
        sm = sm[sm.ticker == ticker]
        if len(sm) == 1:
            comp_name = sm.iloc[0].proper_name
            cik = sm.iloc[0].cik
        else:
            return Response({'signal_data_found': False})

        filepath = os.path.join(DataDir, 'equities_signals_full.hdf')

        signal_data_columns = ['data_date', 'market_cap', 'ticker', 'Sector', 'Industry', 'close',
                               'adj_close', 'SignalConfidence']

        signals = pd.read_hdf(filepath, 'table', where='ticker=="%s"' % ticker)[signal_data_columns]
        signals = signals[signals.SignalConfidence.notnull()]
        ## Check if signal data exists
        if not len(signals):
            return Response({'signal_data_found': False})

        # build context
        context = {'ticker': ticker, 'Name': comp_name, 'CIK': cik,
                   'Sector': signals.Sector.iloc[-1],
                   'Industry': signals.Industry.iloc[-1],
                   'Market Cap': signals.market_cap.iloc[-1],
                   'signal_data': signals[['data_date', 'adj_close', 'SignalConfidence']].to_dict(orient='records'),
                   'signal_data_found': True}

        if include_it_data:
            if pd.isnull(cik):
                it_data = pd.DataFrame()
                context['it_data_found'] = False
                return Response(context)

            # get cik forms
            filepath = os.path.join(DataDir, 'sec_forms_ownership_source_full.hdf')
            forms = pd.read_hdf(filepath, 'table', where='IssuerCIK == "%s"' % cik)

            forms.sort_values('AcceptedDate', ascending=False, inplace=True)
            forms = forms[(forms.valid_purchase + forms.valid_sale) != 0]
            forms['Direction'] = 'Buy'
            forms['Direction'] = forms.Direction.where(forms.valid_purchase == 1, 'Sell')
            forms = forms[~forms.TransType.isin(['LDG', 'HO', 'RB'])]

            cols = ['SECAccNumber', 'URL', 'AcceptedDate', 'FilerName', 'InsiderTitle',
                    'Director', 'TenPercentOwner', 'TransType', 'DollarValue', 'Direction']

            forms = forms[cols].copy()
            forms.reset_index(inplace=True, drop=True)
            forms['tableIndex'] = forms.index
            forms['AcceptedDateDate'] = pd.to_datetime(forms.AcceptedDate.apply(lambda x: x.date()))

            graph_markers = signals.merge(forms, left_on='data_date', right_on='AcceptedDateDate')
            def add_count(x):
                return (pd.Series(index = x.index,data = range(len(x))))
            graph_markers['marker_count'] = graph_markers.groupby(['data_date','Direction'],as_index=False,group_keys=False).apply(lambda x: add_count(x))
            graph_markers['marker_count'] = graph_markers['marker_count'] + 1
            graph_markers = graph_markers[
                ['data_date', 'tableIndex', 'FilerName', 'TransType', 'DollarValue', 'Direction','adj_close','marker_count']]

            graph_markers.fillna(0, inplace=True)
            forms.fillna(0, inplace=True)

            context['graph_markers'] = graph_markers.to_dict(orient='records')
            context['forms_table'] = forms.to_dict(orient='records')

        return Response(context)


class CorrelationView(APIView):
    def post(self, request, format=None):
        aggregation = request.data['aggregation']
        lookback = request.data['lookback']
        corr_threshold = request.data['corr_threshold']
        graph = request.data['graph']
        if not graph:
            dislocations = pd.read_csv(DataDir + '/correlation_network_files/dislocations_' + str(
                aggregation) + 'minute_' + lookback + '_lookback.csv')
            dislocations = dislocations[dislocations.weight >= corr_threshold].reset_index(drop=True)

            dislocations = dislocations[['ticker1', 'ticker2', 'weight',
                                         'comp1_H_1day_abs_return', 'comp2_H_1day_abs_return', 'delta_1day',
                                         'comp1_H_3day_abs_return', 'comp2_H_3day_abs_return', 'delta_3day',
                                         'comp1_H_5day_abs_return', 'comp2_H_5day_abs_return', 'delta_5day']]

            dislocations = dislocations.reindex(dislocations.delta_5day.abs().sort_values(ascending=False).index)
            context = {'data': dislocations.to_dict(orient='records')}
        else:
            df_corrmat = pd.read_csv(DataDir + '/correlation_network_files/corr_matrix_' + str(
                aggregation) + 'minute_' + lookback + '_lookback.csv').set_index(keys=['Unnamed: 0'], drop=True)
            df_nodes = pd.read_csv(DataDir + '/correlation_network_files/node_info.csv')

            node_list = pd.DataFrame(df_corrmat.index.tolist()).reset_index(drop=False).rename(
                columns={'index': 'node_id', 0: 'ticker'})

            df_list = df_corrmat.unstack()

            df_list = pd.DataFrame(df_list, columns=['weight'])
            df_list.index.names = ['ticker1', 'ticker2']
            df_list = df_list.reset_index(drop=False)

            df_list = df_list[df_list.weight != 1].copy()

            df_list = pd.merge(df_list, node_list, left_on=['ticker1'], right_on=['ticker'], how='outer').drop(
                labels=['ticker1', 'ticker'], axis=1).rename(columns={'node_id': 'node1'})
            df_list = pd.merge(df_list, node_list, left_on=['ticker2'], right_on=['ticker'], how='outer').drop(
                labels=['ticker2', 'ticker'], axis=1).rename(columns={'node_id': 'node2'})
            df_list = df_list[['node1', 'node2', 'weight']].copy()

            df_list = df_list[(df_list.weight >= corr_threshold) | (df_list.weight <= -1 * corr_threshold)].copy()

            edge_list = df_list[['node1', 'node2']].values.tolist()

            g = igraph.Graph()

            g.add_vertices(node_list.node_id.max() + 1)
            g.add_edges(edge_list)
            weight_list = [abs(i) for i in df_list.weight.tolist()]
            g.es['weight'] = weight_list

            mst_edge_ids = g.spanning_tree(weights=weight_list, return_tree=False)
            mst_edges_list = [g.get_edgelist()[i] for i in mst_edge_ids]
            mst_edges_weights = [g.es['weight'][i] for i in mst_edge_ids]

            mst_edges = pd.DataFrame(mst_edges_list, columns=['node1', 'node2'])
            mst_edges = pd.merge(mst_edges, pd.DataFrame(mst_edges_weights, columns=['weight']), left_index=True,
                                 right_index=True)

            mst_edges = pd.merge(mst_edges, node_list, left_on='node1', right_on='node_id').drop(
                labels=['node_id', 'node1'], axis=1)
            mst_edges = pd.merge(mst_edges, node_list, left_on='node2', right_on='node_id').drop(
                labels=['node_id', 'node2'], axis=1)

            mst_edges = mst_edges.rename(columns={'ticker_x': 'ticker1', 'ticker_y': 'ticker2'})
            mst_edges = mst_edges[['ticker1', 'ticker2', 'weight']].copy()

            # mst_edges = pd.merge(mst_edges, df_nodes, left_on='ticker1', right_on='ticker').rename(columns={'comp_name':'comp_name1','Sector':'comp1_sector','Industry':'comp1_industry','Industry Group':'comp1_industry_group'}).drop(labels=['ticker'], axis=1)

            # mst_edges = pd.merge(mst_edges, df_nodes, left_on='ticker2', right_on='ticker').rename(columns={'comp_name':'comp_name2','Sector':'comp2_sector','Industry':'comp2_industry','Industry Group':'comp2_industry_group'}).drop(labels=['ticker'], axis=1)

            mst_nodes = list(set(mst_edges.ticker1.unique().tolist() + mst_edges.ticker2.unique().tolist()))
            mst_nodes = df_nodes[df_nodes.ticker.isin(mst_nodes)].reset_index(drop=True)

            # mst_edges.to_csv('./sp500_mst_edges_minute.csv', index=False)
            # mst_nodes.to_csv('./sp500_mst_nodes_minute.csv', index=False)

            nodes, edges = self.create_graph_data(mst_nodes, mst_edges)
            context = {'nodes': nodes.to_dict(orient='records'),
                       'edges': edges.to_dict(orient='records')}

        return Response(context)

    def create_graph_data(self, nodes, edges):
        colors = {'Industrials': 'LightBlue',
                  'Health Care': 'PaleGoldenRod',
                  'Financials': 'Crimson',
                  'Consumer Staples': 'Lavender',
                  'Consumer Discretionary': 'Wheat',
                  'Utilities': 'GreenYellow',
                  'Information Technology': 'GoldenRod',
                  'Energy': 'WhiteSmoke',
                  'Materials': 'LightSlateGray',
                  'Real Estate': 'Lime',
                  'Telecommunication Services': 'Gold'}

        nodes = nodes.drop('Industry Group', axis=1)
        nodes = nodes.rename(columns={'ticker': 'label', 'comp_name': 'name'})
        nodes['title'] = nodes.apply(lambda x: 'Name: %s<br>Sec: %s<br> ind: %s' % (x['name'], x.Sector, x.Industry),
                                     axis=1)
        nodes['color'] = nodes.Sector.map(colors)
        nodes['x'] = 1
        nodes['y'] = nodes['x']
        nodes['id'] = nodes.index + 1
        nodes['radius'] = 10
        nodes['color'] = nodes.color.apply(lambda x: {'background': x})

        edges['from'] = edges.ticker1.map(nodes.set_index('label')['id'])
        edges['to'] = edges.ticker2.map(nodes.set_index('label')['id'])
        edges = edges[['from', 'to', 'weight']].copy()
        edges.columns = ['from', 'to', 'title']
        edges.title = edges.title.round(2)
        edges['width'] = edges.title * 10
        edges['id'] = edges.index + 1
        edges['color'] = 'black'
        edges['color'] = edges.color.apply(lambda x: {'color': x})

        return (nodes, edges)


class NetworkView(APIView):
    def get(self, request, format=None):
        colors = {"Computer and Technology": "LightBlue",
                  "Medical": "PaleGoldenRod",
                  "Transportation": "Chocolate",
                  "Business Services": "Crimson",
                  "Utilities": "Lavender",
                  "Finance": "Wheat",
                  "Industrial PRODUCTS": "GreenYellow",
                  "Multi-Sector Conglomerates": "GoldenRod",
                  "Auto-Tires-Trucks": "WhiteSmoke",
                  "Construction": "LightSlateGray",
                  "Oils-Energy": "Lime",
                  "Basic Materials": "Magenta",
                  "Retail-Wholesale": "Gold",
                  "Consumer Staples": "Orange",
                  "Aerospace": "Peru",
                  "Consumer Discretionary": "MintCream"}

        nodes = pd.read_csv(DataDir + '/sp500_mst_nodes.csv')
        nodes = nodes.drop('zacks_x_ind_desc', axis=1)
        nodes = nodes.rename(columns={'ticker': 'label', 'comp_name': 'name', 'Sector': 'Sector',
                                      'Industry': 'industry'})
        nodes['title'] = nodes.apply(lambda x: 'Name: %s<br>Sec: %s<br> ind: %s' % (x['name'], x.Sector, x.industry),
                                     axis=1)
        nodes['color'] = nodes.Sector.map(colors)
        nodes['x'] = 1
        nodes['y'] = nodes['x']
        nodes['id'] = nodes.index + 1
        nodes['radius'] = 10
        nodes['color'] = nodes.color.apply(lambda x: {'background': x})

        edges = pd.read_csv(DataDir + '/sp500_mst_edges.csv')
        edges['from'] = edges.ticker1.map(nodes.set_index('label')['id'])
        edges['to'] = edges.ticker2.map(nodes.set_index('label')['id'])
        edges = edges[['from', 'to', 'weight']]
        edges.columns = ['from', 'to', 'title']
        edges.title = edges.title.round(2)
        edges['width'] = edges.title * 10
        edges['id'] = edges.index + 1
        edges['color'] = 'black'
        edges['color'] = edges.color.apply(lambda x: {'color': x})

        context = {'my_nodes': nodes.to_dict(orient='records'),
                   'my_edges': edges.to_dict(orient='records')}

        return Response(context)


class FactorReturns(APIView):
    def post(self, request, format=None):
        start_date = request.data['start_date']
        end_date = request.data['end_date']
        selected_factors = request.data['selected_factors']
        returns = pd.read_parquet(os.path.join(DataDir,'factor_returns.parquet'))

        style_factors = ['Dividend_Yield', 'Earnings_Yield',
                         'Exchange_Rate_Sensitivity', 'Growth', 'Leverage',
                         'Liquidity', 'Market_Sensitivity', 'Medium_Term_Momentum',
                         'MidCap', 'Profitability', 'Size', 'Value', 'Volatility','Short_Term_Momentum']
        new_names = []
        for c in returns.columns:
            if c in style_factors:
                new_names.append('Style: '+c)
            elif c == 'Market_Intercept':
                new_names.append('Market: Market_Intercept')
            else:
                new_names.append('Industry: '+c)

        returns.columns = new_names
        returns = returns 

        available_dates = returns.index.tolist()
        all_factors = sorted(returns.columns.tolist(), reverse=True)

        start_date = returns.index.min() if start_date == '' else pd.to_datetime(start_date)
        end_date = returns.index.min() if end_date == '' else pd.to_datetime(end_date)

        selected_factors = selected_factors if len(selected_factors) else ['Style: Growth', 'Style: Value']
        returns = returns[start_date:end_date][selected_factors]
        returns.iloc[0] = 0
        #returns = (1 + returns).cumprod()

        returns.reset_index(inplace=True)

        # construct factor group table
        f = os.path.join(DataDir,'AXUS4-SH.hry.csv')
        df = pd.read_csv(f,sep='|',comment='#',header=None)
        f_o = open(f,mode='r')
        file_data = f_o.readlines()
        for l in file_data:
            if 'Columns' in l:
                columns = re.sub('#Columns: ','',l.rstrip()).split('|')
        df.columns = columns

        sectors = df[df.Level=='Sectors']
        industry_groups = df[df.Level=='Industry Groups']
        industries = df[df.Level=='Industries']

        industries = industries.rename(columns = {'Parent':'Industry Groups','Name':'Industries'})

        industries['Sectors'] = industries['Industry Groups'].map(industry_groups.set_index('Name')['Parent'])
        industries['Sectors'] = industries['Sectors'].str.replace('-S','')

        df = industries[['Sectors','Industries']].copy()
        df.columns = ['Group','Factor']
        df = df.sort_values(['Group','Factor'])

        sf = pd.DataFrame(style_factors,columns = ['Factor'])
        sf['Group'] = 'Style'
        sf = sf.sort_values(['Group','Factor'])

        df = pd.concat([sf,df],ignore_index=True)[['Group','Factor']]

        # create context
        context = {'all_factors': all_factors, 'available_dates': available_dates,
                   'data': returns.to_dict(orient='records'),'factor_table_data':df.to_dict(orient='records')}

        return Response(context)
