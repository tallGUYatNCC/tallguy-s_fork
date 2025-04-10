import dash
from dash import (
    Dash,
    dcc,
    html,
    Input,
    Output,
    State,
    ctx,
    dash_table,
    no_update,
    MATCH,
    callback_context,
    ALL,
)

from dash.exceptions import PreventUpdate
from dash import ClientsideFunction
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
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID", "your-client-id")
AUTH0_CLIENT_SECRET = os.environ.get(
    "AUTH0_CLIENT_SECRET", "your-client-secret"
)
AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "your-auth0-domain.auth0.com")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "super-secret-key")

form_stlye = {""}
button_style = {
    "width": "100%",
    "padding": "10px",
    "fontSize": "16px",
    "border": "none",
    "borderRadius": "5px",
    "backgroundColor": "#007bff",
    "color": "#fff",
    "textAlign": "left",
}


def is_admin_user():
    allowed_admins = os.getenv("ADMIN_EMAILS", "").split(",")
    user_email = session.get("profile", {}).get("email")
    return user_email in [email.strip().lower() for email in allowed_admins]


# O Auth integration
oauth = OAuth()
auth0 = oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    api_base_url=f"https://{os.getenv('AUTH0_DOMAIN')}",
    access_token_url=f"https://{os.getenv('AUTH0_DOMAIN')}/oauth/token",
    authorize_url=f"https://{os.getenv('AUTH0_DOMAIN')}/authorize",
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
)


# Redirects if Oauth
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "profile" not in session:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated


CSV_PATH = os.path.join(os.path.dirname(__file__), "responses.csv")
columns = [
    "Name",
    "Age Range",
    "Age",
    "Local",
    "Country",
    "State",
    "Christ Follower",
    "Faith Decicion",
    "How you found us?",
]

df = pd.DataFrame()
current_chart = "local"

def load_df():
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM responses", conn)
    
df = load_df()



app = Dash(__name__, routes_pathname_prefix="/")
server = app.server
oauth.init_app(server)
app.server.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-dev-key")
app.title = "Pydash Dashboard"
prevent_initial_call = "initial_duplicate"
app.prevent_initial_callbacks = False
app.config.suppress_callback_exceptions = True


app.layout = lambda: render_layout_with_cookie()

from urllib.parse import urlparse, parse_qs


def render_layout_with_cookie():
    submitted_cookie = request.cookies.get("submitted", "false")
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            html.Div(id="dev-cookie-status-wrapper"),
            dcc.Store(id="submission-store", data=submitted_cookie),
            dcc.Store(id="loading-flag", data=False),
            dcc.Store(id="chart-request", data="local"),
            dcc.Store(id="is-admin", data=False),
            html.Div(id="auth-buttons", className="auth-buttons"),
            html.Div(id="delete-status"),
            html.Div(id="form-error"),
            html.Div(id="page-container", className="page-container"),
        ],
        className="main-layout",
    )


# Callback for the admin URL - Adds login button if so.
@app.callback(Output("auth-buttons", "children"), Input("url", "search"))
def show_auth_buttons(search):
    query = parse_qs(search.lstrip("?"))
    is_admin_query = query.get("admin", ["false"])[0].lower() == "true"

    if not is_admin_query:
        return ""

    if "profile" in session:
        return html.A("Logout", href="/logout", style={"marginRight": "10px"})
    else:
        return html.A("Login", href="/login?next=/?admin=true")


# Check if user is admin
@app.callback(Output("is-admin", "data"), Input("url", "search"))
def extract_admin_flag(search):
    query = parse_qs(search.lstrip("?"))
    return query.get("admin", ["false"])[0].lower() == "true"


# Country Integration:
def get_country_list():
    try:
        response = requests.get("https://restcountries.com/v3.1/all")
        countries = sorted([c["name"]["common"] for c in response.json()])

        if "United States" in countries:
            countries.remove("United States")
        countries.insert(0, "United States")
        return countries
    except Exception as e:
        print("Failed to fetch countries:", str(e))
        return [
            "United States",
            "Canada",
            "United Kingdom",
            "Other",
        ]  # Fallback


import requests


# Callback for state dropdown
@app.callback(
    Output("state-dropdown-container", "children"),
    Input("country-dropdown", "value"),
)
def show_state_dropdown(selected_country):
    if not selected_country:
        raise PreventUpdate

    try:
        res = requests.post(
            "https://countriesnow.space/api/v0.1/countries/states",
            json={"country": selected_country},
        )
        data = res.json()
        print("CountriesNow API Response:", data)

        if not data or data.get("error", True) or "data" not in data:
            print("❌ Invalid or error response")
            return html.Div("Could not load states", style={"color": "red"})

        states = data["data"].get("states", [])
        if selected_country == "United States":
            states.append(
                {"name": "District of Columbia"}
            )  # 👈 Add DC manually

        if not states:
            return ""

        return html.Div(
            [
                html.Label("State/Province:", style={"fontWeight": "bold"}),
                dcc.Dropdown(
                    id="state-dropdown",
                    options=[
                        {"label": s["name"], "value": s["name"]}
                        for s in states
                    ],
                    placeholder="Select a state...",
                ),
            ],
            style={"marginTop": "1rem"},
        )

    except Exception as e:
        print("❌ API request failed:", str(e))
        return html.Div("Could not load states", style={"color": "red"})


@app.callback(
    Output("page-container", "children"), Input("submission-store", "data")
)
def render_layout(submitted):
    print("Submission store data:", submitted)  # Add this line to debug
    if submitted == "true":
        return post_submit()
    return pre_submit()


# This is the form before a user submits it
def pre_submit():
    return html.Div(
        [
            html.Div(
                [
                    html.Label(
                        "Enter Your Name:", style={"fontWeight": "bold"}
                    ),
                    dcc.Input(
                        id="inpu",
                        type="text",
                        placeholder="Type here...",
                        value="",
                        className="form-input",
                    ),
                ],
                style={"marginBottom": "1rem"},
            ),
            html.Div(
                [
                    html.Label(
                        "Where are you from?", style={"fontWeight": "bold"}
                    ),
                    dcc.Dropdown(
                        id="country-dropdown",
                        options=[
                            {"label": c, "value": c}
                            for c in get_country_list()
                        ],
                        value="",
                        style={"marginBottom": "1rem"},
                    ),
                    html.Div(id="state-dropdown-container"),
                ],
                style={"marginBottom": "2rem"},
            ),
            html.Div(
                [
                    html.Label(
                        "Are you a christian?:", style={"fontWeight": "bold"}
                    ),
                    dcc.Dropdown(
                        id="christian-status",
                        options=[
                            {"label": x, "value": x} for x in ["Yes", "No"]
                        ],
                        value="",
                    ),
                ],
                style={"marginBottom": "1rem"},
            ),
            html.Div(
                [
                    html.Label(
                        "Did you decide to follow Christ today?:",
                        style={"fontWeight": "bold"},
                    ),
                    dcc.Dropdown(
                        id="faith-decicion",
                        options=[
                            {"label": x, "value": x} for x in ["Yes", "No"]
                        ],
                        value="",
                    ),
                ],
                style={"marginBottom": "1rem"},
            ),
            html.Div(
                [
                    html.Label(
                        "Select Your Age:", style={"fontWeight": "bold"}
                    ),
                    dcc.Slider(
                        id="age-slider",
                        min=10,
                        max=80,
                        step=1,
                        value=0,
                        marks={
                            10: "10",
                            18: "18",
                            25: "25",
                            40: "40",
                            60: "60",
                            80: "80",
                        },
                        tooltip={
                            "placement": "bottom",
                            "always_visible": True,
                        },
                    ),
                ],
                style={"marginBottom": "1rem"},
            ),
            html.Div(
                [
                    html.Label(
                        "How did you find out about us?:",
                        style={"fontWeight": "bold"},
                    ),
                    dcc.Input(
                        id="how-they-found-us",
                        type="text",
                        placeholder="(Optionally) Type here...",
                        value="",
                        className="form-input",
                    ),
                ],
                style={"marginBottom": "2rem"},
            ),
            html.Div(
                [
                    html.Button(
                        "Submit",
                        id="submit-button",
                        n_clicks=0,
                        className="custom-button",
                    )
                ],
                style={"textAlign": "center", "marginBottom": "2rem"},
            ),
        ]
    )


@app.callback(
    Output("admin-panel-wrapper-container", "children"),
    Input("submission-store", "data"),
)
def show_admin_if_allowed(_):
    if is_admin_user():
        return html.Div(
            [
                html.Div(
                    id="admin-panel-wrapper",
                    children=[
                        html.Hr(),
                        html.H4("Admin Tools"),
                        dcc.Download(id="download"),
                        html.Div(
                            [
                                html.Button(
                                    "Download CSV",
                                    id="download-btn",
                                    className="custom-button",
                                ),
                                html.Button(
                                    "View Data",
                                    id="data_button",
                                    className="custom-button",
                                ),
                                html.Button(
                                    "Clear Cookies (Dev)",
                                    id="dev-clear-cookies",
                                    n_clicks=0,
                                    className="custom-button",
                                ),
                                html.Button(
                                    "Delete responses.csv",
                                    id="delete-button",
                                    n_clicks=0,
                                    style={"color": "red"},
                                    className="custom-button-delete",
                                ),
                                html.Div(
                                    id="delete-status",
                                    style={
                                        "marginTop": "0.5rem",
                                        "fontStyle": "italic",
                                    },
                                ),
                            ],
                            style={
                                "marginBottom": "2rem",
                                "textAlign": "center",
                            },
                        ),
                    ],
                )
            ],
            style={"textAlign": "center"},
        )
    return ""


def post_submit():
    return html.Div(
        [
            html.Div(
                [
                    # Centering the hamburger icon
                    html.Div(
                        "Select Chart",
                        id="hamburger",
                        n_clicks=0,
                    ),
                    
                    # Centered navigation menu (hidden initially)
                    html.Div(
                        id="nav-menu",
                        children=[
                            html.Button(
                                "Locals",
                                id={"type": "chart-btn", "value": "local"},
                                n_clicks=0,
                                className="custom-button",
                            ),
                            html.Button(
                                "Where?",
                                id={"type": "chart-btn", "value": "state_map"},
                                n_clicks=0,
                                className="custom-button",
                            ),
                            html.Button(
                                "Ages",
                                id={"type": "chart-btn", "value": "age"},
                                n_clicks=0,
                                className="custom-button",
                            ),
                            html.Button(
                                "Christ Followers",
                                id={"type": "chart-btn", "value": "christians"},
                                n_clicks=0,
                                className="custom-button",
                            ),
                            html.Button(
                                "Faith Decisions",
                                id={"type": "chart-btn", "value": "faithdecicion"},
                                n_clicks=0,
                                className="custom-button",
                            ),
                        ],
                    ),
                ],
                style={"position": "absolute"},
            ),
            html.Div(
                dcc.Loading(
                    id="loading-chart",
                    type="circle",
                    children=html.Div(id="chart-output",style={'marginTop':'40px'}),
                )
            ),
            html.Div(id="admin-panel-wrapper-container"),
        ]
    )


# Hamburger Menu Callback:
@app.callback(
    Output("nav-menu", "style", allow_duplicate = True),
    Input("hamburger", "n_clicks"),
    State("nav-menu", "style"),
    prevent_initial_call=True,
)
def toggle_nav(n_clicks, current_style):
    if n_clicks is None:
        return no_update

    # If there is no current style, set it to an initial state
    if current_style is None:
        return {"display": "flex"}

    # Toggle display based on the current style of the menu
    new_style = current_style.copy() if current_style else {}
    if new_style.get("display") == "none":
        new_style["display"] = "flex"  # Show the menu
    else:
        new_style["display"] = "none"  # Hide the menu
    return new_style

@app.callback(
    Output("nav-menu", "style", allow_duplicate = True),
    Output("chart-request", "data"),  # Update the chart request
    Input({"type": "chart-btn", "value": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def toggle_nav_and_select_chart(n_clicks_list):
    triggered = ctx.triggered_id

    if not triggered:
        raise PreventUpdate

    # Hide the nav menu after chart selection
    new_style = {"display": "none"}

    # Get the chart type from the button that was clicked
    chart_type = triggered["value"]

    return new_style, chart_type






delete_triggered = False  # Delete safeguard


@app.callback(
    Output("delete-status", "children"),
    Input("delete-button", "n_clicks"),
    prevent_initial_call=True,
)
def delete_sql_responses(n_clicks):
    if ctx.triggered_id == "delete-button" and n_clicks:
        try:
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM responses"))
            request._clear_cookie = True
            return "✅ All responses deleted from the database."
        except Exception as e:
            print("Delete failed:", e)
            return "❌ Failed to delete responses from the database."
    raise PreventUpdate


import time


@app.callback(
    Output("chart-output", "children"),
    Output("loading-flag", "data", allow_duplicate=True),
    Input("chart-request", "data"),
    prevent_initial_call=True,
)
def update_chart_view(chart_type):
    # Optional delay to simulate loading — can be removed
    time.sleep(0.5)

    return get_chart_layout(chart_type), False


# Check if Local
def checkLocal(state_):
    return state_ == "District of Columbia"


# This is our main callback for when the form is submitted


@app.callback(
    Output("chart-request", "data", allow_duplicate=True),
    Output("submission-store", "data", allow_duplicate=True),
    Output("form-error", "children"),
    Output("loading-flag", "data", allow_duplicate=True),
    Input("submit-button", "n_clicks"),
    State("inpu", "value"),
    State("age-slider", "value"),
    State("christian-status", "value"),
    State("faith-decicion", "value"),
    State("how-they-found-us", "value"),
    State("country-dropdown", "value"),
    State("state-dropdown", "value"),
    prevent_initial_call=True,
)
def form_submission(
    n_clicks, inpu, age_val, christian, faith, howtheyfoundus, country_, state_
):
    print(
        "Form callback triggered!",
        n_clicks,
        inpu,
        age_val,
        christian,
        faith,
        howtheyfoundus,
    )
    local_value = checkLocal(state_)

    if n_clicks > 0:
        request._set_cookie = True
        age_category = bin_age(age_val)
        required_fields = {
            "Name": inpu,
            "Age Range": age_val,
            "Christ Follower": christian,
            "Faith Decicion": faith,
        }

        missing = [
            field
            for field, value in required_fields.items()
            if not str(value).strip()
        ]
        if missing:
            return (
                no_update,
                no_update,
                f"⚠️ Please fill out: {', '.join(missing)}.",
                False,
            )

        new_row = pd.DataFrame(
            [
                [
                    inpu,
                    age_category,
                    age_val,
                    local_value,
                    country_,
                    state_,
                    christian,
                    faith,
                    howtheyfoundus,
                ]
            ],
            columns=columns,
        )

        global df
        try:
            with engine.connect() as conn:
                query = text("""
                INSERT INTO responses (
                    "Name", "Age Range", "Age", "Local", "Country", "State",
                    "Christ Follower", "Faith Decicion", "How you found us?"
                )
                VALUES (
                    :name, :age_range, :age, :local, :country, :state,
                    :christ_follower, :faith_decicion, :how_found
                )
            """)

                conn.execute(query, {
                    "name": inpu,
                    "age_range": age_category,
                    "age": age_val,
                    "local": local_value,
                    "country": country_,
                    "state": state_,
                    "christ_follower": christian,
                    "faith_decicion": faith,
                    "how_found": howtheyfoundus,
                })
        except Exception as e:
            print("Database insert error:", e)
            return no_update, False, "Error saving your submission.", False


        # Set loading to true after successful submission
        return "local", "true", "", True

    return no_update, False, "", False


# Simple function to take any given age and bin it so we can created age groups.


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
    Input({"type": "chart-btn", "value": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def nav_chart_select(n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered:
        raise PreventUpdate
    return triggered["value"], True


@app.callback(
    Output("chart-request", "data", allow_duplicate=True),
    Output("loading-flag", "data", allow_duplicate=True),
    Input("data_button", "n_clicks"),
    prevent_initial_call=True,
)
def handle_data_click(n_clicks):
    if n_clicks:
        return "data", True
    raise PreventUpdate


# Choose which chart we send to Output


def get_chart_layout(chart_type):
    if chart_type == "local":
        return local_counter()
    if chart_type == "state_map":
        return generate_us_map()
    elif chart_type == "age":
        return html.Div(
            [
                generate_pie_chart_from_column(
                    "Age Range", "Age Distribution"
                ),
                generate_bar_chart_from_column("Age", "Ages in attendance"),
            ]
        )
    elif chart_type == "christians":
        return generate_pie_chart_from_column(
            "Christ Follower", "Christ Follower Count"
        )
    elif chart_type == "faithdecicion":
        return generate_pie_chart_from_column(
            "Faith Decicion", "Faith Decision Count"
        )
    elif chart_type == "data":
        try:
            with engine.connect() as conn:
                df_sql = pd.read_sql("SELECT * FROM responses", conn)

            return dash_table.DataTable(
                data=df_sql.to_dict("records"),
                columns=[{"name": str(i), "id": str(i)} for i in df_sql.columns],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "5px"},
                style_header={"fontWeight": "bold"},
                page_size=20,
            )
        except Exception as e:
            print("View Data SQL query failed:", e)
            return html.Div("❌ Could not load data from the database.")
    else:
        return html.Div("Unknown chart type.")


def generate_us_map():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT state, COUNT(*) 
                FROM responses 
                WHERE state IS NOT NULL AND state != ''
                GROUP BY state
            """)).fetchall()

        if not result:
            return html.Div("No state data available.", style={"color": "gray", "textAlign": "center"})

        state_abbrev = {
            "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
            "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
            "District Of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
            "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
            "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
            "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
            "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
            "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
            "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
            "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
            "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
            "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
            "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
        }

        state_names, counts = zip(*result)
        df_chart = pd.DataFrame({
            "State": [s.strip().title() for s in state_names],
            "Count": counts
        })
        df_chart["Code"] = df_chart["State"].map(state_abbrev)

        fig = px.choropleth(
            df_chart,
            locations="Code",
            locationmode="USA-states",
            color="Count",
            scope="usa",
            color_continuous_scale="Blues",
        )

        fig.update_layout(
            title_text="Respondents by State",
            geo=dict(scope="usa", bgcolor="#FEFAE0", lakecolor="#FEFAE0", showland=True, landcolor="#FAF3D3", showlakes=True),
            paper_bgcolor="#FEFAE0",
            plot_bgcolor="#FEFAE0",
        )

        return html.Div(dcc.Graph(figure=fig), className="graph-object")

    except Exception as e:
        print("Map chart query failed:", e)
        return html.Div("Failed to load state map.")


def local_counter_sql():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT local, COUNT(*) 
                FROM responses 
                GROUP BY local
            """)).fetchall()

        if not result:
            return html.Div("No data available.")

        label_map = {True: "Local", False: "Visitor"}
        labels, counts = zip(*result)
        labels_mapped = [label_map.get(l, "Unknown") for l in labels]

        df_chart = pd.DataFrame({"Visitor": labels_mapped, "Count": counts})

        fig = px.pie(
            df_chart,
            names="Visitor",
            values="Count",
            color="Visitor",
            color_discrete_map={"Local": "blue", "Visitor": "purple"},
            hole=0.1,
        )

        return html.Div(dcc.Graph(figure=style_pie_chart(fig, "Local vs Visitor")), className="graph-object")

    except Exception as e:
        print("Local chart query failed:", e)
        return html.Div("Failed to load chart.")


def generate_pie_chart_from_column(column_name, title):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT "{column_name}", COUNT(*) 
                FROM responses 
                GROUP BY "{column_name}"
            """)).fetchall()

        if not result:
            return html.Div("No data available.")

        labels, counts = zip(*result)
        df_chart = pd.DataFrame({"Label": labels, "Count": counts})

        fig = px.pie(
            df_chart,
            names="Label",
            values="Count",
            hole=0.1,
        )

        return html.Div(dcc.Graph(figure=style_pie_chart(fig, title)), className="graph-object")

    except Exception as e:
        print("Chart query failed:", e)
        return html.Div("Failed to load chart.")


def generate_bar_chart_from_column(column_name, title):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT "{column_name}", COUNT(*) 
                FROM responses 
                GROUP BY "{column_name}"
                ORDER BY "{column_name}"
            """)).fetchall()

        if not result:
            return html.Div("No data available.")

        labels, counts = zip(*result)
        df_chart = pd.DataFrame({"Label": labels, "Count": counts})

        fig = px.bar(
            df_chart,
            x="Label",
            y="Count",
            color="Label",
            title=title,
        )

        fig.update_layout(
            xaxis_title=None,
            yaxis_title="Count",
            title_x=0.5,
            margin=dict(t=50, b=80, l=30, r=30),
            height=400,
            showlegend=False,
            paper_bgcolor="#FEFAE0",
            plot_bgcolor="#FEFAE0",
        )

        return html.Div(dcc.Graph(figure=fig), className="graph-output")
    
    except Exception as e:
        print("Bar chart query failed:", e)
        return html.Div("Failed to load chart.")


from dash import MATCH


@app.callback(
    Output("admin-code", "style"),
    Input("admin-toggle", "n_clicks"),
    prevent_initial_call=True,
)
def show_code_input(n):
    return {"display": "inline-block", "marginTop": "10px"}


ADMIN_CODE = "letmein123"  # You can make this env-based for real security


@app.callback(
    Output("admin-panel", "children"),
    Input("admin-code", "value"),
    prevent_initial_call=True,
)
def grant_admin_access(code):
    if code == ADMIN_CODE:
        return html.Div(
            [
                html.Hr(),
                html.H4("Admin Tools"),
                html.Button(
                    "Download CSV",
                    id="download-btn",
                    type="button",
                    className="custom-button-dev",
                    classNameProp=True,
                ),
                html.Button(
                    "View Data",
                    id="data_button",
                    className="custom-button-dev",
                    classNameProp=True,
                    type="button",
                ),
                html.Button(
                    "Clear Cookies (Dev)",
                    id="dev-clear-cookies",
                    n_clicks=0,
                    className="custom-button-dev",
                ),
                dcc.Download(id="download"),
                html.Div(
                    [
                        html.Button(
                            "Delete responses.csv",
                            id="delete-button",
                            n_clicks=0,
                            style={"color": "red"},
                            className="custom-button-dev",
                            classNameProp=True,
                        ),
                        html.Div(
                            id="delete-status",
                            style={
                                "marginTop": "0.5rem",
                                "fontStyle": "italic",
                            },
                        ),
                    ],
                    style={"marginBottom": "2rem"},
                ),
            ],
            id="admin-stuff",
            style={"backgroundColor": "#888"},
        )
    raise PreventUpdate


@app.callback(
    Output("dev-cookie-status-wrapper", "children"),
    Input("dev-clear-cookies", "n_clicks"),
    prevent_initial_call=True,
)
def dev_clear_cookie(n_clicks):
    # This line ensures only real user clicks count
    if ctx.triggered_id != "dev-clear-cookies" or not n_clicks:
        raise PreventUpdate

    print(">> Clearing cookie (from button)")
    request._clear_cookie = True
    return html.Div(
        [
            html.Div("✅ Cookie cleared!", id="dev-cookie-status"),
            html.Script("setTimeout(() => window.location.reload(), 500);"),
        ]
    )


@app.callback(
    Output("download", "data"),
    Input("download-btn", "n_clicks"),
    prevent_initial_call=True,
)
def download_data(n_clicks):
    try:
        with engine.connect() as conn:
            df_sql = pd.read_sql("SELECT * FROM responses", conn)
        return dcc.send_data_frame(df_sql.to_csv, "responses.csv", index=False)
    except Exception as e:
        print("CSV download failed:", e)
        raise PreventUpdate


@app.server.after_request
def apply_cookie_flags(response):
    if getattr(request, "_set_cookie", False):
        print(">> Setting cookie")
        response.set_cookie(
            "submitted",
            "true",
            max_age=60 * 60 * 24,
            path="/",
            samesite="Lax",
            secure=False,  # Adjust secure=True if using HTTPS
        )
    if getattr(request, "_clear_cookie", False):
        print(">> Clearing cookie")
        response.set_cookie("submitted", "", max_age=0, path="/")
    return response


def style_pie_chart(fig, title):
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="%{label}: %{value}<extra></extra>",
    )
    fig.update_layout(
        title_text=title,
        title_x=0.5,
        legend_title_text="",
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5
        ),
        margin=dict(t=50, b=80, l=30, r=30),
        height=400,
        paper_bgcolor="#FEFAE0",   # Match your site's background
        plot_bgcolor="#FEFAE0",    # Match the plotting area too
    )
    return fig


@server.route("/login")
def login():
    redirect_uri = url_for("callback", _external=True, _scheme="https")
    next_url = request.args.get(
        "next", "/?admin=true"
    )  # default to /?admin=true
    session["next_url"] = next_url
    return auth0.authorize_redirect(redirect_uri=redirect_uri)


@server.route("/callback")
def callback():
    try:
        auth0.authorize_access_token()
        resp = auth0.get("userinfo")
        userinfo = resp.json()
        print("Auth0 Userinfo:", userinfo)  # <- Inspect this

        session["profile"] = {
            "user_id": userinfo.get("sub"),
            "name": userinfo.get("name") or userinfo.get("nickname"),
            "email": userinfo.get(
                "email", "no-email@unknown.fake"
            ),  # fallback
        }

        next_url = session.pop("next_url", "/")
        return redirect(next_url)
    except Exception as e:
        import traceback

        print("Callback error:", str(e))
        traceback.print_exc()
        return f"Callback failed: {e}", 500


@server.route("/logout")
def logout():
    session.clear()
    resp = redirect(
        f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?"
        + f"returnTo={url_for('index', _external=True, _scheme='https')}&client_id={os.getenv('AUTH0_CLIENT_ID')}"
    )
    resp.set_cookie("submitted", "", expires=0, path="/")
    return resp


@server.route("/")
def index():
    return "App is running"


@server.before_request
def ensure_logged_out():
    if (
        request.path == "/"
        and "admin=true" in request.query_string.decode()
        and "profile" not in session
    ):
        return redirect("/login?next=/?admin=true")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, use_reloader=True)

