from django.shortcuts import render

# Create your views here.
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

import datetime,time

import semapp.prep_data as prep_data

class TradingView(APIView):
  def get(self, request, format=None):
    ah,stats = prep_data.trading_create_dashboard_data()

    StartingDate = ah.TradeDate.iloc[0]
    EndingDate = ah.TradeDate.iloc[-1]

    #convert timestamp to timetuple
    ah['TradeDate'] = ah['TradeDate'].apply(lambda x: time.mktime(x.timetuple()))

    stats.reset_index(inplace=True)

    # build context
    context = {'StartingDate': StartingDate.strftime("%m/%d/%Y"),
               'EndingDate': EndingDate.strftime("%m/%d/%Y"),
               'StartingNAV': '${:,}'.format(int(round(ah.SOD_Nav.iloc[0],0))),
               'EndingNAV':'${:,}'.format(int(round(ah.EOD_Nav.iloc[-1],0))),
               'TimeWeightedReturn': '{:.2%}'.format(ah.Portfolio_equity_curve.iloc[-1]-1),
               'chart_data_strategy':ah[['TradeDate','Portfolio_equity_curve']].values.tolist(),
               'chart_data_benchmark':ah[['TradeDate','SP500_equity_curve']].values.tolist(),
               'benchmark_name': 'SP500',
               'stats': stats.to_dict(orient='records'),
        'file_type':"html",
        "title":"Dashboard"}

    return Response(context)
    # return render(request, 'semapp/trading_dashboard.html', context)