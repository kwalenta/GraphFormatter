from dash import Input, Output, State, ctx, no_update, dcc
from dash.exceptions import PreventUpdate
from dash import html
import dash_daq as daq
import plotly.graph_objects as go
import base64
import json
import io
import zipfile
import yaml

class CallbackRegistrar:
    def __init__(self, app, config, df_data, get_style_controls_fn):
        self.app = app
        self.config = config
        self.df_data = df_data
        self.get_style_controls_for_plot_type = get_style_controls_fn

        # Register all general-purpose callbacks
        self.register_toggle_callbacks()
        self.register_color_picker_callbacks()
        self.register_trace_popup_callbacks()
        self.register_style_update_callbacks()  
        self.register_store_config_callback()   
        self.register_upload_callbacks()
        
    # ------------------ 1. Collapsible section toggles ------------------

    def register_toggle_callbacks(self):
        """
        Registers toggle callbacks for each section defined in the configuration.
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
        """
        def toggle_section(n_clicks, current_style):
            is_open = current_style.get("display") != "block"
            label = f"{section.upper()} ▼" if is_open else f"{section.upper()} ▶"
            style = {"display": "block"} if is_open else {"display": "none"}
            return style, label
        return toggle_section

    # ------------------ 2. Color Picker toggle logic ------------------

    def register_color_picker_callbacks(self):
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
        def toggle_picker(open_clicks, close_clicks, current_style):
            if not ctx.triggered:
                return no_update
            trigger = ctx.triggered_id
            if trigger == close_id:
                return {"display": "none"}
            return {"display": "block" if current_style.get("display") == "none" else "none"}
        return toggle_picker
    
    # ------------------ 3. Trace clicker logic ------------------
    
    def register_trace_popup_callbacks(self):
        """
        Registers the popup trace menu callbacks, including:
        - Showing popup on trace click
        - Closing popup on button click
        - Updating style controls when plot_type changes
        """
        @self.app.callback(
            Output("trace-properties-picker-container", "style"),
            Output("trace-properties-picker-container", "children"),
            Output("selected-trace", "data"),
            Input("figure", "clickData"),
            Input("trace-properties-close", "n_clicks"),  # needed to trigger close
            Input("properties-plot_type", "value"),       # for type-based control update
            State("trace-properties-picker-container", "style"),
            State("figure", "figure"),
            State("trace-properties", "data"),
            prevent_initial_call=True
        )
        def toggle_trace_picker(clickData, _, plot_type, current_style, figure_data, trace_properties):
            if not ctx.triggered:
                return current_style, no_update, no_update

            trigger = ctx.triggered_id

            # Close popup
            if trigger == "trace-properties-close":
                return {"display": "none"}, no_update, None

            # Clicked on a trace
            if clickData and "curveNumber" in clickData["points"][0]:
                curve_idx = clickData["points"][0]["curveNumber"]
                # Prevent crash if figure has no traces yet (e.g. no columns selected)
                if not figure_data or "data" not in figure_data or curve_idx >= len(figure_data["data"]):
                    return no_update, no_update, no_update
                trace_name = figure_data["data"][curve_idx]["name"]

                current_trace_style = trace_properties.get(trace_name, {}) if trace_properties else {}

                if plot_type is None:
                    plot_type = self.config.get("properties", {}).get("plot_type", "line")

                controls = self.get_style_controls_for_plot_type(plot_type, current_trace_style)
                return {"display": "block", "marginTop": "10px", "width": "250px"}, controls, trace_name

            # Plot type changed → update styling UI for selected trace
            elif trigger == "properties-plot_type" and current_style.get("display") == "block":
                selected_trace = list(trace_properties.keys())[0] if trace_properties else None
                if selected_trace:
                    current_trace_style = trace_properties.get(selected_trace, {})
                    controls = self.get_style_controls_for_plot_type(plot_type, current_trace_style)
                    return current_style, controls, selected_trace

            return no_update, no_update, no_update
        
    # ------------------ 4. Trace style update logic ------------------

    def register_style_update_callbacks(self):
        """
        Updates the style of a selected trace and stores it in the trace-properties state.
        """
        @self.app.callback(
            Output("trace-properties", "data", allow_duplicate=True),
            Input("trace-color-picker", "value"),
            Input("trace-line-width", "value"),
            Input("trace-marker-size", "value"),
            Input("trace-line-style", "value"),
            Input("trace-opacity", "value"),
            State("selected-trace", "data"),
            State("trace-properties", "data"),
            prevent_initial_call="initial_duplicate"
        )
        def update_trace_style(color, line_width, marker_size, dash, opacity, trace_name, data):
            if trace_name:
                plot_type = self.config.get("plot_settings", {}).get("type", "line")
                style_data = {
                    "color": color["hex"] if color else "#636EFA",
                    "opacity": opacity if opacity is not None else 1.0,
                    "line_width": line_width if line_width is not None else 2,
                    "marker_size": marker_size if marker_size is not None else 8,
                }
                if plot_type in ["line", "area"]:
                    style_data["dash"] = dash if dash else "solid"
                if plot_type == "scatter":
                    style_data["symbol"] = style_data.get("symbol", "circle")
                data[trace_name] = style_data
            return data

    # ------------------ 5. Figure update logic ------------------
    def register_figure_callbacks(self, input_ids, create_trace_fn):
        """
        Registers the main figure-building callback. Updates Plotly figure based on user input and styling.
        """
        @self.app.callback(
            Output("figure", "figure"),
            Output("stored-config", "data", allow_duplicate=True),
            input_ids
        )
        def update_figure(*args):
            *values, selected_columns, trace_properties = args

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

            plot_type = updated_config.get("properties", {}).get("plot_type", "line")

            for col in selected_columns:
                style = trace_properties.get(col, {})
                trace = create_trace_fn(col, plot_type, style)
                fig.add_trace(trace)

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

            if plot_type == "bar_stacked":
                fig.update_layout(barmode="stack")
            elif plot_type == "bar_grouped":
                fig.update_layout(barmode="group")

            return fig, updated_config

    # ------------------ 6. Store config for download ------------------

    def register_store_config_callback(self):
        @self.app.callback(
            Output("download-settings", "data"),
            Input("download-settings-btn", "n_clicks"),
            State("stored-config", "data"),
            State("trace-properties", "data"),
            prevent_initial_call=True
        )
        def download_combined_zip(n_clicks, config_data, trace_data):
            if not config_data or not trace_data:
                raise PreventUpdate

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                # YAML config
                yaml_str = yaml.dump(config_data, sort_keys=False)
                zf.writestr("config.yml", yaml_str)

                # JSON trace styles
                json_str = json.dumps(trace_data, indent=2)
                zf.writestr("trace_styles.json", json_str)

            zip_buffer.seek(0)
            return dcc.send_bytes(zip_buffer.read(), filename="plot_settings.zip")
        

    # ------------------ 7. Upload config callback ------------------

    def register_upload_callbacks(self):
        """
        Registers the callback for uploading settings from a JSON file.
        The uploaded file should contain a JSON object with "config" and "traces" keys.
        """
        @self.app.callback(
            Output("trace-properties", "data", allow_duplicate=True),
            Input("upload-trace-styles", "contents"),
            prevent_initial_call="initial_duplicate"
        )
        def load_trace_styles(contents):
            if contents is None:
                raise PreventUpdate

            content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)
            
            try:
                trace_styles = json.loads(decoded.decode("utf-8"))
            except Exception as e:
                print("Error decoding trace styles:", e)
                raise PreventUpdate

            return trace_styles

