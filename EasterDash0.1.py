# app.py

import dash
from dash import Dash, dcc, html, Input, Output, State, ctx, dash_table
import plotly.express as px
import pandas as pd
import pydash as _
import kagglehub
import os
import dash_bootstrap_components as dbc

df = pd.DataFrame(columns=['Name', 'Age Range', 'Out of Town?'])

# App init
app = Dash(__name__)
app.title = "Pydash Dashboard"

# Layout
app.layout = html.Div([
    html.Label("Are you from out of town?:"),
    dcc.Dropdown(
        id='dropdown',
        options=[
            {'label': 'Yes', 'value': 'Yes'},
            {'label': 'No', 'value': 'No'},
        ],
        value='No'
    ),

    html.Br(),

    html.Label("Select an Age Range:"),
    dcc.RadioItems(
        id='radio',
        options=[
            {'label': '<18', 'value': '<18'},
            {'label': '18-25', 'value': '18-25'},
            {'label': '18-25', 'value': '18-25'},
            {'label': '25-40', 'value': '25-40'},
            {'label': '>40', 'value': '>40'},
            
        ],
        value='1',
        inline=True
    ),

    html.Br(),

    html.Label("Enter Your Name:"),
    dcc.Input(
        id='inpu',
        type='text',
        placeholder='Type here...',
        value=''
    ),

    html.Button('Submit', id='submit-button', n_clicks=0),

    html.Br(), html.Br(),
    dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in df.columns],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'fontWeight': 'bold'}
    )
    html.Div(id='output')
])

# Callbacks
@app.callback(
    Output('output', 'children'),
    State('inpu','value'),
    State('radio','value'),
    State('dropdown','value'),
    Input('submit-button', 'n_clicks'),
)
def form_submission(inpu,radio,dropdown,n_clicks):
    if n_clicks > 0:
        new_row = pd.DataFrame([{'Name': inpu, 'Age Range': radio, 'Out of Town?': dropdown}])

        # Append using concat
        df = pd.concat([df, new_row], ignore_index=True)
    return ""


# Run server
if __name__ == '__main__':
    app.run(debug=True)
