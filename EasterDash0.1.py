import dash
from dash import Dash, dcc, html, Input, Output, State, ctx, dash_table, no_update, MATCH
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import os
from flask import request, make_response
# auth_setup.py (optional) or top of app.py
import os
from functools import wraps
from flask import redirect, session, url_for, request
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID", "your-client-id")
AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET", "your-client-secret")
AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "your-auth0-domain.auth0.com")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "super-secret-key")



def is_admin_user():
    return session.get('profile', {}).get('email') == os.getenv("ADMIN_EMAIL")


oauth = OAuth()
auth0 = oauth.register(
    'auth0',
    client_id=os.getenv('AUTH0_CLIENT_ID'),
    client_secret=os.getenv('AUTH0_CLIENT_SECRET'),
    api_base_url=f"https://{os.getenv('AUTH0_DOMAIN')}",
    access_token_url=f"https://{os.getenv('AUTH0_DOMAIN')}/oauth/token",
    authorize_url=f"https://{os.getenv('AUTH0_DOMAIN')}/authorize",
    client_kwargs={
        'scope': 'openid profile email'
    },
    server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration"
)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


delete_triggered = False  # simple in-memory guard

CSV_PATH = os.path.join(os.path.dirname(__file__), "responses.csv")
columns = ['Name', 'Age Range', 'Local', 'Christ Follower', 'Faith Decicion', 'How you found us?']

df = pd.DataFrame()
current_chart = "local"

if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, names=columns, header=0)
else:
    df = pd.DataFrame(columns=columns)

app = Dash(__name__, routes_pathname_prefix="/")
server = app.server
oauth.init_app(server)
app.server.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-dev-key")
app.title = "Pydash Dashboard"
prevent_initial_call='initial_duplicate'
app.prevent_initial_callbacks = False
app.config.suppress_callback_exceptions = True

app.layout = lambda: render_layout_with_cookie()

from urllib.parse import urlparse, parse_qs

def render_layout_with_cookie():
    submitted_cookie = request.cookies.get("submitted")
    return html.Div([
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="submission-store", data="true" if submitted_cookie == "true" else "false"),
        dcc.Store(id="loading-flag", data=False),
        dcc.Store(id="clear-cookie", data=False),
        dcc.Store(id="chart-request", data="local"),
        dcc.Store(id="is-admin", data=False),  # default False, will be updated later
        html.Div(id="auth-buttons", style={'textAlign': 'right', 'marginBottom': '1rem'}),  # <- added
        html.Div(id="delete-status"),
        html.Div(id="form-error"),
        html.Div(id="page-container", style={
            'maxWidth': '600px',
            'margin': '0 auto',
            'padding': '2rem',
            'textAlign': 'left'
        })
    ], style={'fontFamily': 'Arial, sans-serif'})


@app.callback(
    Output("auth-buttons", "children"),
    Input("url", "search")
)
def show_auth_buttons(search):
    query = parse_qs(search.lstrip("?"))
    is_admin_query = query.get("admin", ["false"])[0].lower() == "true"

    if not is_admin_query:
        return ""

    if "profile" in session:
        return html.A("Logout", href="/logout", style={"marginRight": "10px"})
    else:
        return html.A("Login", href="/login?next=/?admin=true")




@app.callback(
    Output('is-admin', 'data'),
    Input('url', 'search')
)
def extract_admin_flag(search):
    query = parse_qs(search.lstrip('?'))
    return query.get('admin', ['false'])[0].lower() == 'true'




@app.callback(
    Output("page-container", "children"),
    Input("submission-store", "data")
)
def render_layout(submitted):
    print("Submission store data:", submitted)  # Add this line to debug
    if submitted == "true":
        return post_submit()
    return pre_submit()




# Form + delete view
def pre_submit():
    return html.Div([
        html.Div([
            html.Label("Enter Your Name:", style={'fontWeight': 'bold'}),
            dcc.Input(id='inpu', type='text', placeholder='Type here...', value='', style={'width': '30%', 'outline':'1px solid black', 'marginTop':'5px', 'borderRadius':'1px', 'marginLeft':'10px'})
        ], style={'marginBottom': '1rem'}),

        html.Div([
            html.Label("Are you from DC?:",style={'fontWeight': 'bold'}),
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


@app.callback(
    Output('admin-panel-wrapper-container', 'children'),
    Input('submission-store', 'data')
)
def show_admin_if_allowed(_):
    if is_admin_user():
        return html.Div([
            html.Div(id="admin-panel-wrapper", children=[
                html.Hr(),
                html.H4("Admin Tools"),
                dcc.Download(id="download"),
                html.Div([
                    html.Button("Download CSV", id="download-btn", className="custom-button"),
                    html.Button("View Data", id="data_button", className="custom-button"),
                    html.Button('Delete responses.csv', id='delete-button', n_clicks=0, style={'color': 'red'},className="custom-button-delete"),
                    html.Div(id='delete-status', style={'marginTop': '0.5rem', 'fontStyle': 'italic'})
                ], style={'marginBottom': '2rem','textAlign':'center'}),
            ])
        ], style={'textAlign':'center'})
    return ""





def post_submit():
    return html.Div([
        html.Div(
            dcc.Loading(
                id="loading-chart",
                type="circle",  # or "dot", "default"
                children=html.Div(id="chart-output")  # ← IMPORTANT
            )
        ),
        html.Br(),
        html.Div(id="select-chart-toggle", children=
            dcc.RadioItems(
                id='chart-toggle',
                options=[
                    {'label': 'Geographic', 'value': 'local'},
                    {'label': 'Ages', 'value': 'age'},
                    {'label': 'Christ Followers', 'value': 'christians'},
                    {'label': 'Faith Decicions', 'value': 'faithdecicion'},
                ],
                value='local',
                inline=True,
                className="graph-radio-group"),
            style={'textAlign': 'center', 'marginBottom': '2rem'}
        ),
        html.Div(id="admin-panel-wrapper-container")
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


import time

@app.callback(
    Output('chart-output', 'children'),
    Output('loading-flag', 'data', allow_duplicate=True),
    Input('chart-request', 'data'),
    prevent_initial_call=True
)
def update_chart_view(chart_type):
    # Optional delay to simulate loading — can be removed
    time.sleep(0.5)

    return get_chart_layout(chart_type), False






@app.callback(
    Output('chart-request', 'data', allow_duplicate=True),
    Output('submission-store', 'data'),
    Output('form-error', 'children'),
    Output('loading-flag', 'data', allow_duplicate=True),  # New output to trigger loading
    Input('submit-button', 'n_clicks'),
    State('inpu', 'value'),
    State('age-slider', 'value'),
    State('dropdown', 'value'),
    State('christian-status', 'value'),
    State('faith-decicion', 'value'),
    State('how-they-found-us', 'value'),
    prevent_initial_call=True
)
def form_submission(n_clicks, inpu, age_val, dropdown, christian, faith, howtheyfoundus):
    print("Form callback triggered!", n_clicks, inpu, age_val, dropdown, christian, faith, howtheyfoundus)

    if n_clicks > 0:
        request._set_cookie = True
        age_category = bin_age(age_val)
        required_fields = {
            "Name": inpu,
            "Age Range": age_val,
            "Local": dropdown,
            "Christ Follower": christian,
            "Faith Decicion": faith
        }

        missing = [field for field, value in required_fields.items() if not str(value).strip()]
        if missing:
            return no_update, False, f"⚠️ Please fill out: {', '.join(missing)}.", False

        new_row = pd.DataFrame(
            [[inpu, age_category, dropdown, christian, faith, howtheyfoundus]],
            columns=columns
        )

        global df
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CSV_PATH, index=False)

        # Set loading to true after successful submission
        return "local", "true", "", True

    return no_update, False, "", False



def bin_age(age):
    if age < 18:
        return "<18"
    elif 18 <= age <= 25:
        return "18-25"
    elif 26 <= age <= 40:
        return "25-40"
    else:
        return ">40"


@app.callback(
    Output("chart-request", "data", allow_duplicate=True),
    Output("loading-flag", "data", allow_duplicate=True),
    Input("chart-toggle", "value"),
    prevent_initial_call=True
)
def handle_chart_toggle(toggle_value):
    return toggle_value, True


@app.callback(
    Output("chart-request", "data", allow_duplicate=True),
    Output("loading-flag", "data", allow_duplicate=True),
    Input("data_button", "n_clicks"),
    prevent_initial_call=True
)
def handle_data_click(n_clicks):
    if n_clicks:
        return "data", True
    raise PreventUpdate



    

def get_chart_layout(chart_type):
    if chart_type == "local":
        return local_counter()
    elif chart_type == "age":
        return generate_pie_chart_from_column("Age Range", "Age Distribution")
    elif chart_type == "christians":
        return generate_pie_chart_from_column("Christ Follower", "Christ Follower Count")
    elif chart_type == "faithdecicion":
        return generate_pie_chart_from_column("Faith Decicion", "Faith Decision Count")
    elif chart_type == "data":
        return dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': str(i), 'id': str(i)} for i in df.columns],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'fontWeight': 'bold'}
        )
    else:
        return html.Div("Unknown chart type.")




def local_counter():
    label_map = {'Yes': 'Local', 'No': 'Visitor'}
    renamed_series = df["Local"].map(label_map)

    count_series = renamed_series.value_counts()
    pie_df = pd.DataFrame({'Visitor': count_series.index, 'Count': count_series.values})

    fig = px.pie(
        pie_df,
        names='Visitor',
        values='Count',
        color='Visitor',
        color_discrete_map={'Local': 'blue', 'Visitor': 'purple'},
        hole=0.1
    )

    return dcc.Graph(figure=style_pie_chart(fig, "Local vs Visitor"), style={'width': '100%'})


def generate_pie_chart_from_column(column_name, title):
    global df
    if column_name not in df.columns or df.empty:
        return html.Div("No data available.", style={'textAlign': 'center', 'color': 'gray'})

    count_series = df[column_name].value_counts()
    
    # Automatically cycle through 6 colors
    default_colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3']
    
    fig = px.pie(
        pd.DataFrame({'Label': count_series.index, 'Count': count_series.values}),
        names='Label',
        values='Count',
        hole=0.1,
        color_discrete_sequence=default_colors
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='%{label}: %{value}<extra></extra>'
    )
    
    fig.update_layout(
        title_text=title,
        title_x=0.5,
        legend_title_text='',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=50, b=80, l=30, r=30),
        height=400
    )
    
    return dcc.Graph(figure=fig)


from dash import MATCH

@app.callback(
    Output('admin-code', 'style'),
    Input('admin-toggle', 'n_clicks'),
    prevent_initial_call=True
)
def show_code_input(n):
    return {'display': 'inline-block', 'marginTop': '10px'}


ADMIN_CODE = "letmein123"  # You can make this env-based for real security

@app.callback(
    Output('admin-panel', 'children'),
    Input('admin-code', 'value'),
    prevent_initial_call=True
)
def grant_admin_access(code):
    if code == ADMIN_CODE:
        return html.Div([
            html.Hr(),
            html.H4("Admin Tools"),
            html.Button("Download CSV", id="download-btn", type="button", className="custom-button", classNameProp=True),
            html.Button("View Data", id="data_button", className="custom-button", classNameProp=True, type="button"),
            dcc.Download(id="download"),
            html.Div([
            html.Button('Delete responses.csv', id='delete-button', n_clicks=0, style={'color': 'red'}, className="custom-button", classNameProp=True),
            html.Div(id='delete-status', style={'marginTop': '0.5rem', 'fontStyle': 'italic'})
            ], style={'marginBottom': '2rem'}),
        ], id='admin-stuff')
    raise PreventUpdate



@app.callback(
        Output("download", "data"),
        Input('download-btn','n_clicks'),
        prevent_initial_call=True
)
def download_data(n_clicks):
    if n_clicks > 0:
        return dcc.send_data_frame(df.to_csv, "responses.csv", index=False)

@app.server.after_request
def apply_cookie_flags(response):
    # Set cookie when form is submitted
    if getattr(request, "_set_cookie", False):
        response.set_cookie("submitted", "true", max_age=60*60*24)  # 1 day
    # Clear cookie when delete is triggered
    if getattr(request, "_clear_cookie", False):
        response.set_cookie("submitted", "", max_age=0)
    return response

def style_pie_chart(fig, title):
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='%{label}: %{value}<extra></extra>'
    )
    fig.update_layout(
        title_text=title,
        title_x=0.5,
        legend_title_text='',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=50, b=80, l=30, r=30),
        height=400
    )
    return fig

@server.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True, _scheme='https')
    next_url = request.args.get('next', '/?admin=true')  # default to /?admin=true
    session['next_url'] = next_url
    return auth0.authorize_redirect(redirect_uri=redirect_uri)

@server.route('/callback')
def callback():
    try:
        auth0.authorize_access_token()
        resp = auth0.get('userinfo')
        userinfo = resp.json()
        print("Auth0 Userinfo:", userinfo)  # <- Inspect this

        session['profile'] = {
            'user_id': userinfo.get('sub'),
            'name': userinfo.get('name') or userinfo.get('nickname'),
            'email': userinfo.get('email', 'no-email@unknown.fake')  # fallback
        }

        next_url = session.pop('next_url', '/')
        return redirect(next_url)
    except Exception as e:
        import traceback
        print("Callback error:", str(e))
        traceback.print_exc()
        return f"Callback failed: {e}", 500




@server.route('/logout')
def logout():
    session.clear()
    return redirect(
        f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?" +
        f"returnTo={url_for('index', _external=True, _scheme='https')}&client_id={os.getenv('AUTH0_CLIENT_ID')}"
)

@server.route('/')
def index():
    return "App is running"




if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run(host='0.0.0.0', port=port, use_reloader=True)

