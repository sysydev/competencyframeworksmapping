from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Confirm the API Key is loaded
api_key = os.getenv('SENDGRID_API_KEY')
if not api_key:
    print("SendGrid API Key not found. Please check your .env file.")
else:
    print("SendGrid API Key successfully loaded.")

# Other imports
import pandas as pd
import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load the data
framework_data = pd.read_csv('all_competency_framework.csv')
definitions_data = pd.read_csv('competency_definitions.csv')
rating_scales_data = pd.read_csv('all_rating_scales.csv')
competency_data = pd.read_csv('spider_chart_data.csv')
position_sub_items_data = pd.read_csv('position_sub_items.csv')
organization_chart_data = pd.read_csv('organization_chart_data.csv')

# Ensure all column names are lowercase for consistency
framework_data.columns = framework_data.columns.str.lower()
definitions_data.columns = definitions_data.columns.str.lower()
rating_scales_data.columns = rating_scales_data.columns.str.lower()
competency_data.columns = competency_data.columns.str.lower()
position_sub_items_data.columns = position_sub_items_data.columns.str.lower()
organization_chart_data.columns = organization_chart_data.columns.str.lower()

# Strip trailing spaces in key columns
framework_data = framework_data.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
definitions_data = definitions_data.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
rating_scales_data = rating_scales_data.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
competency_data = competency_data.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
position_sub_items_data = position_sub_items_data.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
organization_chart_data = organization_chart_data.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Huneety Assessment Framework"

# Get dropdown options
framework_options = framework_data['framework'].unique()
rating_scale_options = rating_scales_data['rating scales'].unique()
position_options = competency_data['position'].unique()

# Helper function to send email
def send_email(first_name, last_name, position, organization, assessment_type):
    try:
        email_subject = f"New 360 Assessment Request: {assessment_type}"
        email_content = (
            f"New 360 Assessment Request\n\n"
            f"Name: {first_name} {last_name}\n"
            f"Position: {position}\n"
            f"Organization: {organization}\n"
            f"Assessment Type: {assessment_type}"
        )
        message = Mail(
            from_email="no-reply@huneety.com",
            to_emails="contact@huneety.com",
            subject=email_subject,
            plain_text_content=email_content
        )
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
    except Exception as e:
        print(f"An error occurred: {e}")

# Function to create the organization chart
def create_organization_chart(data):
    data['manager'] = data['manager'].fillna('')  # Replace NaN with empty strings for managers
    data['label'] = data['name'] + " (" + data['title'] + ")"  # Combine name and title

    labels = data['label'].tolist()
    parents = data['manager'].apply(lambda x: data.loc[data['name'] == x, 'label'].values[0] if x in data['name'].values else '').tolist()

    colors = ['green' if 'Manager' in title else 'blue' for title in data['title']]

    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        marker=dict(colors=colors),
        branchvalues="total"
    ))

    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        title="Organization Chart"
    )
    return fig

# Function to create the taxonomy tree
def create_taxonomy_tree(df):
    tree = []
    for competency, group_data in df.groupby('competency'):
        definition = definitions_data.loc[
            definitions_data['competency'] == competency, 'definition'
        ].values[0] if competency in definitions_data['competency'].values else "No definition available."
        tree.append(html.Div(competency, style={
            "color": "blue", "fontWeight": "bold", "fontSize": "18px", "marginTop": "15px"
        }))
        tree.append(html.Div(f"Definition: {definition}", style={
            "fontStyle": "italic", "fontSize": "14px", "color": "#555", "marginBottom": "10px", "marginLeft": "20px"
        }))
        for _, row in group_data.iterrows():
            tree.append(html.Div(
                f"◉ {row['type'].capitalize()}: {row['sub-item']}",
                style={
                    "marginLeft": "40px",
                    "color": "red" if row['type'].lower() == "technical ability" else "green",
                    "fontSize": "14px",
                    "marginBottom": "5px"
                }
            ))
    return tree

# Function to create the rating scale table
def create_rating_scale_table(selected_scale):
    filtered_data = rating_scales_data[rating_scales_data['rating scales'] == selected_scale]
    rows = []
    for _, row in filtered_data.iterrows():
        rows.append(html.Tr([
            html.Td(row['level']),
            html.Td(row['rating score'])
        ]))
    return html.Table(
        [
            html.Thead(html.Tr([html.Th("Level"), html.Th("Description")])),
            html.Tbody(rows)
        ],
        style={"width": "80%", "margin": "0 auto", "marginBottom": "20px"}
    )

# Function to create the spider chart
def create_spider_chart(data, position):
    filtered_data = data[data['position'] == position]
    categories = filtered_data['competency'].tolist()
    values = filtered_data['proficiency level'].tolist()
    if categories and values:
        values += values[:1]  # Close the spider chart
        categories += categories[:1]

        fig = go.Figure(
            data=go.Scatterpolar(r=values, theta=categories, fill='toself', name="Proficiency Level")
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False,
            title=f"{position} Competency Requirements"
        )
        return fig
    else:
        return go.Figure()

# Function to create the competency and sub-items list
def create_competency_list(data, position):
    filtered_data = data[data['position'] == position]
    items = []
    for competency, group_data in filtered_data.groupby('competency'):
        items.append(html.Div(competency, style={
            "color": "blue", "fontWeight": "bold", "fontSize": "18px", "marginTop": "15px"
        }))
        for _, row in group_data.iterrows():
            items.append(html.Div(
                f"◉ {row['sub-item']} (Proficiency Level: {row['proficiency level']})",
                style={
                    "marginLeft": "20px",
                    "color": "red" if row['type'].lower() == "technical ability" else "green",
                    "fontSize": "14px",
                    "marginBottom": "5px"
                }
            ))
    return items

# App layout
app.layout = html.Div([
    # Logo
    html.Div([
        html.Img(src="/assets/huneetylearning_logo.png", style={
            "display": "block",
            "margin": "0 auto",
            "width": "150px",
            "height": "auto"
        })
    ], style={"padding": "20px 0"}),

    # Step 1: Setting Your Competency Framework
    html.Div([
        html.H1("Step 1: Setting Your Competency Framework", style={"textAlign": "center", "padding": "20px"}),
        html.P(
            "Huneety creates your competency framework based on your job descriptions or helps you design a unique framework "
            "tailored to your industry, leveraging labor market data.",
            style={"textAlign": "center", "marginBottom": "20px", "fontSize": "16px"}
        ),
        dcc.Dropdown(
            id="framework-dropdown",
            options=[{"label": fw, "value": fw} for fw in framework_options],
            value=framework_options[0],
            clearable=False,
            style={"width": "50%", "margin": "0 auto"}
        ),
        html.Div(id="taxonomy-tree", style={"marginTop": "20px"})
    ], style={"marginBottom": "40px", "padding": "20px", "border": "1px solid #ccc", "borderRadius": "10px"}),

    # Step 2: Choose a Rating Scale
    html.Div([
        html.H1("Step 2: Choose a Rating Scale", style={"textAlign": "center", "padding": "20px"}),
        html.P(
            "Huneety offers the flexibility to customize rating scales to align with your assessment objectives. "
            "We recommend using a 1-to-5 rating scale, with each rating and definition fully customizable upon request.",
            style={"textAlign": "center", "marginBottom": "20px", "fontSize": "16px"}
        ),
        dcc.Dropdown(
            id="rating-scale-dropdown",
            options=[{"label": rs, "value": rs} for rs in rating_scale_options],
            value=rating_scale_options[0],
            clearable=False,
            style={"width": "50%", "margin": "0 auto"}
        ),
        html.Div(id="rating-scale-table")
    ], style={"marginBottom": "40px", "padding": "20px", "border": "1px solid #ccc", "borderRadius": "10px"}),

    # Step 3: Competency Deployment - Competency Mapping
    html.Div([
        html.H1("Step 3: Competency Deployment - Competency Mapping", style={"textAlign": "center", "padding": "20px"}),
        html.P(
            "Competencies are assigned to targeted jobs and aligned with assessment priorities. "
            "Huneety establishes a baseline for each competency to effectively measure skill gaps. "
            "Competencies can be deployed as groups (e.g., leadership competencies, core values) or for specific positions "
            "(e.g., Finance Manager).",
            style={"textAlign": "center", "marginBottom": "20px", "fontSize": "16px"}
        ),
        dcc.Dropdown(
            id="position-dropdown",
            options=[{"label": pos, "value": pos} for pos in position_options],
            value=position_options[0],
            clearable=False,
            style={"width": "50%", "margin": "0 auto"}
        ),
        html.Div(id="spider-chart-section", style={"marginTop": "20px"}),
        html.Div(id="competency-list-section", style={"marginTop": "40px"})
    ], style={"marginBottom": "40px", "padding": "20px", "border": "1px solid #ccc", "borderRadius": "10px"}),

    # Step 4: Gathering People Priorities for the Assessment
    html.Div([
        html.H1("Step 4: Gathering Your People Priorities for the Assessment", style={"textAlign": "center", "padding": "20px"}),
        html.P(
            "Huneety collects your key people priorities before launching your assessment projects. Projects can be tailored "
            "to align with your retention strategies, such as:\n"
            "• High potentials: Visualizing gaps between current positions and career paths.\n"
            "• Managers and leaders: Assessing leadership capabilities.\n"
            "• Specific employee groups to evaluate culture fit.\n"
            "• Entire departments or organizations.",
            style={"textAlign": "center", "marginBottom": "20px", "fontSize": "16px"}
        ),
        html.Div(dcc.Graph(figure=create_organization_chart(organization_chart_data)), style={"marginBottom": "40px"})
    ], style={"marginBottom": "40px", "padding": "20px", "border": "1px solid #ccc", "borderRadius": "10px"}),

    # Step 5: Debriefing 360 Assessment Reports
    html.Div([
        html.H1("Step 5: Debriefing 360 Assessment Reports", style={"textAlign": "center", "padding": "20px"}),
        html.P(
            "Select the type of 360 assessment report and request a template using the form below.",
            style={"textAlign": "center", "marginBottom": "20px", "fontSize": "16px"}
        ),
        dcc.Dropdown(
            id="assessment-dropdown",
            options=[
                {"label": "360 Assessment Report for Leadership", "value": "leadership"},
                {"label": "360 Assessment Report for Core Values", "value": "core_values"},
                {"label": "360 Assessment for Full Position Assessment", "value": "full_position"},
                {"label": "360 Assessment for Succession Planning", "value": "succession"}
            ],
            value=None,
            placeholder="Select Assessment Type",
            style={"width": "50%", "margin": "0 auto"}
        ),
        html.Div(id="assessment-result", style={"textAlign": "center", "marginTop": "20px"}),
        html.Div([
            html.Label("First Name"),
            dcc.Input(id="first-name", type="text", placeholder="First Name", style={"marginBottom": "10px", "width": "100%"}),
            html.Label("Last Name"),
            dcc.Input(id="last-name", type="text", placeholder="Last Name", style={"marginBottom": "10px", "width": "100%"}),
            html.Label("Email Address"),  # New email field
            dcc.Input(id="email-address", type="email", placeholder="Email Address", style={"marginBottom": "10px", "width": "100%"}),  # Add type email for validation
            html.Label("Position"),
            dcc.Input(id="position", type="text", placeholder="Position", style={"marginBottom": "10px", "width": "100%"}),
            html.Label("Organization"),
            dcc.Input(id="organization", type="text", placeholder="Organization", style={"marginBottom": "10px", "width": "100%"}),
            dbc.Button("Submit", id="submit-button", color="primary", style={"marginTop": "10px", "width": "100%"})
        ], style={"width": "50%", "margin": "0 auto", "display": "block"}, id="assessment-form")
    ], style={"marginBottom": "40px", "padding": "20px", "border": "1px solid #ccc", "borderRadius": "10px"}),

    # Step 6: Producing a Skills Analytics Dashboard
    html.Div([
        html.H1("Step 6: Producing a Skills Analytics Dashboard", style={"textAlign": "center", "padding": "20px"}),
        html.Iframe(
            src="https://lookerstudio.google.com/embed/reporting/3d47bde0-d3d8-412f-819e-9145c2174db8/page/p_davu4ue6tc",
            style={"width": "100%", "height": "600px", "border": "none"}
        )
    ], style={"marginBottom": "40px", "padding": "20px", "border": "1px solid #ccc", "borderRadius": "10px"}),

    # Step 7: Individual Development Plans
    html.Div([
        html.H1("Step 7: Individual Development Plans (IDPs) to Bridge the Gaps", style={"textAlign": "center", "padding": "20px"}),
        html.P(
            "Individual Development Plans (IDPs) are designed based on the 70/20/10 principle. These plans can be tailored for "
            "individuals or groups to address shared gaps. We prioritize leveraging your company's internal experts to enhance "
            "engagement, collaboration, and productivity.",
            style={"textAlign": "center", "marginBottom": "20px", "fontSize": "16px"}
        ),
        html.Div([
            html.A(
                dbc.Button("Schedule a Meeting to Discuss Your Project", color="primary"),
                href="https://calendly.com/simon-huneety",
                style={"textAlign": "center", "width": "100%"}
            )
        ])
    ], style={"marginBottom": "40px", "padding": "20px", "border": "1px solid #ccc", "borderRadius": "10px"})
])

# Callbacks
@app.callback(
    Output("taxonomy-tree", "children"),
    [Input("framework-dropdown", "value")]
)
def update_framework(selected_framework):
    filtered_data = framework_data[framework_data['framework'] == selected_framework]
    return create_taxonomy_tree(filtered_data)


@app.callback(
    Output("rating-scale-table", "children"),
    [Input("rating-scale-dropdown", "value")]
)
def update_rating_scale(selected_scale):
    return create_rating_scale_table(selected_scale)


@app.callback(
    [Output("spider-chart-section", "children"),
     Output("competency-list-section", "children")],
    [Input("position-dropdown", "value")]
)
def update_visualizations(selected_position):
    # Generate spider chart
    spider_chart = dcc.Graph(figure=create_spider_chart(competency_data, selected_position))

    # Generate competency list
    competency_list = create_competency_list(position_sub_items_data, selected_position)

    return spider_chart, competency_list

@app.callback(
    Output("assessment-result", "children"),
    [Input("assessment-dropdown", "value")]
)
def update_assessment_result(selected_assessment):
    if selected_assessment:
        return f"You have selected {selected_assessment}. Fill the form below to request the template."
    return ""


@app.callback(
    Output("assessment-form", "style"),
    [Input("assessment-dropdown", "value")]
)
def toggle_form(selected_assessment):
    if selected_assessment:
        return {"width": "50%", "margin": "0 auto", "display": "block"}
    return {"width": "50%", "margin": "0 auto", "display": "none"}

@app.callback(
    Output("submit-button", "children"),
    [Input("submit-button", "n_clicks")],
    [State("first-name", "value"),
     State("last-name", "value"),
     State("email-address", "value"),  # Include email field for internal record
     State("position", "value"),
     State("organization", "value"),
     State("assessment-dropdown", "value")]
)
def submit_form(n_clicks, first_name, last_name, email_address, position, organization, assessment_type):
    if n_clicks:
        try:
            # Send email notification using SendGrid
            message = Mail(
                from_email="contact@huneety.com",  # Sender email
                to_emails="contact@huneety.com",  # Internal recipient email
                subject=f"New Assessment Request - {assessment_type}",
                html_content=f"""
                    <p><strong>Assessment Type:</strong> {assessment_type}</p>
                    <p><strong>First Name:</strong> {first_name}</p>
                    <p><strong>Last Name:</strong> {last_name}</p>
                    <p><strong>Email Address:</strong> {email_address}</p>
                    <p><strong>Position:</strong> {position}</p>
                    <p><strong>Organization:</strong> {organization}</p>
                """
            )
            sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))  # Ensure the key is correctly set in your .env file
            sg.send(message)

            return "Thank you! Your request has been submitted successfully. You will receive an email shortly."
        except Exception as e:
            print(f"An error occurred while sending the email: {e}")
            return "An error occurred while processing your request. Please try again later."
    return "Submit"

# Run the app
if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0", port=8050)