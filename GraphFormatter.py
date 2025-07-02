import dash
from dash import dcc, html, Input, Output, State, dash_table, ctx
from dash.exceptions import PreventUpdate
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
        self.register_figure_callbacks()
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
        "trace-properties" (with property "data").

        Returns:
            list: A list of Input objects corresponding to the application's input components.
        """
        ids = []
        for section, settings in self.config.items():
            for setting, value in settings.items():  
                if isinstance(value, list) and len(value) == 2:
                    ids.append(Input(f"{section}-{setting}_0", "value"))
                    ids.append(Input(f"{section}-{setting}_1", "value"))
                else:
                    ids.append(Input(f"{section}-{setting}", "value"))

        ids.append(Input("data-table", "selected_columns"))
        ids.append(Input("trace-properties", "data"))
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
                    dcc.Store(id="trace-properties", data={}),
                    html.Div([
                        html.Label("Line Color"),
                        daq.ColorPicker(id="trace-properties-picker", value={"hex": "#636EFA"}),

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

                        html.Button("✖ Close", id="trace-properties-close")
                    ], id="trace-properties-picker-container", style={"display": "none", "marginTop": "10px", "width": "250px"})

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

    def create_trace(self, col, plot_type, style):
        """
        Factory method to create different types of traces based on plot_type.
        
        Args:
            col (str): Column name for the trace
            plot_type (str): Type of plot ("line", "bar", "scatter", "area")
            style (dict): Style configuration for the trace
            
        Returns:
            plotly trace object
        """
        base_config = {
            'x': self.df_data.index,
            'y': self.df_data[col],
            'name': col,
            'opacity': style.get("opacity", 1.0)
        }
        
        if plot_type == "line":
            return go.Scatter(
                mode="lines+markers",
                line=dict(
                    color=style.get("color"),
                    width=style.get("width", 2),
                    dash=style.get("dash", "solid")
                ),
                **base_config
            )
        elif plot_type == "bar":
            return go.Bar(
                marker=dict(
                    color=style.get("color"),
                    line=dict(width=style.get("width", 0))
                ),
                **base_config
            )
        elif plot_type == "scatter":
            return go.Scatter(
                mode="markers",
                marker=dict(
                    color=style.get("color"),
                    size=style.get("width", 8),  # Use width as marker size
                    line=dict(width=style.get("line_width", 0))
                ),
                **base_config
            )
        elif plot_type == "area":
            return go.Scatter(
                mode="lines",
                fill='tonexty' if col != self.df_data.columns[0] else 'tozeroy',
                line=dict(
                    color=style.get("color"),
                    width=style.get("width", 2),
                    dash=style.get("dash", "solid")
                ),
                **base_config
            )
        else:
            # Default to line plot
            return go.Scatter(
                mode="lines+markers",
                line=dict(
                    color=style.get("color"),
                    width=style.get("width", 2),
                    dash=style.get("dash", "solid")
                ),
                **base_config
            )

    def get_style_controls_for_plot_type(self, plot_type, current_style=None):
        """
        Returns appropriate style controls based on plot type with current values.
        
        Args:
            plot_type (str): The type of plot
            current_style (dict): Current style settings for the trace
            
        Returns:
            list: List of HTML components for style controls
        """
        if current_style is None:
            current_style = {}
            
        # Get current values or defaults
        current_color = current_style.get("color", "#636EFA")
        current_opacity = current_style.get("opacity", 1.0)
        current_width = current_style.get("width", 2 if plot_type in ["line", "area"] else 8 if plot_type == "scatter" else 0)
        current_dash = current_style.get("dash", "solid")
        
        common_controls = [
            html.Label("Color"),
            daq.ColorPicker(id="trace-properties-picker", value={"hex": current_color}),
            html.Label("Opacity"),
            dcc.Slider(id="trace-opacity", min=0, max=1, step=0.05, value=current_opacity),
        ]
        
        if plot_type == "line":
            specific_controls = [
                html.Label("Line Width"),
                dcc.Input(id="trace-line-width", type="number", min=0, step=0.5, value=current_width),
                html.Label("Dash Style"),
                dcc.Dropdown(
                    id="trace-line-style",
                    options=[
                        {"label": "Solid", "value": "solid"},
                        {"label": "Dash", "value": "dash"},
                        {"label": "Dot", "value": "dot"},
                        {"label": "DashDot", "value": "dashdot"},
                    ],
                    value=current_dash
                ),
            ]
        elif plot_type == "bar":
            specific_controls = [
                html.Label("Border Width"),
                dcc.Input(id="trace-line-width", type="number", min=0, step=0.5, value=current_width),
                dcc.Dropdown(
                    id="trace-line-style",
                    options=[],
                    value="solid",
                    style={"display": "none"}  # No dash style for bars
                ),
            ]
        elif plot_type == "scatter":
            specific_controls = [
                html.Label("Marker Size"),
                dcc.Input(id="trace-line-width", type="number", min=1, step=1, value=current_width),
                html.Label("Marker Border Width"),
                #dcc.Input(id="trace-line-border-width", type="number", min=0, step=0.5, value=0),
                dcc.Dropdown(
                    id="trace-line-style",
                    options=[],
                    value="solid",
                    style={"display": "none"}  # No dash style for bars
                ),
            ]
        elif plot_type == "area":
            specific_controls = [
                html.Label("Line Width"),
                dcc.Input(id="trace-line-width", type="number", min=0, step=0.5, value=current_width),
                html.Label("Dash Style"),
                dcc.Dropdown(
                    id="trace-line-style",
                    options=[
                        {"label": "Solid", "value": "solid"},
                        {"label": "Dash", "value": "dash"},
                        {"label": "Dot", "value": "dot"},
                        {"label": "DashDot", "value": "dashdot"},
                    ],
                    value=current_dash
                ),
            ]
        else:
            specific_controls = [
                html.Label(""),
                dcc.Input(id="trace-line-width", type="number", min=0, step=0.5, value=current_width, style={"display": "none"}),
                html.Label(""),
                dcc.Dropdown(
                    id="trace-line-style",
                    options=[],
                    value=current_dash,
                    style={"display": "none"}  # No dash style for other types
                ),
            ]
            
        return common_controls + specific_controls + [html.Button("✖ Close", id="trace-properties-close")]

    def register_figure_callbacks(self):
        """
        Registers all Dash callback functions required for interactive graph formatting.
        This method sets up the following callbacks:
        1. Updates the Plotly figure based on user input controls, including plot type, selected columns, and trace colors.
        2. Toggles the visibility and content of the trace properties picker when a trace is clicked or the plot type changes.
        3. Updates the style properties of individual traces (such as color, width, dash style, and opacity) based on user input.
        The callbacks handle:
            - Dynamic updating of the figure layout and traces according to the current configuration and user selections.
            - Display and update of trace-specific style controls, adapting to the selected plot type.
            - Storage and retrieval of trace style data for consistent user experience.
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
            
            # Get plot type from config
            plot_type = updated_config.get("plot_settings", {}).get("type", "line")

            # Plot selected columns using the factory method
            for col in selected_columns:
                style = trace_colors.get(col, {})
                trace = self.create_trace(col, plot_type, style)
                fig.add_trace(trace)

            # Apply layout settings (rest remains the same)
            fig.update_layout(
                xaxis=updated_config.get("xaxis", {}),
                yaxis=updated_config.get("yaxis", {}),
                width=updated_config["properties"]["width"],
                height=updated_config["properties"]["height"],
                paper_bgcolor=updated_config["properties"]["paper_bgcolor"],
                plot_bgcolor=updated_config["properties"]["plot_bgcolor"],
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

            # Optional line above plot
            if updated_config["top-line"]["enabled"]:
                fig.add_shape(
                    type="line",
                    xref="paper", yref="paper",
                    y0=updated_config["top-line"]["y"],
                    y1=updated_config["top-line"]["y"],
                    x0=updated_config["top-line"]["x0"],
                    x1=updated_config["top-line"]["x1"],
                    line=dict(
                        color=updated_config["top-line"]["color"],
                        width=updated_config["top-line"]["width"]
                    )
                )

            return fig

        @self.app.callback(
            Output("trace-properties-picker-container", "style"),
            Output("trace-properties-picker-container", "children"),
            Output("selected-trace", "data"),
            Input("figure", "clickData"),
            Input("trace-properties-close", "n_clicks"),
            Input("plot_settings-type", "value"),  # Add plot type as input
            State("trace-properties-picker-container", "style"),
            State("figure", "figure"),
            State("trace-properties", "data"),  # Add current trace colors as state
            prevent_initial_call=True
        )
        def toggle_trace_picker(clickData, close_clicks, plot_type, current_style, figure_data, trace_colors):
            if not ctx.triggered:
                return current_style, dash.no_update, dash.no_update
                
            trigger = ctx.triggered_id
            
            if trigger == "trace-properties-close":
                return {"display": "none"}, dash.no_update, None
                
            if clickData and "curveNumber" in clickData["points"][0]:
                curve_idx = clickData["points"][0]["curveNumber"]
                trace_name = figure_data["data"][curve_idx]["name"]
                
                # Get current trace style or defaults
                current_trace_style = trace_colors.get(trace_name, {})
                
                # Get plot type (from input or fallback to config)
                if plot_type is None:
                    plot_type = self.config.get("plot_settings", {}).get("type", "line")
                
                controls = self.get_style_controls_for_plot_type(plot_type, current_trace_style)
                
                return {"display": "block", "marginTop": "10px", "width": "250px"}, controls, trace_name
            
            # If plot type changed, update controls with current trace if one is selected
            elif trigger == "plot_settings-type" and current_style.get("display") == "block":
                # Get currently selected trace from trace_colors or use first available
                selected_trace = list(trace_colors.keys())[0] if trace_colors else None
                if selected_trace:
                    current_trace_style = trace_colors.get(selected_trace, {})
                    controls = self.get_style_controls_for_plot_type(plot_type, current_trace_style)
                    return current_style, controls, selected_trace
                
            return dash.no_update, dash.no_update, dash.no_update

        @self.app.callback(
            Output("trace-properties", "data", allow_duplicate=True),
            Input("trace-properties-picker", "value"),
            Input("trace-line-width", "value"),
            Input("trace-line-style", "value"),
            Input("trace-opacity", "value"),
            State("selected-trace", "data"),
            State("trace-properties", "data"),
            prevent_initial_call="initial_duplicate"
        )
        def update_trace_style(color, width, dash, opacity, trace_name, data):
            if trace_name:
                plot_type = self.config.get("plot_settings", {}).get("type", "line")
                
                style_data = {
                    "color": color["hex"] if color else "#636EFA",
                    "opacity": opacity if opacity is not None else 1.0
                }
                
                # Add plot-type specific properties
                if plot_type in ["line", "area"]:
                    style_data.update({
                        "width": width if width is not None else 2,
                        "dash": dash if dash else "solid"
                    })
                elif plot_type == "bar":
                    style_data["width"] = width if width is not None else 0  # border width
                elif plot_type == "scatter":
                    style_data["width"] = width if width is not None else 8  # marker size
                
                data[trace_name] = style_data
            
            return data
    
    def run(self):
        """
        Starts the Flask application in debug mode.

        This method runs the Flask app associated with the instance, enabling debug mode for development purposes.
        """
        self.app.run(debug=True)


if __name__ == "__main__":
    app_instance = GraphFormatter("config.yml")
    app_instance.run()