import dash
from dash import dcc, html, Input, Output, State, dash_table, ctx
import dash_daq as daq
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import yaml

from config.config_loader import ConfigLoader
from data.data_provider import DataProvider
from components.layout_builder import LayoutBuilder
from callbacks.callback_registrar import CallbackRegistrar



class GraphFormatter:
    """
    A Dash app for interactively customizing Plotly graphs.
    """

    def __init__(self, config_path):
        # Dash app setup
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True, 
                             prevent_initial_callbacks=True)
        self.app.title = "Interactive Plot Editor"

        # Load data and config
        self.df_data = DataProvider().generate_dummy_data()
        self.config = ConfigLoader(config_path).get_config()
        self.input_ids = self.build_input_ids()

        # Build layout
        layout_builder = LayoutBuilder(self.config, self.df_data)
        self.app.layout = layout_builder.build_layout()

        # Register callbacks
        registrar = CallbackRegistrar(
            app=self.app,
            config=self.config,
            df_data=self.df_data,
            get_style_controls_fn=self.get_style_controls_for_plot_type
        )
        registrar.register_figure_callbacks(
            input_ids=self.input_ids,
            create_trace_fn=self.create_trace
        )

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

    def get_style_controls_for_plot_type(self, plot_type, current_style=None):

        if current_style is None:
            current_style = {}

        current_color = current_style.get("color", "#636EFA")
        current_opacity = current_style.get("opacity", 1.0)
        current_line_width = current_style.get("line_width", 2)
        current_marker_size = current_style.get("marker_size", 8)
        current_dash = current_style.get("dash", "solid")
        current_scatter_symbol = current_style.get("symbol", "circle")

        def visible(types): return {"display": "block"} if plot_type in types else {"display": "none"}

        return [
            html.Label("Color"),
            daq.ColorPicker(id="trace-color-picker", value={"hex": current_color}),
            html.Label("Opacity"),
            dcc.Slider(
                id="trace-opacity",
                min=0,
                max=1,
                step=0.05,
                value=current_opacity,
                marks={0: "0", 0.5: "0.5", 1: "1"}
            ),
            html.Label("Line Width", style=visible(["line", "area"])),
            dcc.Input(id="trace-line-width", type="number", min=0, step=0.5, value=current_line_width,
                    style=visible(["line", "area"])),
            html.Label("Marker Size", style=visible(["scatter", "line"])),
            dcc.Input(id="trace-marker-size", type="number", min=0, step=0.5, value=current_marker_size,
                    style=visible(["scatter", "line"])),
            html.Label("Dash Style", style=visible(["line", "area"])),
            dcc.Dropdown(id="trace-line-style",
                options=[{"label": "Solid", "value": "solid"}, {"label": "Dash", "value": "dash"},
                    {"label": "Dot", "value": "dot"}, {"label": "DashDot", "value": "dashdot"}],
                value=current_dash,
                style=visible(["line", "area"])),
            html.Label("Symbol", style=visible(["scatter"])),
            dcc.Dropdown(id="trace-scatter-symbol",
                options=[{"label": "Circle", "value": "circle"}, {"label": "Square", "value": "square"},
                    {"label": "Diamond", "value": "diamond"}, {"label": "Cross", "value": "cross"}],
                value=current_scatter_symbol,
                style=visible(["scatter"])),
            html.Button("✖ Close", id="trace-properties-close"),
        ]

    def create_trace(self, col, plot_type, style):
        """
        Creates a Plotly trace (line, bar, area, etc.) based on the selected plot type and styling.
        """
        common_style = {
            "name": col,
            "opacity": style.get("opacity", 1.0),
        }
        line_width = style.get("line_width", 2)
        marker_size = style.get("marker_size", 8)

        if plot_type == "line":
            return go.Scatter(
                x=self.df_data.index, y=self.df_data[col], mode="lines+markers",
                line=dict(
                    color=style.get("color", "#636EFA"),
                    width=line_width,
                    dash=style.get("dash", "solid")
                ),
                marker=dict(
                    size=marker_size,
                    color=style.get("color", "#636EFA"),
                    symbol=style.get("symbol", "circle")
                ),
                **common_style
            )
        elif plot_type == "scatter":
            return go.Scatter(
                x=self.df_data.index, y=self.df_data[col], mode="markers",
                marker=dict(
                    color=style.get("color", "#636EFA"),
                    size=marker_size,
                    symbol=style.get("symbol", "circle")
                ),
                **common_style
            )
        elif plot_type == "bar_grouped" or plot_type == "bar_stacked":
            return go.Bar(x=self.df_data.index, y=self.df_data[col],
                          marker_color=style.get("color", "#636EFA"), **common_style)
        elif plot_type == "area":
            return go.Scatter(x=self.df_data.index, y=self.df_data[col], mode="lines",
                              fill="tozeroy", line=dict(color=style.get("color", "#636EFA"), width=style.get("width", 2),
                                                       dash=style.get("dash", "solid")), **common_style)
        else:
            return go.Scatter(x=self.df_data.index, y=self.df_data[col], mode="lines", **common_style)
