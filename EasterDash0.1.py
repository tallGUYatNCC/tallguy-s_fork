import dash
from dash import Dash, dcc, html, Input, Output, State, ctx, dash_table, no_update
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import os
from flask import request, make_response

delete_triggered = False  # simple in-memory guard

CSV_PATH = os.path.join(os.path.dirname(__file__), "responses.csv")
columns = ['Name', 'Age Range', 'Out of Town?', 'Christ Follower', 'Faith Decicion', 'How you found us?']

df = pd.DataFrame()
current_chart = "local"

if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, names=columns, header=0)
else:
    df = pd.DataFrame(columns=columns)

app = Dash(__name__)
app.title = "Pydash Dashboard"
app.config.suppress_callback_exceptions = True
app.prevent_initial_callbacks='initial_duplicate'


app.layout = lambda: render_layout_with_cookie()

def render_layout_with_cookie():
    submitted_cookie = request.cookies.get("submitted")
    return html.Div([
        dcc.Store(id="submission-store", data=(submitted_cookie == "true")),
        dcc.Store(id="clear-cookie", data=False),
        html.Div(id="delete-status"),
        html.Div(id="select-chart-toggle"),
        html.Div(id="output"),
        html.Div(id="form-error"),
        html.Div(id="page-container", style={
            'maxWidth': '600px',
            'margin': '0 auto',
            'padding': '2rem',
            'textAlign': 'left'
        })
    ], style={'fontFamily': 'Arial, sans-serif'})





@app.callback(
    Output("page-container", "children"),
    Input("submission-store", "data")
)
def render_layout(submitted):
    return post_submit() if submitted else pre_submit()


# Form + delete view
def pre_submit():
    return html.Div([
        html.Div([
            html.Label("Enter Your Name:", style={'fontWeight': 'bold'}),
            dcc.Input(id='inpu', type='text', placeholder='Type here...', value='', style={'width': '30%', 'outline':'1px solid black', 'marginTop':'5px', 'borderRadius':'1px', 'marginLeft':'10px'})
        ], style={'marginBottom': '1rem'}),

        html.Div([
            html.Label("Are you from out of town?:",style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='dropdown', options=[{'label': x, 'value': x} for x in ['Yes', 'No']], value='')
        ], style={'marginBottom': '1rem'}),

        html.Div([
            html.Label("Are you a christian?:",style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='christian-status', options=[{'label': x, 'value': x} for x in ['Yes', 'No']], value='')
        ], style={'marginBottom': '1rem'}),

        html.Div([
            html.Label("Did you decide to follow Christ today?:",style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='faith-decicion', options=[{'label': x, 'value': x} for x in ['Yes', 'No']], value='')
        ], style={'marginBottom': '1rem'}),

        html.Div([
        html.Label("Select Your Age:", style={'fontWeight': 'bold'}),
        dcc.Slider(
            id='age-slider',
            min=10,
            max=80,
            step=1,
            value=0,
            marks={
                10: '10',
                18: '18',
                25: '25',
                40: '40',
                60: '60',
                80: '80'
            },
            tooltip={"placement": "bottom", "always_visible": True}
        )
        ], style={'marginBottom': '1rem'}),

        html.Div([
            html.Label("How did you find out about us?:",style={'fontWeight': 'bold'}),
            dcc.Input(id='how-they-found-us', type='text', placeholder='(Optionally) Type here...', value='', style={'width': '100%', 'outline':'1px solid black', 'marginTop':'5px', 'borderRadius':'1px'})
        ], style={'marginBottom': '2rem'}),

        html.Div([
            html.Button('Submit', id='submit-button', n_clicks=0)
        ], style={'textAlign': 'center', 'marginBottom': '2rem'})
    ])

def post_submit():
    return html.Div([
        html.Div([
            html.Button('Delete responses.csv', id='delete-button', n_clicks=0, style={'color': 'red'}),
            html.Div(id='delete-status', style={'marginTop': '0.5rem', 'fontStyle': 'italic'})
        ], style={'marginBottom': '2rem'}),

        html.Div(id="select-chart-toggle", children=
            dcc.RadioItems(
                id='chart-toggle',
                options=[
                    {'label': 'Local', 'value': 'local'},
                    {'label': 'Ages', 'value': 'age'},
                    {'label': 'Christ Followers', 'value': 'christians'},
                    {'label': 'Faith Decicions', 'value': 'faithdecicion'},
                    {'label': 'Data', 'value': 'data'},
                ],
                value='local',
                inline=True
            ),
            style={'textAlign': 'center', 'marginBottom': '2rem'}
        )
    ])

@app.callback(
    Output('delete-status', 'children'),
    Output('clear-cookie', 'data'),
    Input('delete-button', 'n_clicks'),
    prevent_initial_call=True
)
def delete_csv(n_clicks):
    global df, delete_triggered

    # Hard stop if already triggered
    if delete_triggered:
        raise PreventUpdate

    # Only proceed if user truly clicked
    if ctx.triggered_id == 'delete-button' and n_clicks:
        delete_triggered = True
        if os.path.exists(CSV_PATH):
            os.remove(CSV_PATH)
            df = pd.DataFrame(columns=columns)
            request._clear_cookie = True
            return "responses.csv deleted successfully.", True
        return "responses.csv does not exist.", False

    raise PreventUpdate





# Submit form
@app.callback(
    Output('output', 'children', allow_duplicate=True),
    Output('submission-store', 'data'),
    Output('form-error', 'children'),
    Input('submit-button', 'n_clicks'),
    State('inpu','value'),
    State('age-slider', 'value'),
    State('dropdown','value'),
    State('christian-status','value'),
    State('faith-decicion','value'),
    State('how-they-found-us','value'),
    prevent_initial_call=True
)
def form_submission(n_clicks, inpu, age_val, dropdown, christian, faith, howtheyfoundus):
    global df
    if n_clicks > 0:
        request._set_cookie = True  # Flag to set cookie in response
        age_category = bin_age(age_val)
        # Trim all required fields
        required_fields = {
            "Name": inpu,
            "Age Range": age_val,
            "Out of Town?": dropdown,
            "Christ Follower": christian,
            "Faith Decicion": faith
        }

        missing = [field for field, value in required_fields.items() if not str(value).strip()]
        if missing:
            return "", False, f"⚠️ Please fill out: {', '.join(missing)}."

        # Add the row
        new_row = pd.DataFrame(
            [[inpu, age_category, dropdown, christian, faith, howtheyfoundus]],
            columns=columns
        )
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CSV_PATH, index=False)
        return chart_selection("local"), True, ""
    return "", False, ""

def bin_age(age):
    if age < 18:
        return "<18"
    elif 18 <= age <= 25:
        return "18-25"
    elif 26 <= age <= 40:
        return "25-40"
    else:
        return ">40"


# Chart switcher
@app.callback(
    Output('output', 'children'),
    Input('chart-toggle', 'value')
)
def chart_selection(chart_type):
    if chart_type == "local":
        return out_of_town()
    elif chart_type == "age":
        return age_range()
    elif chart_type == "christians":
        return christ_count()
    elif chart_type == "faithdecicion":
        return faith_decicion_count()
    else:
        return dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': str(i), 'id': str(i)} for i in df.columns],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'fontWeight': 'bold'}
        )

def out_of_town():
    count_series = df["Out of Town?"].value_counts()
    pie_df = pd.DataFrame({'Visitor': count_series.index, 'Count': count_series.values})
    fig = px.pie(pie_df, names='Visitor', values='Count')
    fig.update_traces(hovertemplate='%{value}<extra></extra>')
    return dcc.Graph(figure=fig)

def age_range():
    count_series = df["Age Range"].value_counts()
    pie_df = pd.DataFrame({'Age': count_series.index, 'Count': count_series.values})
    fig = px.pie(pie_df, names='Age', values='Count')
    fig.update_traces(hovertemplate='%{value}<extra></extra>')
    return dcc.Graph(figure=fig)

def christ_count():
    count_series = df["Christ Follower"].value_counts()
    pie_df = pd.DataFrame({'Christians': count_series.index, 'Count': count_series.values})
    fig = px.pie(pie_df, names='Christians', values='Count')
    fig.update_traces(hovertemplate='%{value}<extra></extra>')
    return dcc.Graph(figure=fig)

def faith_decicion_count():
    count_series = df["Faith Decicion"].value_counts()
    pie_df = pd.DataFrame({'Faith Decicion': count_series.index, 'Count': count_series.values})
    fig = px.pie(pie_df, names='Faith Decicion', values='Count')
    fig.update_traces(hovertemplate='%{value}<extra></extra>')
    return dcc.Graph(figure=fig)


@app.server.after_request
def apply_cookie_flags(response):
    # Set cookie when form is submitted
    if getattr(request, "_set_cookie", False):
        response.set_cookie("submitted", "true", max_age=60*60*24)  # 1 day
    # Clear cookie when delete is triggered
    if getattr(request, "_clear_cookie", False):
        response.set_cookie("submitted", "", max_age=0)
    return response




if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run(host='0.0.0.0', port=port)
