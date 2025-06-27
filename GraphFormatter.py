import dash
from dash import dcc, html, Input, Output, State, dash_table, ctx
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import dash_daq as daq
import yaml


class GraphFormatter:
    """
    A Dash app for interactively customizing Plotly graphs.

    Users can tweak layout, colors, annotations, and traces via a visual UI.
    Configuration is read from an external YAML file.
    """
    def __init__(self, config_path):
        """
        Initializes the app: loads config, creates dummy data,
        builds layout, and registers all callbacks.
        """
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.app.title = "Interactive Plot Editor"
        self.df_data = self.generate_dummy_data()
        self.config = self.load_config(config_path)
        self.input_ids = self.build_input_ids()

        self.app.layout = self.build_layout()
        self.register_callbacks()
        self.register_toggle_callbacks()
        self.register_color_picker_callbacks()

    def generate_dummy_data(self):
        """
        Generates a dummy pandas DataFrame with random integer data.
        This method creates a DataFrame with 10 columns labeled 'Series A' to 'Series J',
        each containing 100 random integers between 0 and 99. The random seed is set to 0
        for reproducibility.
        Returns:
            pandas.DataFrame: A DataFrame with shape (100, 10) containing random integer data.
        """
    
        np.random.seed(0)
        return pd.DataFrame({
            f"Series {chr(65+i)}": np.random.randint(0, 100, 100)
            for i in range(10)
        })

    def load_config(self, path):
        """
        Loads a YAML configuration file from the specified path.

        Args:
            path (str): The file path to the YAML configuration file.

        Returns:
            dict: The contents of the YAML file as a dictionary.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            yaml.YAMLError: If the file cannot be parsed as valid YAML.
        """
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def build_input_ids(self):
        """
        Builds a list of Input objects representing the input IDs required for the application.

        Iterates over the configuration dictionary (`self.config`), creating an Input object for each setting in each section,
        using the format "{section}-{setting}" as the input ID and "value" as the property.
        Additionally, appends Input objects for "data-table" (with property "selected_columns") and
        "trace-colors" (with property "data").

        Returns:
            list: A list of Input objects corresponding to the application's input components.
        """
        ids = []
        for section, settings in self.config.items():
            for setting, value in settings.items():  # <-- FIXED
                if isinstance(value, list) and len(value) == 2:
                    ids.append(Input(f"{section}-{setting}_0", "value"))
                    ids.append(Input(f"{section}-{setting}_1", "value"))
                else:
                    ids.append(Input(f"{section}-{setting}", "value"))

        ids.append(Input("data-table", "selected_columns"))
        ids.append(Input("trace-colors", "data"))
        return ids

    def build_layout(self):
        """
        Constructs and returns the main layout of the Dash application.

        The layout includes:
            - A header for the plot customizer.
            - A set of collapsible sections for configuration, dynamically generated from self.config.
            - A central area with:
                - A Plotly graph for data visualization.
                - Color picker controls for customizing trace colors, with state management using dcc.Store.
                - A data table displaying the contents of self.df_data, with selectable columns and custom styling.

        Returns:
            dash.html.Div: The root Div containing all layout components.
        """
        return html.Div([
            html.H3("Plot Customizer"),

            html.Div([
                *[self.create_collapsible_section(section, settings) for section, settings in self.config.items()]
            ], style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "padding": "10px 20px"}),

            html.Div([
                html.Div([
                    dcc.Graph(id="figure")
                ], style={"width": "50%", "display": "inline-block", "verticalAlign": "top"}),

                html.Div([
                    dcc.Store(id="selected-trace", data=None),
                    dcc.Store(id="trace-colors", data={}),
                    html.Div([
                        html.Label("Line Color"),
                        daq.ColorPicker(id="trace-color-picker", value={"hex": "#636EFA"}),

                        html.Label("Line Width"),
                        dcc.Input(id="trace-line-width", type="number", min=0.5, step=0.5, value=2),

                        html.Label("Dash Style"),
                        dcc.Dropdown(
                            id="trace-line-style",
                            options=[
                                {"label": "Solid", "value": "solid"},
                                {"label": "Dash", "value": "dash"},
                                {"label": "Dot", "value": "dot"},
                                {"label": "DashDot", "value": "dashdot"},
                            ],
                            value="solid"
                        ),

                        html.Label("Opacity"),
                        dcc.Slider(id="trace-opacity", min=0, max=1, step=0.05, value=1),

                        html.Button("✖ Close", id="trace-color-close")
                    ], id="trace-color-picker-container", style={"display": "none", "marginTop": "10px", "width": "250px"})

                ]),


                html.Div([
                    dash_table.DataTable(
                        id="data-table",
                        columns=[{"name": col, "id": col, "selectable": True} for col in self.df_data.columns],
                        data=self.df_data.to_dict("records"),
                        column_selectable="multi",
                        selected_columns=[],
                        style_table={"maxHeight": "400px", "overflowY": "auto", "overflowX": "auto"},
                        style_cell={"textAlign": "left", "padding": "5px"},
                        style_header={"backgroundColor": "lightgrey", "fontWeight": "bold"},
                    )
                ], style={"width": "28%", "display": "inline-block", "verticalAlign": "top", "padding": "10px", "textAlign": "center"})
            ], style={"display": "flex", "justifyContent": "center", "alignItems": "center", "width": "100%"})
        ])

    def create_collapsible_section(self, section_name, settings):
        """
        Creates a collapsible UI section for a given group of settings.

        Parameters:
            section_name (str): The name of the section, used for labeling and generating unique IDs.
            settings (dict): A dictionary where keys are setting names and values are their default values.
                Supported value types:
                    - bool: Rendered as a checklist (checkbox).
                    - int or float: Rendered as a numeric input (step is 0.01 for "x", "y", "x0", "x1", else 1).
                    - str containing "color": Rendered as a color picker with toggle and close buttons.
                    - str: Rendered as a text input.
                    - Other types: Rendered as an unsupported type message.

        Returns:
            dash.html.Div: A Dash HTML Div containing a button to toggle the section and the corresponding input components,
            all styled and grouped within a bordered container.
        """
        toggle_id = f"{section_name}-toggle"
        container_id = f"{section_name}-container"
        inputs = []

        for setting, value in settings.items():
            input_id = f"{section_name}-{setting}"
            step = 0.01 if setting in ["x", "y", "x0", "x1"] else 1

            if isinstance(value, bool):
                input_component = dcc.Checklist(
                    options=[{"label": "", "value": "on"}],
                    value=["on"] if value else [],
                    id=input_id
                )
            elif isinstance(value, (int, float)):
                input_component = dcc.Input(type="number", value=value, id=input_id, step=step, style={"width": "100px"})
            elif isinstance(value, str) and "color" in setting:
                picker_id = input_id
                toggle_btn_id = f"{input_id}-toggle"
                close_btn_id = f"{input_id}-close"
                input_component = html.Div([
                    html.Button("Pick Color", id=toggle_btn_id),
                    html.Div([
                        daq.ColorPicker(id=picker_id, value={"hex": value}, size=164),
                        html.Button("✖ Close", id=close_btn_id)
                    ], id=f"{picker_id}-container", style={"display": "none"})
                ])
            elif isinstance(value, str):
                input_component = dcc.Input(type="text", value=value, id=input_id, style={"width": "150px"})
            elif isinstance(value, list) and len(value) == 2: # for ranges like xlimit
                input_component = html.Div([
                    dcc.Input(type="number", value=value[0], id=f"{input_id}_0", style={"width": "80px", "marginRight": "5px"}),
                    dcc.Input(type="number", value=value[1], id=f"{input_id}_1", style={"width": "80px"})
                ])

            else:
                input_component = html.Div(f"Unsupported type for {setting}")

            inputs.append(html.Div([
                html.Label(setting),
                input_component
            ], style={"marginBottom": "10px", "marginRight": "20px"}))

        return html.Div([
            html.Button(f"{section_name.upper()} ▶", id=toggle_id, n_clicks=0, style={"width": "100%"}),
            html.Div(id=container_id, children=inputs, style={"display": "none"})
        ], style={"width": "220px", "border": "1px solid #ccc", "padding": "10px", "borderRadius": "6px"})

    def register_callbacks(self):
        """
        Registers Dash callback functions for interactive graph formatting.

        This method sets up the following callbacks:
        
        1. Updates the Plotly figure based on user input controls, selected columns, and trace colors.
            - Dynamically constructs the figure using updated configuration values.
            - Applies user-selected colors and settings to traces and layout.
            - Updates annotations for title, description, and footnote.

        2. Toggles the visibility of the trace color picker UI.
            - Shows the color picker when a trace is clicked in the figure.
            - Hides the color picker when the close button is pressed.
            - Stores the selected trace name for color assignment.

        3. Updates the color mapping for traces.
            - Assigns the picked color to the selected trace in the color map.

        Returns:
            None
        """
        @self.app.callback(
            Output("figure", "figure"),
            self.input_ids
        )
        def update_figure(*args):
            *values, selected_columns, trace_colors = args

            updated_config = {}
            i = 0
            for section, settings in self.config.items():
                updated_config[section] = {}
                for setting, default_val in settings.items():
                    input_val = values[i]
                    if isinstance(default_val, bool):
                        updated_config[section][setting] = "on" in (input_val or [])
                        i += 1
                    elif isinstance(default_val, str) and "color" in setting:
                        updated_config[section][setting] = input_val["hex"] if isinstance(input_val, dict) else input_val
                        i += 1
                    elif isinstance(default_val, list) and len(default_val) == 2:
                        updated_config[section][setting] = [values[i], values[i+1]]
                        i += 2
                    else:
                        updated_config[section][setting] = input_val
                        i += 1

            fig = go.Figure()

            # Plot selected columns
            for col in selected_columns:

                style = trace_colors.get(col, {})
                fig.add_trace(go.Scatter(
                    x=self.df_data.index,
                    y=self.df_data[col],
                    mode="lines+markers",
                    name=col,
                    line=dict(
                        color=style.get("color"),
                        width=style.get("width", 2),
                        dash=style.get("dash", "solid")
                    ),
                    opacity=style.get("opacity", 1.0)
                ))


            # Apply layout settings
            fig.update_layout(
                xaxis=updated_config.get("xaxis", {}),
                yaxis=updated_config.get("yaxis", {}),
                width=updated_config["properties"]["width"],
                height=updated_config["properties"]["height"],
                paper_bgcolor=updated_config["properties"]["paper_bgcolor"],
                plot_bgcolor=updated_config["properties"]["plot_bgcolor"],
                # margin=dict(t=130, b=100),
                margin=updated_config.get("margin", dict(t=130, b=100)),
                template="plotly_white",
                annotations=[
                    dict(
                        text=f"<b>{updated_config['title']['text']}</b><br><sup>{updated_config['title']['subtitle']}</sup>",
                        x=updated_config['title']['x'],
                        y=updated_config['title']['y'],
                        xref="paper",
                        yref="paper",
                        xanchor=updated_config['title']['xanchor'],
                        yanchor=updated_config['title']['yanchor'],
                        showarrow=False,
                        font=dict(size=updated_config['title']['fontsize'])
                    ),
                    dict(
                        text=updated_config['description']['text'],
                        x=updated_config['description']['x'],
                        y=updated_config['description']['y'],
                        xref="paper",
                        yref="paper",
                        xanchor=updated_config['description']['xanchor'],
                        yanchor=updated_config['description']['yanchor'],
                        showarrow=False,
                        font=dict(size=updated_config['description']['fontsize'], color=updated_config['description']['color'])
                    ),
                    dict(
                        text=f"<i>{updated_config['footnote']['text']}</i>",
                        x=updated_config['footnote']['x'],
                        y=updated_config['footnote']['y'],
                        xref="paper",
                        yref="paper",
                        xanchor=updated_config['footnote']['xanchor'],
                        yanchor=updated_config['footnote']['yanchor'],
                        showarrow=False,
                        font=dict(size=updated_config['footnote']['fontsize'], color=updated_config['footnote']['color'])
                    )
                ],
                legend=updated_config.get("legend", {})
            )

            return fig

        @self.app.callback(
            Output("trace-color-picker-container", "style"),
            Output("selected-trace", "data"),
            Input("figure", "clickData"),
            Input("trace-color-close", "n_clicks"),
            State("trace-color-picker-container", "style"),
            State("figure", "figure"),
            prevent_initial_call=True
        )
        def toggle_trace_picker(clickData, close_clicks, current_style, figure_data):
            if not ctx.triggered:
                return current_style, dash.no_update
            trigger = ctx.triggered_id
            if trigger == "trace-color-close":
                return {"display": "none"}, None
            if clickData and "curveNumber" in clickData["points"][0]:
                curve_idx = clickData["points"][0]["curveNumber"]
                trace_name = figure_data["data"][curve_idx]["name"]
                return {"display": "block"}, trace_name
            return dash.no_update, dash.no_update

        # @self.app.callback(
        #     Output("trace-colors", "data"),
        #     Input("trace-color-picker", "value"),
        #     State("selected-trace", "data"),
        #     State("trace-colors", "data"),
        #     prevent_initial_call=True
        # )
        # def update_trace_color(picked, trace_name, color_map):
        #     if trace_name is None:
        #         return color_map
        #     color_map[trace_name] = picked["hex"]
        #     return color_map
        @self.app.callback(
            Output("trace-colors", "data", allow_duplicate=True),
            Input("trace-color-picker", "value"),
            Input("trace-line-width", "value"),
            Input("trace-line-style", "value"),
            Input("trace-opacity", "value"),
            State("selected-trace", "data"),
            State("trace-colors", "data"),
            prevent_initial_call="initial_duplicate"
        )
        def update_trace_style(color, width, dash, opacity, trace_name, data):
            if trace_name:
                data[trace_name] = {
                    "color": color["hex"],
                    "width": width,
                    "dash": dash,
                    "opacity": opacity
                }
            return data

    def register_toggle_callbacks(self):
        """
        Registers toggle callbacks for each section defined in the configuration.

        For each section in `self.config`, this method creates a Dash callback that toggles
        the visibility (style) of the corresponding container and updates the toggle button's
        label when the button is clicked. The callback is registered with the Dash app and
        is associated with the toggle button and container for each section.

        The callback is created using the `_make_toggle_callback` method, which is passed the
        current section name.

        Returns:
            None
        """
        for section in self.config:
            toggle_id = f"{section}-toggle"
            container_id = f"{section}-container"

            self.app.callback(
                Output(container_id, "style"),
                Output(toggle_id, "children"),
                Input(toggle_id, "n_clicks"),
                State(container_id, "style"),
                prevent_initial_call=True
            )(self._make_toggle_callback(section))

    def _make_toggle_callback(self, section):
        """
        Creates a callback function to toggle the visibility and label of a UI section.

        Args:
            section (str): The name of the section to be toggled.

        Returns:
            function: A callback function that takes the number of clicks (`n_clicks`) and the current style (`current_style`),
                      and returns a tuple containing the updated style dictionary and label string for the section.
        """
        def toggle_section(n_clicks, current_style):
            is_open = current_style.get("display") != "block"
            label = f"{section.upper()} ▼" if is_open else f"{section.upper()} ▶"
            style = {"display": "block"} if is_open else {"display": "none"}
            return style, label
        return toggle_section

    def register_color_picker_callbacks(self):
        """
        Registers Dash callback functions for color picker components in the application.

        Iterates through the configuration dictionary (`self.config`) to find settings related to colors.
        For each color-related setting, it dynamically creates callback functions that control the visibility
        of the color picker UI elements. The callbacks are triggered by toggle and close button clicks,
        updating the style of the color picker container accordingly.

        This method assumes that for each color setting, there are corresponding toggle, close, and container
        component IDs following the pattern: "{section}-{setting}-toggle", "{section}-{setting}-close", and
        "{section}-{setting}-container".

        Returns:
            None
        """
        for section, settings in self.config.items():
            for setting in settings:
                if isinstance(settings[setting], str) and "color" in setting:
                    toggle_id = f"{section}-{setting}-toggle"
                    close_id = f"{section}-{setting}-close"
                    container_id = f"{section}-{setting}-container"

                    self.app.callback(
                        Output(container_id, "style"),
                        [Input(toggle_id, "n_clicks"), Input(close_id, "n_clicks")],
                        State(container_id, "style"),
                        prevent_initial_call=True
                    )(self._make_color_picker_callback(close_id))

    def _make_color_picker_callback(self, close_id):
        """
        Creates a callback function to toggle the display state of a color picker component.

        Args:
            close_id (str): The ID of the component that, when triggered, should close the color picker.

        Returns:
            function: A callback function that takes the number of open and close clicks, and the current style dict,
                      and returns an updated style dict to show or hide the color picker based on which component triggered the callback.
        """
        def toggle_picker(open_clicks, close_clicks, current_style):
            if not ctx.triggered:
                return dash.no_update
            trigger = ctx.triggered_id
            if trigger == close_id:
                return {"display": "none"}
            return {"display": "block" if current_style.get("display") == "none" else "none"}
        return toggle_picker

    def run(self):
        """
        Starts the Flask application in debug mode.

        This method runs the Flask app associated with the instance, enabling debug mode for development purposes.
        """
        self.app.run(debug=True)


if __name__ == "__main__":
    app_instance = GraphFormatter("config.yml")
    app_instance.run()