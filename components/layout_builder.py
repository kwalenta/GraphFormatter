from dash import html, dcc
import dash_daq as daq
from dash import dash_table
import pandas as pd


class LayoutBuilder:
    def __init__(self, config: dict, data: pd.DataFrame):
        self.config = config
        self.df_data = data

    def build_layout(self) -> html.Div:
        return html.Div([
            dcc.Store(id="selected-trace", data=None),
            dcc.Store(id="trace-properties", data={}),
            dcc.Store(id="uploaded-settings", data={}),
            dcc.Store(id="stored-config", data={}),


            html.H3("Plot Customizer"),
            html.Div([
                html.Div([
                    dcc.Upload(
                        id="upload-trace-styles",
                        children=html.Button("🎨 Upload Trace Styles"),
                        multiple=False
                    ),
                    html.Button("⬇ Download Settings", id="download-settings-btn"),
                ], style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "padding": "10px 20px"}),
                dcc.Download(id="download-settings"),
            ]),

            html.Div([
                *[self.create_collapsible_section(section, settings) for section, settings in self.config.items()]
            ], style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "padding": "10px 20px"}),

            html.Div([
                html.Div([
                    dcc.Graph(id="figure")
                ], style={"width": "50%", "display": "inline-block", "verticalAlign": "top"}),

                html.Div(id="trace-properties-picker-container", style={"display": "none"}),
                html.Button("✖ Close", id="trace-properties-close", style={"display": "none"}),

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

    def create_collapsible_section(self, section_name: str, settings: dict) -> html.Div:
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
            elif isinstance(value, str) and "plot_type" in setting:
                input_component = dcc.Dropdown(
                    id=input_id,
                    options=[
                        {"label": "Line", "value": "line"},
                        {"label": "Bar (grouped)", "value": "bar_grouped"},
                        {"label": "Bar (stacked)", "value": "bar_stacked"},
                        {"label": "Scatter", "value": "scatter"},
                        {"label": "Area", "value": "area"}
                    ],
                    value=value
                )
            elif isinstance(value, str) and "file_format" in setting:
                input_component = dcc.Dropdown(
                    id=input_id,
                    options=[
                        {"label": "PNG", "value": "png"},
                        {"label": "JPEG", "value": "jpeg"},
                        {"label": "SVG", "value": "svg"},
                    ],
                    value=value
                )
            elif isinstance(value, str):
                input_component = dcc.Input(type="text", value=value, id=input_id, style={"width": "150px"})
            elif isinstance(value, list) and len(value) == 2:
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
