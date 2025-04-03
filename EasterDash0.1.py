# app.py

import dash
from dash import Dash, dcc, html, Input, Output, State, ctx
import plotly.express as px
import pandas as pd
import pydash as _

# Sample data
df = pd.DataFrame([
    {'name': 'Alice', 'age': 30, 'role': 'dev'},
    {'name': 'Bob', 'age': 25, 'role': 'designer'},
    {'name': 'Charlie', 'age': 35, 'role': 'dev'},
    {'name': 'Diana', 'age': 40, 'role': 'manager'},
])

# App init
app = Dash(__name__)
app.title = "Pydash Dashboard"

# Layout
app.layout = html.Div([
    html.H1("Pydash + Dash Starter"),
    
    html.Label("Filter by role:"),
    dcc.Dropdown(
        id='role-dropdown',
        options=[{'label': role, 'value': role} for role in _.uniq(_.map_(df.to_dict('records'), 'role'))],
        value=None,
        placeholder="Select a role"
    ),

    html.Button("Show Grouped Data", id="group-btn", n_clicks=0),

    html.Div(id='group-output', style={'whiteSpace': 'pre-wrap', 'marginTop': '1rem'}),

    dcc.Graph(id='age-chart')
])

# Callbacks
@app.callback(
    Output('group-output', 'children'),
    Input('group-btn', 'n_clicks'),
)
def show_grouped(n):
    if n == 0:
        return ""
    grouped = _.group_by(df.to_dict('records'), 'role')
    return str(grouped)

@app.callback(
    Output('age-chart', 'figure'),
    Input('role-dropdown', 'value')
)
def update_chart(role_filter):
    if role_filter:
        filtered = _.filter_(df.to_dict('records'), lambda x: x['role'] == role_filter)
    else:
        filtered = df.to_dict('records')

    chart_df = pd.DataFrame(filtered)
    fig = px.bar(chart_df, x='name', y='age', color='role', title="Age by Name")
    return fig


# Run server
if __name__ == '__main__':
    app.run_server(debug=True)
