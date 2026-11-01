"""The column sub-components must not share a name: it is the CSV file name."""

from resslab_hub.routers.columns import (
    axial_shortening_component,
    moment_strong_component,
    moment_weak_component,
)


def test_column_series_have_distinct_csv_names():
    names = [
        axial_shortening_component.name,
        moment_strong_component.name,
        moment_weak_component.name,
    ]
    assert len(set(names)) == len(names)
    assert moment_strong_component.name.endswith("moment-strong")
    assert moment_weak_component.name.endswith("moment-weak")
