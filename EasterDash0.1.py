# app.py

import dash
from dash import Dash, dcc, html, Input, Output, State, ctx
import plotly.express as px
import pandas as pd
import pydash as _
import kagglehub
import os
import dash_bootstrap_components as dbc

# Download latest version
path = kagglehub.dataset_download("sujaykapadnis/nfl-stadium-attendance-dataset")

#print("Path to dataset files:", path)
csv_path = os.path.join(path, "attendance.csv")

# Sample data
df = pd.read_csv(csv_path)
df_sorted = df.sort_values(by='year', ascending=False)

# App init
app = Dash(__name__)
app.title = "Pydash Dashboard"

# Layout
app.layout = html.Div([
    html.Label("Choose an option from the dropdown:"),
    dcc.Dropdown(
        id='dropdown',
        options=[
            {'label': 'Option A', 'value': 'A'},
            {'label': 'Option B', 'value': 'B'},
            {'label': 'Option C', 'value': 'C'}
        ],
        value='A'
    ),

    html.Br(),

    html.Label("Pick one radio option:"),
    dcc.RadioItems(
        id='radio',
        options=[
            {'label': 'Radio 1', 'value': '1'},
            {'label': 'Radio 2', 'value': '2'}
        ],
        value='1',
        inline=True
    ),

    html.Br(),

    html.Label("Enter some text:"),
    dcc.Input(
        id='inpu',
        type='text',
        placeholder='Type here...',
        value=''
    ),

    html.Button('Submit', id='submit-button', n_clicks=0),

    html.Br(), html.Br(),

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
        return f"Submitted → Dropdown: {dropdown}, Radio: {radio}, Input: {inpu}"
    return ""


# Run server
if __name__ == '__main__':
    app.run(debug=True)
