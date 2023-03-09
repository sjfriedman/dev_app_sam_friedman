from dash import Dash, html, dcc, callback, ctx
from dash import dash_table
import dash.dash_table.FormatTemplate as FormatTemplate
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from LiveMarketData import *

app = Dash(__name__)

# initiates data holders
stocks = {}
ohlc = {}

# sets up candle sticks
fig = go.Figure(data=[go.Candlestick()])
fig.update_xaxes({"title": "Time Interval"})
fig.update_yaxes({"title": "Stock Price Range"})


def tejas_get_stock_data( ticker, type ):
    '''
    loads stock data
    '''

    #gets ticker in uppercase    
    ticker = ticker.upper()

    # gets data and checks to make sure its a real data point
    try:
        tejas = CurrentMarket( ticker, type )
    except:
        print( "Unable to load symbol, try again." )
        return None

    if tejas.Error > 0:
        return None
    
    # creates df for data
    stock_data = {
        'Ticker': tejas.ticker,
        'AssetType': tejas.asset_type,
        'Price': tejas.Price(),
        'Change': tejas.Change(),
        'Volume': tejas.Volume(),
        'Previous Close': tejas.PreviousClose(),
        'Year': tejas.OneYearTarget(),
        'OHLC': None
    }

    # stores candlestick data
    try:
        stock_data['OHLC'] = tejas.OHLC(interval='15m')
    except:
        print('Unable to load OHLC, but stock data loaded')


    return stock_data 

# build screen layour
app.layout = html.Div(children=[
    html.H1(children='SSMIF.Dash'),

    # building fake buttons
    html.Nav(className = "nav nav-pills", children=[
        html.A('Search', className="nav-item nav-link btn", href='/search'),
        html.A('Portfolios', className="nav-item nav-link btn", href='/portfolios'),
        html.A('Screens', className="nav-item nav-link btn", href='/screens'),
        html.A('Data Sets', className="nav-item nav-link btn", href='/data-sets'),
        html.A('Algos', className="nav-item nav-link active btn", href='/algos')]) ,

    html.Div(children='''
        SSMIF.Dash - One stop shop to SSMIF Data
    '''),


    # Input table that holds stock and # of shares.
    dash_table.DataTable(
        id='input-table',
        style_cell={'padding': '5px'},
        style_header={
            'backgroundColor': 'darkgrey',
            'fontWeight': 'bold'
        },
        columns=(
            [{'id': 'Ticker', 'name': 'Ticker'},
             {'id': 'Shares', 'name': 'Shares', 'type': 'numeric' }]
        ),
        data= [{'Ticker':'','Shares': 0}],
        editable=True
    ),

    html.Hr(),

    # list of symbols
    dash_table.DataTable(
        id='output-table',
        style_cell={'padding': '5px'},
        style_header={
            'backgroundColor': 'darkgrey',
            'fontWeight': 'bold'
        },
        columns=(
            [
             {'id': 'Ticker', 'name': 'Ticker'},
             {'id': 'Shares', 'name': 'Shares'},
             {'id': 'Value', 'name': 'Value', 'type': 'numeric', 'format': FormatTemplate.money(2) },
             {'id': 'Change', 'name': 'Change'},
             {'id': 'Year', 'name': 'Year', 'type': 'numeric', 'format': FormatTemplate.money(2) },
            ]
        ),
        data = [],
        row_deletable=True
    ),

    html.Blockquote(id='selected'),

    # initiates candlestick graph
    dcc.Graph(
        id='graph',
        figure=fig
    )
])

# Dash callbacks.  This callback can work off two inputs 
#1. Entering new symbol in the input-table
#2. Clicking on X in a row in the output table deletes from output table and we need to clean up
@app.callback(
    Output('output-table', 'data'),
    Input('input-table', 'data'),
    Input('output-table','data')
    )
def loading_data(rows,tickers):
    '''
        loads and output data
    '''
    
    # analyzing selected row
    triggered_id = ctx.triggered_id
    if triggered_id == 'output-table':
        
        # Get list of tickers
        keepers = []
        for ticker in tickers:
            keepers.append(ticker['Ticker'])
        
        # find the ticker to remove
        remove = ''
        for ticker in stocks:
            if ticker not in keepers:
                remove = ticker
                break
        
        # If found one remove it from stocks and ohlc
        if remove:
            del stocks[remove]
            del ohlc[remove]
        return list(stocks.values())
    
    # if no data
    if len(rows) == 0:
        return list(stocks.values())

    # Some data but no ticker entered
    ticker = rows[0]['Ticker']
    if not ticker:
        return list(stocks.values())

    # getting data if there is
    ticker = ticker.upper()
    sd = tejas_get_stock_data( ticker, "STOCK" )
    if sd is None:
        return list(stocks.values())

    # Compute the value and add the share count
    sd['Value'] = sd['Price'] * int(rows[0]['Shares'])
    sd['Shares'] = int(rows[0]['Shares'])
    
    # updating OHLC data
    ohlc[ticker]=sd['OHLC']
    ohlc[ticker]['Dates'] = pd.to_datetime(ohlc[ticker].index)
    del sd['OHLC']

    # Add to stocks list
    stocks[ticker] = sd
    
    return list(stocks.values())

# If a row is clicked then activate the candle stick graph
@callback(
    Output('graph', 'figure'), 
    Input('output-table', 'active_cell'),
    Input('output-table', 'data'))
def update_candle_stick(active_cell, data):
    if data and active_cell:
        ticker =  data[active_cell['row']]['Ticker'];

        candle = go.Figure(data = go.Candlestick(
            x=ohlc[ticker]['Dates'],
            open=ohlc[ticker]['Open'],
            high=ohlc[ticker]['High'],
            low=ohlc[ticker]['Low'],
            close=ohlc[ticker]['Close'],
            hovertext="Symbol: " + ticker
        ))
        candle.update_layout(
            title={"text":"CandleStick for 15 Minute Interval ("+ticker+")"}
        )
        candle.update_xaxes({"title": "Time Interval"})
        candle.update_yaxes({"title": "Stock Price Range"})
        return candle
    else:
        return fig


if __name__ == '__main__':
    app.run_server(debug=True)

