import bokeh.io
import bokeh.plotting
import bokeh.models
import bokeh as bk
import numpy as np


def fig_setup(nh3_alert_level, co_alert_level, o2_alert_level):
    time = np.array([], dtype=np.datetime64)

    nh3_danger_zone = bokeh.models.BoxAnnotation(
        bottom=nh3_alert_level, fill_alpha=0.2, fill_color="#D55E00"
    )
    nh3_safe_zone = bokeh.models.BoxAnnotation(
        top=nh3_alert_level, fill_alpha=0.2, fill_color="#0072B2"
    )

    co_danger_zone = bokeh.models.BoxAnnotation(
        bottom=co_alert_level, fill_alpha=0.2, fill_color="#D55E00"
    )
    co_safe_zone = bokeh.models.BoxAnnotation(
        top=co_alert_level, fill_alpha=0.2, fill_color="#0072B2"
    )

    o2_danger_zone = bokeh.models.BoxAnnotation(
        top=o2_alert_level, fill_alpha=0.2, fill_color="#D55E00"
    )
    o2_safe_zone = bokeh.models.BoxAnnotation(
        bottom=o2_alert_level, fill_alpha=0.2, fill_color="#0072B2"
    )

    ds = bk.models.ColumnDataSource(
        data=dict(time=time, nh3_level=[], co_level=[], oxygenlevel=[])
    )  # like empty df

    # NH3-Plot
    nh3_fig = bk.plotting.figure(x_axis_type="datetime", height=400, width=800)
    nh3_fig.line(x="time", y="nh3_level", source=ds, legend_label="NH3-Level")
    nh3_fig.add_layout(nh3_danger_zone)
    nh3_fig.add_layout(nh3_safe_zone)
    nh3_fig.title.text = "Ammonia"

    # CO-Plot
    co_fig = bk.plotting.figure(x_axis_type="datetime", height=400, width=800)
    co_fig.line(x="time", y="co_level", source=ds, legend_label="CO-Level")
    co_fig.add_layout(co_danger_zone)
    co_fig.add_layout(co_safe_zone)
    co_fig.title.text = "Carbon Monoxide"

    # O2-Plot
    o2_fig = bk.plotting.figure(x_axis_type="datetime", height=400, width=800)
    o2_fig.line(x="time", y="oxygenlevel", source=ds, legend_label="O2-Level")
    o2_fig.add_layout(o2_danger_zone)
    o2_fig.add_layout(o2_safe_zone)
    o2_fig.title.text = "Oxygen"

    p = bokeh.layouts.gridplot([[nh3_fig], [co_fig], [o2_fig]])
    handle = bokeh.io.show(
        p, notebook_handle=True
    )  # um Daten nachzuschieben im Notebook

    return handle, ds


def plot(handle, ds, time, ammonia, carbon_monoxide, oxygen):
    ds.stream(
        dict(
            time=[time],
            nh3_level=[ammonia],
            co_level=[carbon_monoxide],
            oxygenlevel=[oxygen],
        ),
        rollover=600,
    )  # Neue Daten werden an das Ende der Kolonnen angehängt, ab 600 werden die ältesten Daten herausgeworfen
    bk.io.push_notebook(handle=handle)
